from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.db.models import (
    Q,
    Count,
    Sum,
    Avg,
    Prefetch,
    Exists,
    OuterRef,
    Case,
    When,
    IntegerField,
)
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta
from .models import Habitacion, Huesped, Membership, Reserva, CheckIn, CheckOut
from .forms import (
    CrearPersonalHotelForm,
    HuespedForm,
    HabitacionForm,
    ReservaForm,
    CheckInForm,
    CheckOutForm,
)


def _checkin_reserva(reserva):
    """Evita hasattr/getattr con reverse OneToOne (puede lanzar RelatedObjectDoesNotExist)."""
    try:
        return reserva.checkin
    except ObjectDoesNotExist:
        return None


def _checkout_reserva(reserva):
    try:
        return reserva.checkout
    except ObjectDoesNotExist:
        return None


def _nombre_empleado_checkin(user):
    """Nombre que se guarda en CheckIn.empleado según la cuenta con la que inició sesión."""
    if not user or not getattr(user, 'is_authenticated', False):
        return ''
    nombre = (user.get_full_name() or '').strip()
    if nombre:
        return nombre[:100]
    return (user.get_username() or '')[:100]


def _reservas_activas_en_habitacion(habitacion):
    """Reservas que siguen ocupando o reservando la habitación (no canceladas ni check-out)."""
    return Reserva.objects.filter(
        habitacion=habitacion,
        estado__in=[
            Reserva.ESTADO_PENDIENTE,
            Reserva.ESTADO_CONFIRMADA,
            Reserva.ESTADO_CHECKIN,
        ],
    )


def sincronizar_estado_habitacion(habitacion):
    """
    Ajusta el estado físico de la habitación según reservas activas.
    Debe llamarse tras cancelar, editar habitación de una reserva, etc.
    """
    pk = habitacion.pk if hasattr(habitacion, 'pk') else habitacion
    habitacion = Habitacion.objects.get(pk=pk)
    qs = _reservas_activas_en_habitacion(habitacion)
    if not qs.exists():
        habitacion.estado = Habitacion.ESTADO_DISPONIBLE
    elif qs.filter(estado=Reserva.ESTADO_CHECKIN).exists():
        habitacion.estado = Habitacion.ESTADO_OCUPADA
    else:
        habitacion.estado = Habitacion.ESTADO_RESERVADA
    habitacion.save(update_fields=['estado'])


def index(request):
    """Dashboard de recepción mejorado con tareas del día"""
    hoy = timezone.localdate()
    ahora = timezone.now()
    
    # Estadísticas rápidas
    total_habitaciones = Habitacion.objects.count()
    habitaciones_disponibles = Habitacion.objects.filter(estado=Habitacion.ESTADO_DISPONIBLE).count()
    habitaciones_ocupadas = Habitacion.objects.filter(estado=Habitacion.ESTADO_OCUPADA).count()
    habitaciones_limpieza = Habitacion.objects.filter(estado=Habitacion.ESTADO_LIMPIEZA).count()
    
    # Check-ins pendientes: confirmadas, dentro de estancia, sin check-in aún
    checkins_pendientes = (
        Reserva.objects.filter(
            estado=Reserva.ESTADO_CONFIRMADA,
            fecha_entrada__lte=hoy,
            fecha_salida__gt=hoy,
        )
        .annotate(_tiene_ci=Exists(CheckIn.objects.filter(reserva_id=OuterRef('pk'))))
        .filter(_tiene_ci=False)
        .select_related('huesped', 'habitacion')
        .order_by('fecha_entrada')[:10]
    )
    
    # Check-outs visibles hoy: salida programada hoy, salida prevista hoy, o en habitación con salida futura (salida anticipada)
    checkouts_hoy = (
        Reserva.objects.filter(estado=Reserva.ESTADO_CHECKIN)
        .filter(
            Q(fecha_salida=hoy)
            | Q(fecha_hora_salida_prevista__date=hoy)
            | Q(fecha_entrada__lte=hoy, fecha_salida__gt=hoy)
        )
        .select_related('huesped', 'habitacion')
        .order_by('fecha_hora_salida_prevista', 'fecha_salida')[:10]
    )

    # Check-outs en ventana próxima (salida prevista con hora en 2 h, o hoy sin hora fija)
    hora_limite = ahora + timedelta(hours=2)
    checkouts_proximos = (
        Reserva.objects.filter(estado=Reserva.ESTADO_CHECKIN)
        .filter(
            Q(
                fecha_hora_salida_prevista__isnull=False,
                fecha_hora_salida_prevista__gte=ahora,
                fecha_hora_salida_prevista__lte=hora_limite,
            )
            | Q(fecha_hora_salida_prevista__isnull=True, fecha_salida=hoy)
        )
        .select_related('huesped', 'habitacion')
        .order_by('fecha_hora_salida_prevista', 'fecha_salida')[:5]
    )
    
    # Habitaciones en limpieza por más de 2 horas
    habitaciones_limpieza_largas = Habitacion.objects.filter(
        estado=Habitacion.ESTADO_LIMPIEZA
    )[:5]
    
    # Reservas recientes
    reservas_recientes = (
        Reserva.objects.all()
        .select_related('huesped', 'habitacion', 'creado_por')
        .order_by('-fecha_creacion')[:5]
    )
    
    context = {
        'total_habitaciones': total_habitaciones,
        'habitaciones_disponibles': habitaciones_disponibles,
        'habitaciones_ocupadas': habitaciones_ocupadas,
        'habitaciones_limpieza': habitaciones_limpieza,
        'checkins_pendientes': checkins_pendientes,
        'checkouts_hoy': checkouts_hoy,
        'checkouts_proximos': checkouts_proximos,
        'habitaciones_limpieza_largas': habitaciones_limpieza_largas,
        'reservas_recientes': reservas_recientes,
        'hoy': hoy,
    }
    return render(request, 'hotel/index.html', context)


# ========== GESTIÓN DE RESERVAS ==========

def lista_reservas(request):
    """Lista todas las reservas con filtros"""
    reservas = Reserva.objects.all().select_related('huesped', 'habitacion', 'creado_por')
    
    # Filtros
    estado = request.GET.get('estado')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    if estado:
        reservas = reservas.filter(estado=estado)
    if fecha_desde:
        reservas = reservas.filter(fecha_entrada__gte=fecha_desde)
    if fecha_hasta:
        reservas = reservas.filter(fecha_entrada__lte=fecha_hasta)
    
    reservas = reservas.order_by('-fecha_creacion')
    
    context = {
        'reservas': reservas,
        'estado_actual': estado,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    }
    return render(request, 'hotel/reservas/lista.html', context)


def crear_reserva(request):
    """Crear una nueva reserva"""
    if request.method == 'POST':
        form = ReservaForm(request.POST)
        if form.is_valid():
            reserva = form.save()
            if request.user.is_authenticated:
                reserva.creado_por = request.user
                reserva.save(update_fields=['creado_por'])
            reserva.habitacion.estado = Habitacion.ESTADO_RESERVADA
            reserva.habitacion.save(update_fields=['estado'])
            messages.success(request, f'Reserva #{reserva.id} creada exitosamente.')
            return redirect('detalle_reserva', reserva_id=reserva.id)
    else:
        form = ReservaForm()
    
    return render(request, 'hotel/reservas/crear.html', {'form': form})


def detalle_reserva(request, reserva_id):
    """Ver detalles de una reserva"""
    reserva = get_object_or_404(
        Reserva.objects.select_related(
            'huesped',
            'habitacion',
            'creado_por',
            'checkin',
            'checkout',
            'checkout__registrado_por',
        ),
        id=reserva_id,
    )
    checkin = _checkin_reserva(reserva)
    checkout = _checkout_reserva(reserva)

    hoy = timezone.localdate()
    puede_checkin = (
        checkin is None
        and reserva.estado
        in (Reserva.ESTADO_PENDIENTE, Reserva.ESTADO_CONFIRMADA)
        and reserva.fecha_entrada <= hoy
    )
    puede_checkout = (
        checkin is not None
        and checkout is None
        and reserva.estado == Reserva.ESTADO_CHECKIN
    )
    puede_cancelar = (
        checkin is None
        and reserva.estado not in (Reserva.ESTADO_CANCELADA, Reserva.ESTADO_CHECKOUT)
    )

    context = {
        'reserva': reserva,
        'checkin': checkin,
        'checkout': checkout,
        'puede_checkin': puede_checkin,
        'puede_checkout': puede_checkout,
        'puede_cancelar': puede_cancelar,
        'hoy': hoy,
    }
    return render(request, 'hotel/reservas/detalle.html', context)


def editar_reserva(request, reserva_id):
    """Editar una reserva existente"""
    reserva = get_object_or_404(
        Reserva.objects.select_related('huesped', 'habitacion'),
        id=reserva_id,
    )

    if request.method == 'POST':
        form = ReservaForm(request.POST, instance=reserva)
        if form.is_valid():
            habitacion_anterior_id = reserva.habitacion_id
            form.save()
            reserva.refresh_from_db()
            if habitacion_anterior_id != reserva.habitacion_id:
                sincronizar_estado_habitacion(Habitacion.objects.get(pk=habitacion_anterior_id))
                sincronizar_estado_habitacion(reserva.habitacion)
            messages.success(request, f'Reserva #{reserva.id} actualizada exitosamente.')
            return redirect('detalle_reserva', reserva_id=reserva.id)
    else:
        form = ReservaForm(instance=reserva)
    
    return render(request, 'hotel/reservas/editar.html', {'form': form, 'reserva': reserva})


def cancelar_reserva(request, reserva_id):
    """Cancelar una reserva"""
    reserva = get_object_or_404(Reserva, id=reserva_id)
    puede_cancelar = (
        _checkin_reserva(reserva) is None
        and reserva.estado not in (Reserva.ESTADO_CANCELADA, Reserva.ESTADO_CHECKOUT)
    )

    if request.method == 'POST':
        if _checkin_reserva(reserva) is not None:
            messages.error(
                request,
                'No se puede cancelar: ya existe check-in. Use el flujo de check-out o consulte al administrador.',
            )
            return redirect('detalle_reserva', reserva_id=reserva.id)
        if reserva.estado in (Reserva.ESTADO_CANCELADA, Reserva.ESTADO_CHECKOUT):
            messages.warning(request, 'Esta reserva ya no se puede cancelar.')
            return redirect('detalle_reserva', reserva_id=reserva.id)
        habitacion = reserva.habitacion
        reserva.estado = Reserva.ESTADO_CANCELADA
        reserva.save(update_fields=['estado', 'fecha_actualizacion'])
        sincronizar_estado_habitacion(habitacion)
        messages.success(request, f'Reserva #{reserva.id} cancelada exitosamente.')
        return redirect('lista_reservas')

    return render(request, 'hotel/reservas/cancelar.html', {'reserva': reserva, 'puede_cancelar': puede_cancelar})


# ========== CONTROL DE HABITACIONES ==========

def lista_habitaciones(request):
    """Lista todas las habitaciones con su estado"""
    habitaciones = Habitacion.objects.all().annotate(
        reservas_activas=Count(
            'reservas',
            filter=Q(
                reservas__estado__in=[
                    Reserva.ESTADO_PENDIENTE,
                    Reserva.ESTADO_CONFIRMADA,
                    Reserva.ESTADO_CHECKIN,
                ]
            ),
        )
    )
    
    estado = request.GET.get('estado')
    tipo = request.GET.get('tipo')
    
    if estado:
        habitaciones = habitaciones.filter(estado=estado)
    if tipo:
        habitaciones = habitaciones.filter(tipo=tipo)
    
    habitaciones = habitaciones.order_by('numero')
    
    context = {
        'habitaciones': habitaciones,
        'estado_actual': estado,
        'tipo_actual': tipo,
    }
    return render(request, 'hotel/habitaciones/lista.html', context)


def detalle_habitacion(request, habitacion_id):
    """Ver detalles de una habitación"""
    habitacion = get_object_or_404(Habitacion, id=habitacion_id)
    reservas = habitacion.reservas.all().order_by('-fecha_creacion')[:10]
    
    # Verificar disponibilidad para fechas específicas
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    disponible = None
    
    if fecha_desde and fecha_hasta:
        reservas_conflictivas = Reserva.objects.filter(
            habitacion=habitacion,
            estado__in=[
                Reserva.ESTADO_PENDIENTE,
                Reserva.ESTADO_CONFIRMADA,
                Reserva.ESTADO_CHECKIN,
            ],
            fecha_entrada__lt=fecha_hasta,
            fecha_salida__gt=fecha_desde,
        )
        disponible = not reservas_conflictivas.exists()
    
    context = {
        'habitacion': habitacion,
        'reservas': reservas,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'disponible': disponible,
    }
    return render(request, 'hotel/habitaciones/detalle.html', context)


def crear_habitacion(request):
    """Crear una nueva habitación"""
    if request.method == 'POST':
        form = HabitacionForm(request.POST)
        if form.is_valid():
            habitacion = form.save()
            messages.success(request, f'Habitación {habitacion.numero} creada exitosamente.')
            return redirect('detalle_habitacion', habitacion_id=habitacion.id)
    else:
        form = HabitacionForm()
    
    return render(request, 'hotel/habitaciones/crear.html', {'form': form})


def editar_habitacion(request, habitacion_id):
    """Editar una habitación existente"""
    habitacion = get_object_or_404(Habitacion, id=habitacion_id)
    
    if request.method == 'POST':
        form = HabitacionForm(request.POST, instance=habitacion)
        if form.is_valid():
            form.save()
            messages.success(request, f'Habitación {habitacion.numero} actualizada exitosamente.')
            return redirect('detalle_habitacion', habitacion_id=habitacion.id)
    else:
        form = HabitacionForm(instance=habitacion)
    
    return render(request, 'hotel/habitaciones/editar.html', {'form': form, 'habitacion': habitacion})


@require_http_methods(['POST'])
def eliminar_habitacion(request, habitacion_id):
    """Elimina una habitación sin reservas activas (admin)."""
    habitacion = get_object_or_404(Habitacion, id=habitacion_id)
    activas = habitacion.reservas.filter(
        estado__in=[
            Reserva.ESTADO_PENDIENTE,
            Reserva.ESTADO_CONFIRMADA,
            Reserva.ESTADO_CHECKIN,
        ]
    )
    if activas.exists():
        messages.error(
            request,
            'No se puede eliminar esta habitación: tiene reservas pendientes, confirmadas o con check-in.',
        )
        return redirect('detalle_habitacion', habitacion_id=habitacion.id)
    n_historial = habitacion.reservas.count()
    numero = habitacion.numero
    habitacion.delete()
    if n_historial:
        messages.warning(
            request,
            f'Habitación {numero} eliminada. También se eliminaron {n_historial} reserva(s) del historial.',
        )
    else:
        messages.success(request, f'Habitación {numero} eliminada.')
    return redirect('lista_habitaciones')


def disponibilidad_habitaciones(request):
    """Ver disponibilidad de habitaciones en un rango de fechas"""
    fecha_desde = request.GET.get('fecha_desde', timezone.localdate().isoformat())
    fecha_hasta = request.GET.get('fecha_hasta', (timezone.localdate() + timedelta(days=7)).isoformat())
    
    habitaciones = Habitacion.objects.all()
    habitaciones_disponibles = []
    
    for habitacion in habitaciones:
        reservas_conflictivas = Reserva.objects.filter(
            habitacion=habitacion,
            estado__in=[
                Reserva.ESTADO_PENDIENTE,
                Reserva.ESTADO_CONFIRMADA,
                Reserva.ESTADO_CHECKIN,
            ],
            fecha_entrada__lt=fecha_hasta,
            fecha_salida__gt=fecha_desde,
        )
        disponible = (
            not reservas_conflictivas.exists()
            and habitacion.estado != Habitacion.ESTADO_MANTENIMIENTO
        )
        habitaciones_disponibles.append({
            'habitacion': habitacion,
            'disponible': disponible,
        })
    
    context = {
        'habitaciones': habitaciones_disponibles,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    }
    return render(request, 'hotel/habitaciones/disponibilidad.html', context)


# ========== CHECK-IN / CHECK-OUT ==========

def lista_checkins(request):
    """Lista todos los check-ins"""
    checkins = CheckIn.objects.all().select_related('reserva', 'reserva__huesped', 'reserva__habitacion')
    checkins = checkins.order_by('-fecha_hora')
    
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    if fecha_desde:
        checkins = checkins.filter(fecha_hora__date__gte=fecha_desde)
    if fecha_hasta:
        checkins = checkins.filter(fecha_hora__date__lte=fecha_hasta)
    
    context = {
        'checkins': checkins,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    }
    return render(request, 'hotel/checkin/lista.html', context)


def realizar_checkin(request, reserva_id):
    """Realizar check-in de una reserva"""
    reserva = get_object_or_404(Reserva, id=reserva_id)
    hoy = timezone.localdate()

    if _checkin_reserva(reserva) is not None:
        messages.warning(request, 'Esta reserva ya tiene un check-in registrado.')
        return redirect('detalle_reserva', reserva_id=reserva.id)

    if reserva.estado in (Reserva.ESTADO_CANCELADA, Reserva.ESTADO_CHECKOUT):
        messages.error(request, 'No se puede hacer check-in en una reserva cancelada o ya con check-out.')
        return redirect('detalle_reserva', reserva_id=reserva.id)
    if reserva.estado not in (Reserva.ESTADO_PENDIENTE, Reserva.ESTADO_CONFIRMADA):
        messages.error(request, 'Solo se puede hacer check-in con reserva pendiente o confirmada.')
        return redirect('detalle_reserva', reserva_id=reserva.id)
    if reserva.fecha_entrada > hoy:
        messages.error(request, 'No se puede hacer check-in antes de la fecha de entrada de la reserva.')
        return redirect('detalle_reserva', reserva_id=reserva.id)
    
    if request.method == 'POST':
        form = CheckInForm(request.POST)
        if form.is_valid():
            checkin = form.save(commit=False)
            checkin.reserva = reserva
            checkin.fecha_hora = timezone.now()
            checkin.empleado = _nombre_empleado_checkin(request.user)
            checkin.save()
            
            reserva.estado = Reserva.ESTADO_CHECKIN
            reserva.save(update_fields=['estado', 'fecha_actualizacion'])
            reserva.habitacion.estado = Habitacion.ESTADO_OCUPADA
            reserva.habitacion.save(update_fields=['estado'])
            
            messages.success(request, f'Check-in realizado exitosamente para la reserva #{reserva.id}.')
            return redirect('detalle_reserva', reserva_id=reserva.id)
    else:
        form = CheckInForm()

    return render(request, 'hotel/checkin/realizar.html', {'form': form, 'reserva': reserva})


def lista_checkouts(request):
    """Lista todos los check-outs"""
    checkouts = CheckOut.objects.all().select_related(
        'reserva', 'reserva__huesped', 'reserva__habitacion', 'registrado_por'
    )
    checkouts = checkouts.order_by('-fecha_hora')
    
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    if fecha_desde:
        checkouts = checkouts.filter(fecha_hora__date__gte=fecha_desde)
    if fecha_hasta:
        checkouts = checkouts.filter(fecha_hora__date__lte=fecha_hasta)
    
    context = {
        'checkouts': checkouts,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    }
    return render(request, 'hotel/checkout/lista.html', context)


def realizar_checkout(request, reserva_id):
    """Realizar check-out de una reserva"""
    reserva = get_object_or_404(Reserva, id=reserva_id)
    
    if _checkin_reserva(reserva) is None:
        messages.warning(request, 'No se puede realizar check-out sin un check-in previo.')
        return redirect('detalle_reserva', reserva_id=reserva.id)
    
    if _checkout_reserva(reserva) is not None:
        messages.warning(request, 'Esta reserva ya tiene un check-out registrado.')
        return redirect('detalle_reserva', reserva_id=reserva.id)

    if reserva.estado != Reserva.ESTADO_CHECKIN:
        messages.error(request, 'Solo se puede hacer check-out con reserva en estado check-in.')
        return redirect('detalle_reserva', reserva_id=reserva.id)
    
    if request.method == 'POST':
        form = CheckOutForm(request.POST)
        if form.is_valid():
            checkout = form.save(commit=False)
            checkout.reserva = reserva
            checkout.fecha_hora = timezone.now()
            checkout.registrado_por = request.user
            checkout.save()
            
            reserva.estado = Reserva.ESTADO_CHECKOUT
            reserva.save(update_fields=['estado', 'fecha_actualizacion'])
            reserva.habitacion.estado = Habitacion.ESTADO_LIMPIEZA
            reserva.habitacion.save(update_fields=['estado'])
            
            messages.success(request, f'Check-out realizado exitosamente para la reserva #{reserva.id}.')
            return redirect('detalle_reserva', reserva_id=reserva.id)
    else:
        form = CheckOutForm(initial={'total_pagado': reserva.precio_total})

    return render(request, 'hotel/checkout/realizar.html', {'form': form, 'reserva': reserva})


# ========== GESTIÓN DE HUÉSPEDES ==========

# ========== REPORTES Y ANÁLISIS ==========

def reportes(request):
    """Página principal de reportes"""
    return render(request, 'hotel/reportes/index.html')


def _resolver_rango_fechas(request, dias_default=30):
    """
    Resuelve y sanea el rango de fechas para reportes.
    - Si formato es inválido, usa últimos `dias_default` días.
    - Si fecha_desde > fecha_hasta, intercambia para evitar errores.
    """
    hoy = timezone.localdate()
    fecha_desde_raw = request.GET.get('fecha_desde')
    fecha_hasta_raw = request.GET.get('fecha_hasta')

    try:
        fecha_desde = datetime.strptime(fecha_desde_raw, '%Y-%m-%d').date() if fecha_desde_raw else (hoy - timedelta(days=dias_default))
    except (ValueError, TypeError):
        fecha_desde = hoy - timedelta(days=dias_default)

    try:
        fecha_hasta = datetime.strptime(fecha_hasta_raw, '%Y-%m-%d').date() if fecha_hasta_raw else hoy
    except (ValueError, TypeError):
        fecha_hasta = hoy

    if fecha_desde > fecha_hasta:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde

    return fecha_desde, fecha_hasta


def reporte_ocupacion(request):
    """Reporte de ocupación del hotel"""
    fecha_desde, fecha_hasta = _resolver_rango_fechas(request)
    
    # Calcular ocupación por día
    ocupacion_por_dia = []
    fecha_actual = fecha_desde
    fecha_fin = fecha_hasta
    
    total_habitaciones = Habitacion.objects.count()
    
    while fecha_actual <= fecha_fin:
        # Noches con huésped en casa (excluye canceladas; incluye checkout si aún cubre la noche).
        reservas_activas = (
            Reserva.objects.filter(
                fecha_entrada__lte=fecha_actual,
                fecha_salida__gt=fecha_actual,
            )
            .exclude(estado=Reserva.ESTADO_CANCELADA)
            .count()
        )

        porcentaje_raw = (reservas_activas / total_habitaciones * 100) if total_habitaciones > 0 else 0
        porcentaje = min(100.0, round(porcentaje_raw, 2))

        ocupacion_por_dia.append({
            'fecha': fecha_actual,
            'ocupadas': reservas_activas,
            'disponibles': total_habitaciones - reservas_activas,
            'porcentaje': porcentaje,
        })
        fecha_actual += timedelta(days=1)
    
    # Estadísticas generales
    reservas_periodo = Reserva.objects.filter(
        fecha_entrada__gte=fecha_desde,
        fecha_entrada__lte=fecha_hasta,
    ).exclude(estado=Reserva.ESTADO_CANCELADA)
    
    total_reservas = reservas_periodo.count()
    ingresos_totales = reservas_periodo.aggregate(Sum('precio_total'))['precio_total__sum'] or 0
    ocupacion_promedio = sum(d['porcentaje'] for d in ocupacion_por_dia) / len(ocupacion_por_dia) if ocupacion_por_dia else 0

    checkins_detalle = list(
        CheckIn.objects.filter(
            fecha_hora__date__gte=fecha_desde,
            fecha_hora__date__lte=fecha_hasta,
        )
        .select_related('reserva', 'reserva__huesped', 'reserva__habitacion')
        .order_by('-fecha_hora')
    )
    checkouts_detalle = list(
        CheckOut.objects.filter(
            fecha_hora__date__gte=fecha_desde,
            fecha_hora__date__lte=fecha_hasta,
        )
        .select_related('reserva', 'reserva__huesped', 'reserva__habitacion', 'registrado_por')
        .order_by('-fecha_hora')
    )

    context = {
        'ocupacion_por_dia': ocupacion_por_dia,
        'fecha_desde': fecha_desde.isoformat(),
        'fecha_hasta': fecha_hasta.isoformat(),
        'fecha_desde_fmt': fecha_desde.strftime('%d/%m/%Y'),
        'fecha_hasta_fmt': fecha_hasta.strftime('%d/%m/%Y'),
        'total_reservas': total_reservas,
        'ingresos_totales': ingresos_totales,
        'ocupacion_promedio': round(ocupacion_promedio, 2),
        'total_habitaciones': total_habitaciones,
        'checkins_detalle': checkins_detalle,
        'checkouts_detalle': checkouts_detalle,
    }
    return render(request, 'hotel/reportes/ocupacion.html', context)


def reporte_ingresos(request):
    """Reporte de ingresos"""
    fecha_desde, fecha_hasta = _resolver_rango_fechas(request)
    
    # Ingresos por reservas (excluye canceladas)
    reservas = Reserva.objects.filter(
        fecha_entrada__gte=fecha_desde,
        fecha_entrada__lte=fecha_hasta,
    ).exclude(estado=Reserva.ESTADO_CANCELADA)
    
    ingresos_reservas = reservas.aggregate(Sum('precio_total'))['precio_total__sum'] or 0
    
    # Ingresos por check-outs (pagos reales)
    checkouts = CheckOut.objects.filter(
        fecha_hora__date__gte=fecha_desde,
        fecha_hora__date__lte=fecha_hasta,
    )

    ingresos_checkouts = checkouts.aggregate(Sum('total_pagado'))['total_pagado__sum'] or 0

    checkouts_detalle = list(
        checkouts.select_related(
            'reserva', 'reserva__huesped', 'reserva__habitacion', 'registrado_por'
        ).order_by('-fecha_hora')
    )
    checkins_detalle = list(
        CheckIn.objects.filter(
            fecha_hora__date__gte=fecha_desde,
            fecha_hora__date__lte=fecha_hasta,
        )
        .select_related('reserva', 'reserva__huesped', 'reserva__habitacion')
        .order_by('-fecha_hora')
    )

    # Ingresos por método de pago (etiquetas legibles)
    metodo_pago_labels = dict(CheckOut.METODO_PAGO_CHOICES)
    ingresos_por_metodo = list(
        checkouts.values('metodo_pago').annotate(total=Sum('total_pagado')).order_by('-total')
    )
    for row in ingresos_por_metodo:
        code = row.get('metodo_pago')
        row['metodo_display'] = metodo_pago_labels.get(code, code or '—')
    
    # Ingresos por tipo de habitación
    tipo_labels = dict(Habitacion.TIPO_CHOICES)
    ingresos_por_tipo = list(
        reservas.values('habitacion__tipo').annotate(
            total=Sum('precio_total'),
            cantidad=Count('id')
        ).order_by('-total')
    )
    for row in ingresos_por_tipo:
        code = row.get('habitacion__tipo')
        row['tipo_display'] = tipo_labels.get(code, code or '—')

    depositos_checkin = (
        CheckIn.objects.filter(
            fecha_hora__date__gte=fecha_desde,
            fecha_hora__date__lte=fecha_hasta,
            deposito__gt=0,
        ).aggregate(Sum('deposito'))['deposito__sum']
        or 0
    )

    metodo_dep_labels = dict(CheckIn.METODO_DEPOSITO_CHOICES)
    depositos_por_metodo = list(
        CheckIn.objects.filter(
            fecha_hora__date__gte=fecha_desde,
            fecha_hora__date__lte=fecha_hasta,
            deposito__gt=0,
            metodo_deposito__isnull=False,
        )
        .values('metodo_deposito')
        .annotate(total=Sum('deposito'))
        .order_by('-total')
    )
    for row in depositos_por_metodo:
        code = row.get('metodo_deposito')
        row['metodo_display'] = metodo_dep_labels.get(code, code or '—')

    context = {
        'fecha_desde': fecha_desde.isoformat(),
        'fecha_hasta': fecha_hasta.isoformat(),
        'fecha_desde_fmt': fecha_desde.strftime('%d/%m/%Y'),
        'fecha_hasta_fmt': fecha_hasta.strftime('%d/%m/%Y'),
        'ingresos_reservas': ingresos_reservas,
        'ingresos_checkouts': ingresos_checkouts,
        'depositos_checkin': depositos_checkin,
        'depositos_por_metodo': depositos_por_metodo,
        'ingresos_por_metodo': ingresos_por_metodo,
        'ingresos_por_tipo': ingresos_por_tipo,
        'checkins_detalle': checkins_detalle,
        'checkouts_detalle': checkouts_detalle,
    }
    return render(request, 'hotel/reportes/ingresos.html', context)


# ========== NUEVAS FUNCIONALIDADES DE RECEPCIÓN ==========

def checkin_rapido(request):
    """Lista de check-ins pendientes con acción rápida"""
    hoy = timezone.localdate()
    
    # Check-ins pendientes de hoy
    checkins_pendientes = (
        Reserva.objects.filter(
            estado=Reserva.ESTADO_CONFIRMADA,
            fecha_entrada__lte=hoy,
            fecha_salida__gt=hoy,
        )
        .annotate(_tiene_ci=Exists(CheckIn.objects.filter(reserva_id=OuterRef('pk'))))
        .filter(_tiene_ci=False)
        .select_related('huesped', 'habitacion')
        .order_by('fecha_entrada')
    )
    
    # Si hay un ID específico, hacer check-in directo
    reserva_id = request.GET.get('reserva_id')
    if reserva_id:
        reserva = get_object_or_404(Reserva, id=reserva_id, estado=Reserva.ESTADO_CONFIRMADA)
        
        if request.method == 'POST':
            from decimal import Decimal

            documentos_recibidos = request.POST.get('documentos_recibidos') == 'on'
            deposito_str = request.POST.get('deposito', '0') or '0'
            metodo_deposito = request.POST.get('metodo_deposito', '').strip()
            try:
                deposito = Decimal(str(deposito_str))
            except Exception:
                messages.error(request, 'Depósito no válido.')
                return redirect(f'{reverse("checkin_rapido")}?reserva_id={reserva.id}')
            metodos_validos = {CheckIn.DEPOSITO_EFECTIVO, CheckIn.DEPOSITO_YAPE, CheckIn.DEPOSITO_TRANSFERENCIA}
            if deposito > 0 and metodo_deposito not in metodos_validos:
                messages.error(request, 'Si hay depósito, indique si fue por Yape, efectivo o transferencia.')
                return redirect(f'{reverse("checkin_rapido")}?reserva_id={reserva.id}')

            CheckIn.objects.create(
                reserva=reserva,
                fecha_hora=timezone.now(),
                empleado=_nombre_empleado_checkin(request.user),
                documentos_recibidos=documentos_recibidos,
                deposito=deposito,
                metodo_deposito=metodo_deposito if deposito > 0 else None,
            )
            
            reserva.estado = Reserva.ESTADO_CHECKIN
            reserva.save()
            reserva.habitacion.estado = Habitacion.ESTADO_OCUPADA
            reserva.habitacion.save()
            
            messages.success(request, f'Check-in realizado para Reserva #{reserva.id}.')
            return redirect('checkin_rapido')
        
        context = {
            'reserva': reserva,
            'hacer_checkin': True,
            'empleado_registrado': _nombre_empleado_checkin(request.user),
        }
        return render(request, 'hotel/recepcion/checkin_rapido.html', context)
    
    context = {
        'checkins_pendientes': checkins_pendientes,
        'hoy': hoy,
    }
    return render(request, 'hotel/recepcion/checkin_rapido.html', context)


def checkout_rapido(request):
    """Lista de check-outs pendientes con acción rápida"""
    hoy = timezone.localdate()
    
    # Todas las estancias con check-in activo (incluye salida anticipada: pagaron noche completa y se van antes de fecha_salida)
    checkouts_pendientes = (
        Reserva.objects.filter(estado=Reserva.ESTADO_CHECKIN)
        .annotate(
            _tiene_ci=Exists(CheckIn.objects.filter(reserva_id=OuterRef('pk'))),
            prioridad_salida=Case(
                When(fecha_salida__lte=hoy, then=0),
                default=1,
                output_field=IntegerField(),
            ),
        )
        .filter(_tiene_ci=True)
        .select_related('huesped', 'habitacion', 'checkin')
        .order_by('prioridad_salida', 'fecha_salida', 'fecha_hora_salida_prevista', 'id')
    )
    
    # Si hay un ID específico, hacer check-out directo
    reserva_id = request.GET.get('reserva_id')
    if reserva_id:
        reserva = get_object_or_404(Reserva, id=reserva_id, estado=Reserva.ESTADO_CHECKIN)
        
        if _checkin_reserva(reserva) is None:
            messages.warning(request, 'No se puede realizar check-out sin check-in previo.')
            return redirect('checkout_rapido')
        
        if request.method == 'POST':
            from decimal import Decimal
            total_pagado_str = request.POST.get('total_pagado', str(reserva.precio_total)) or str(reserva.precio_total)
            metodo_pago = request.POST.get('metodo_pago', 'efectivo')
            calificacion_str = request.POST.get('calificacion') or None
            danos_observados = request.POST.get('danos_observados', '').strip()
            
            # Convertir tipos
            try:
                total_pagado = Decimal(str(total_pagado_str))
                calificacion = int(calificacion_str) if calificacion_str and calificacion_str.isdigit() else None
            except (ValueError, TypeError):
                messages.error(request, 'Error en los datos ingresados. Por favor verifique los valores.')
                return redirect('checkout_rapido')
            
            # El formulario envía el monto a cobrar en check-out (saldo), ya neto del depósito.
            total_cobrado = max(Decimal('0'), total_pagado)

            CheckOut.objects.create(
                reserva=reserva,
                fecha_hora=timezone.now(),
                registrado_por=request.user,
                total_pagado=total_cobrado,
                metodo_pago=metodo_pago,
                calificacion=calificacion,
                danos_observados=danos_observados,
            )
            
            reserva.estado = Reserva.ESTADO_CHECKOUT
            reserva.save()
            reserva.habitacion.estado = Habitacion.ESTADO_LIMPIEZA
            reserva.habitacion.save()
            
            messages.success(request, f'Check-out realizado para Reserva #{reserva.id}.')
            return redirect('checkout_rapido')
        
        # Calcular total a pagar (precio - depósito)
        ci = _checkin_reserva(reserva)
        deposito = ci.deposito if ci else 0
        total_a_pagar = float(reserva.precio_total) - float(deposito)
        
        context = {
            'reserva': reserva,
            'deposito': deposito,
            'total_a_pagar': total_a_pagar,
            'hacer_checkout': True,
        }
        return render(request, 'hotel/recepcion/checkout_rapido.html', context)
    
    context = {
        'checkouts_pendientes': checkouts_pendientes,
        'hoy': hoy,
    }
    return render(request, 'hotel/recepcion/checkout_rapido.html', context)


def busqueda_rapida(request):
    """Búsqueda rápida global"""
    query = request.GET.get('q', '').strip()
    resultados = {
        'reservas': [],
        'habitaciones': [],
    }
    
    if query:
        # Buscar reservas
        resultados['reservas'] = Reserva.objects.filter(
            Q(id__icontains=query) |
            Q(huesped__nombre__icontains=query) |
            Q(huesped__apellidos__icontains=query) |
            Q(huesped__documento_identidad__icontains=query) |
            Q(huesped__lugar_procedencia__icontains=query) |
            Q(habitacion__numero__icontains=query)
        ).select_related('huesped', 'habitacion')[:5]
        
        # Buscar habitaciones
        resultados['habitaciones'] = Habitacion.objects.filter(
            Q(numero__icontains=query)
        )[:5]
    
    return JsonResponse({
        'reservas': [
            {
                'id': r.id,
                'huesped': r.huesped.nombre_completo,
                'habitacion': r.habitacion.numero,
                'estado': r.get_estado_display(),
                'url': f'/reservas/{r.id}/'
            } for r in resultados['reservas']
        ],
        'habitaciones': [
            {
                'id': h.id,
                'numero': h.numero,
                'tipo': h.get_tipo_display(),
                'estado': h.get_estado_display(),
                'url': f'/habitaciones/{h.id}/'
            } for h in resultados['habitaciones']
        ],
    })


def tablero_habitaciones(request):
    """Tablero tipo Kanban por estado, con resumen y reservas activas por habitación."""
    activos_estados = [
        Reserva.ESTADO_PENDIENTE,
        Reserva.ESTADO_CONFIRMADA,
        Reserva.ESTADO_CHECKIN,
    ]
    reservas_activas_qs = (
        Reserva.objects.filter(estado__in=activos_estados)
        .select_related('huesped')
        .order_by('fecha_entrada', 'id')
    )

    def habitaciones_por_columna(estado):
        return (
            Habitacion.objects.filter(estado=estado)
            .annotate(
                reserva_activa=Count(
                    'reservas',
                    filter=Q(reservas__estado__in=activos_estados),
                )
            )
            .prefetch_related(
                Prefetch(
                    'reservas',
                    queryset=reservas_activas_qs,
                    to_attr='reservas_activas_prefetched',
                )
            )
            .order_by('numero')
        )

    columnas_meta = [
        ('disponible', 'Disponible', 'success', 'bi-door-open'),
        ('ocupada', 'Ocupada', 'danger', 'bi-person-fill'),
        ('reservada', 'Reservada', 'warning', 'bi-calendar-check'),
        ('limpieza', 'En limpieza', 'info', 'bi-droplet-half'),
        ('mantenimiento', 'Mantenimiento', 'secondary', 'bi-tools'),
    ]
    columnas = []
    for estado_key, label, variant, icon in columnas_meta:
        habitaciones = list(habitaciones_por_columna(estado_key))
        columnas.append(
            {
                'estado': estado_key,
                'label': label,
                'bs_variant': variant,
                'icon': icon,
                'habitaciones': habitaciones,
                'count': len(habitaciones),
            }
        )

    total = Habitacion.objects.count()
    n_disponible = next(c['count'] for c in columnas if c['estado'] == 'disponible')
    n_ocupada = next(c['count'] for c in columnas if c['estado'] == 'ocupada')
    n_reservada = next(c['count'] for c in columnas if c['estado'] == 'reservada')
    n_limpieza = next(c['count'] for c in columnas if c['estado'] == 'limpieza')
    n_mantenimiento = next(c['count'] for c in columnas if c['estado'] == 'mantenimiento')
    ocupacion_pct = round((n_ocupada / total) * 100, 1) if total else 0.0

    context = {
        'columnas': columnas,
        'total_habitaciones': total,
        'n_disponible': n_disponible,
        'n_ocupada': n_ocupada,
        'n_reservada': n_reservada,
        'n_limpieza': n_limpieza,
        'n_mantenimiento': n_mantenimiento,
        'ocupacion_pct': ocupacion_pct,
        'ahora': timezone.localtime(timezone.now()),
    }
    return render(request, 'hotel/recepcion/tablero_habitaciones.html', context)


def walkin(request):
    """Check-in sin reserva previa (walk-in): por noches o por horas (salida prevista con fecha y hora)."""
    if request.method == 'POST':
        documento = request.POST.get('documento_identidad', '').strip()
        nombre = request.POST.get('nombre', '').strip()
        apellidos = request.POST.get('apellidos', '').strip()
        lugar_procedencia = request.POST.get('lugar_procedencia', '').strip()
        habitacion_id = request.POST.get('habitacion')
        numero_huespedes_str = request.POST.get('numero_huespedes', '1')
        noches_str = request.POST.get('noches', '1')
        tipo_estadia = request.POST.get('tipo_estadia', 'noches').strip()
        duracion_horas_str = request.POST.get('duracion_horas', '3')
        precio_acordado_str = (request.POST.get('precio_acordado') or '').strip()
        documentos_recibidos = request.POST.get('documentos_recibidos') == 'on'
        deposito_str = request.POST.get('deposito', '0') or '0'
        metodo_deposito = request.POST.get('metodo_deposito', '').strip()

        try:
            from decimal import Decimal

            ahora = timezone.localtime(timezone.now())
            fecha_entrada = ahora.date()
            fecha_hora_salida_prevista = None
            fecha_salida = None
            precio_total = None

            numero_huespedes = int(numero_huespedes_str)
            deposito = Decimal(str(deposito_str))

            if not documento or not nombre or not apellidos or not lugar_procedencia:
                messages.error(request, 'Complete DNI, nombres, apellidos y lugar de procedencia del huésped.')
                return redirect('walkin')

            # Buscar o crear huésped
            huesped, created = Huesped.objects.get_or_create(
                documento_identidad=documento,
                defaults={
                    'nombre': nombre,
                    'apellidos': apellidos,
                    'lugar_procedencia': lugar_procedencia,
                    'email': '',
                    'telefono': '',
                },
            )
            if not created:
                huesped.nombre = nombre
                huesped.apellidos = apellidos
                huesped.lugar_procedencia = lugar_procedencia
                huesped.save(update_fields=['nombre', 'apellidos', 'lugar_procedencia', 'fecha_actualizacion'])
            
            habitacion = get_object_or_404(Habitacion, id=habitacion_id)
            if habitacion.estado != Habitacion.ESTADO_DISPONIBLE:
                messages.error(request, 'La habitación ya no está disponible. Elija otra e intente de nuevo.')
                return redirect('walkin')
            
            # Validar capacidad
            if numero_huespedes > habitacion.capacidad:
                messages.error(request, f'El número de huéspedes ({numero_huespedes}) excede la capacidad de la habitación ({habitacion.capacidad}).')
                return redirect('walkin')

            metodos_validos = {CheckIn.DEPOSITO_EFECTIVO, CheckIn.DEPOSITO_YAPE, CheckIn.DEPOSITO_TRANSFERENCIA}
            if deposito > 0 and metodo_deposito not in metodos_validos:
                messages.error(request, 'Si hay depósito, indique si fue por Yape, efectivo o transferencia.')
                return redirect('walkin')
            metodo_deposito_val = metodo_deposito if deposito > 0 else None

            if tipo_estadia == 'horas':
                try:
                    duracion_horas = int(duracion_horas_str)
                except (TypeError, ValueError):
                    duracion_horas = 3
                duracion_horas = max(1, min(duracion_horas, 72))
                fecha_hora_salida_prevista = ahora + timedelta(hours=duracion_horas)
                fecha_salida = fecha_hora_salida_prevista.date()
                if fecha_salida < fecha_entrada:
                    fecha_salida = fecha_entrada

                if precio_acordado_str:
                    precio_total = Decimal(precio_acordado_str.replace(',', '.'))
                    if precio_total < 0:
                        raise ValueError('El precio acordado no puede ser negativo.')
                else:
                    horas_d = Decimal(duracion_horas)
                    proporcional = (habitacion.precio_noche * (horas_d / Decimal(24))).quantize(
                        Decimal('0.01')
                    )
                    minimo = (habitacion.precio_noche * Decimal('0.15')).quantize(Decimal('0.01'))
                    precio_total = max(proporcional, minimo)

                msg_extra = (
                    f'estadía por horas (~{duracion_horas} h), salida prevista '
                    f'{timezone.localtime(fecha_hora_salida_prevista).strftime("%d/%m/%Y %H:%M")}'
                )
            else:
                try:
                    noches = int(noches_str)
                except (TypeError, ValueError):
                    noches = 1
                noches = max(1, noches)
                fecha_salida = fecha_entrada + timedelta(days=noches)
                precio_total = None
                msg_extra = f'{noches} noche(s), salida {fecha_salida.strftime("%d/%m/%Y")}'
            
            # Crear reserva y check-in inmediato
            create_kwargs = dict(
                huesped=huesped,
                habitacion=habitacion,
                fecha_entrada=fecha_entrada,
                fecha_salida=fecha_salida,
                numero_huespedes=numero_huespedes,
                estado=Reserva.ESTADO_CHECKIN,
                fecha_hora_salida_prevista=fecha_hora_salida_prevista,
            )
            if precio_total is not None:
                create_kwargs['precio_total'] = precio_total
            if request.user.is_authenticated:
                create_kwargs['creado_por'] = request.user
            reserva = Reserva.objects.create(**create_kwargs)
            
            CheckIn.objects.create(
                reserva=reserva,
                fecha_hora=timezone.now(),
                empleado=_nombre_empleado_checkin(request.user),
                documentos_recibidos=documentos_recibidos,
                deposito=deposito,
                metodo_deposito=metodo_deposito_val,
            )
            
            habitacion.estado = Habitacion.ESTADO_OCUPADA
            habitacion.save()
            
            messages.success(
                request,
                f'Walk-in registrado (reserva #{reserva.id}). Entrada: {fecha_entrada.strftime("%d/%m/%Y")}, '
                f'{msg_extra}. Check-in con fecha y hora actuales.',
            )
            return redirect('detalle_reserva', reserva_id=reserva.id)
            
        except ValueError as e:
            messages.error(request, f'Error en los datos ingresados: {str(e)}')
            return redirect('walkin')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('walkin')
    
    # GET: Mostrar formulario
    habitaciones_disponibles = Habitacion.objects.filter(
        estado=Habitacion.ESTADO_DISPONIBLE
    ).order_by('numero')
    
    context = {
        'habitaciones': habitaciones_disponibles,
        'entrada_automatica': timezone.localtime(timezone.now()),
    }
    return render(request, 'hotel/recepcion/walkin.html', context)


def calendario_ocupacion(request):
    """Vista de calendario con ocupación"""
    mes = request.GET.get('mes', timezone.now().month)
    año = request.GET.get('año', timezone.now().year)
    
    try:
        mes = int(mes)
        año = int(año)
    except (ValueError, TypeError):
        mes = timezone.now().month
        año = timezone.now().year
    
    # Obtener todas las reservas del mes
    fecha_inicio = datetime(año, mes, 1).date()
    if mes == 12:
        fecha_fin = datetime(año + 1, 1, 1).date() - timedelta(days=1)
    else:
        fecha_fin = datetime(año, mes + 1, 1).date() - timedelta(days=1)
    
    reservas = Reserva.objects.filter(
        Q(fecha_entrada__lte=fecha_fin, fecha_salida__gte=fecha_inicio)
    ).select_related('huesped', 'habitacion')
    
    # Organizar por día
    ocupacion_por_dia = {}
    for reserva in reservas:
        fecha_actual = max(reserva.fecha_entrada, fecha_inicio)
        fecha_final = min(reserva.fecha_salida, fecha_fin)
        
        while fecha_actual <= fecha_final:
            if fecha_actual not in ocupacion_por_dia:
                ocupacion_por_dia[fecha_actual] = []
            ocupacion_por_dia[fecha_actual].append(reserva)
            fecha_actual += timedelta(days=1)
    
    context = {
        'mes': mes,
        'año': año,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'ocupacion_por_dia': ocupacion_por_dia,
        'reservas': reservas,
    }
    return render(request, 'hotel/recepcion/calendario.html', context)


@require_http_methods(['POST'])
def actualizar_estado_habitacion(request, habitacion_id):
    """Cambio de estado de habitación (admin: cualquier estado; limpieza: sin ocupada/reservada)."""
    habitacion = get_object_or_404(Habitacion, id=habitacion_id)
    role = request.membership.role
    nuevo = request.POST.get('estado')
    validos = {c[0] for c in Habitacion.ESTADO_CHOICES}
    if nuevo not in validos:
        messages.error(request, 'Estado no válido.')
        return redirect('detalle_habitacion', habitacion_id=habitacion.id)

    if role == Membership.ROLE_LIMPIEZA:
        if habitacion.estado in (Habitacion.ESTADO_OCUPADA, Habitacion.ESTADO_RESERVADA):
            messages.error(request, 'No puedes modificar habitaciones ocupadas o reservadas.')
            return redirect('detalle_habitacion', habitacion_id=habitacion.id)
        if nuevo in (Habitacion.ESTADO_OCUPADA, Habitacion.ESTADO_RESERVADA):
            messages.error(request, 'Tu rol no puede dejar la habitación en ese estado.')
            return redirect('detalle_habitacion', habitacion_id=habitacion.id)
    elif role != Membership.ROLE_ADMIN:
        messages.error(request, 'No tienes permiso para esta acción.')
        return redirect('detalle_habitacion', habitacion_id=habitacion.id)

    habitacion.estado = nuevo
    habitacion.save()
    messages.success(request, f'Estado actualizado: {habitacion.get_estado_display()}')
    return redirect('detalle_habitacion', habitacion_id=habitacion.id)


def lista_equipo(request):
    """Listado de usuarios del hotel (solo administrador)."""
    miembros = (
        Membership.objects.filter(tenant=request.tenant)
        .select_related('user')
        .order_by('role', 'user__username')
    )
    ingreso_path = reverse('accounts_ingreso_con_hotel', kwargs={'tenant_slug': request.tenant.slug})
    ingreso_url = request.build_absolute_uri(ingreso_path)
    return render(
        request,
        'hotel/equipo/lista.html',
        {'miembros': miembros, 'ingreso_url': ingreso_url},
    )


def crear_equipo(request):
    """Crear cuenta de recepción o limpieza para el hotel actual."""
    form = CrearPersonalHotelForm(request.POST or None, tenant=request.tenant)
    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data['username'].strip()
        role = form.cleaned_data['role']
        pwd = form.cleaned_data['password1']
        user = User.objects.create_user(username=username, email='', password=pwd)
        Membership.objects.create(user=user, tenant=request.tenant, role=role)
        role_label = dict(Membership.ROLE_CHOICES).get(role, role)
        messages.success(
            request,
            f'Cuenta creada para el usuario «{username}» como {role_label}. '
            f'Comparte el enlace de ingreso del listado de equipo: allí elige el mismo rol, este usuario y la contraseña.',
        )
        return redirect('lista_equipo')
    return render(request, 'hotel/equipo/crear.html', {'form': form})


@require_http_methods(['POST'])
def eliminar_equipo(request, membership_id):
    """Quita recepción o limpieza del hotel (no administradores ni a ti mismo)."""
    m = get_object_or_404(Membership, pk=membership_id, tenant=request.tenant)
    if m.user_id == request.user.id:
        messages.error(request, 'No puedes eliminarte a ti mismo.')
        return redirect('lista_equipo')
    if m.role == Membership.ROLE_ADMIN:
        messages.error(request, 'No se puede dar de baja a un administrador desde aquí.')
        return redirect('lista_equipo')
    username = m.user.get_username()
    m.delete()
    messages.success(request, f'Se quitó del equipo a {username}.')
    return redirect('lista_equipo')

