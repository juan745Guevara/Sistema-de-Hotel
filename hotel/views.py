from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta
from .models import Habitacion, Huesped, Reserva, CheckIn, CheckOut
from .forms import HuespedForm, HabitacionForm, ReservaForm, CheckInForm, CheckOutForm


def index(request):
    """Dashboard de recepción mejorado con tareas del día"""
    hoy = timezone.now().date()
    ahora = timezone.now()
    
    # Estadísticas rápidas
    total_habitaciones = Habitacion.objects.count()
    habitaciones_disponibles = Habitacion.objects.filter(estado='disponible').count()
    habitaciones_ocupadas = Habitacion.objects.filter(estado='ocupada').count()
    habitaciones_limpieza = Habitacion.objects.filter(estado='limpieza').count()
    
    # Check-ins pendientes de hoy
    checkins_pendientes = Reserva.objects.filter(
        fecha_entrada=hoy,
        estado=Reserva.ESTADO_CONFIRMADA
    ).select_related('huesped', 'habitacion').order_by('fecha_entrada')[:10]
    
    # Check-outs programados para hoy
    checkouts_hoy = Reserva.objects.filter(
        fecha_salida=hoy,
        estado=Reserva.ESTADO_CHECKIN
    ).select_related('huesped', 'habitacion').order_by('fecha_salida')[:10]
    
    # Check-outs próximos (próximas 2 horas)
    hora_limite = ahora + timedelta(hours=2)
    checkouts_proximos = Reserva.objects.filter(
        fecha_salida=hoy,
        estado=Reserva.ESTADO_CHECKIN
    ).select_related('huesped', 'habitacion')[:5]
    
    # Habitaciones en limpieza por más de 2 horas
    habitaciones_limpieza_largas = Habitacion.objects.filter(
        estado='limpieza'
    )[:5]
    
    # Reservas recientes
    reservas_recientes = Reserva.objects.all().select_related('huesped', 'habitacion').order_by('-fecha_creacion')[:5]
    
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
    reservas = Reserva.objects.all().select_related('huesped', 'habitacion')
    
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
            # Actualizar estado de la habitación
            reserva.habitacion.estado = 'reservada'
            reserva.habitacion.save()
            messages.success(request, f'Reserva #{reserva.id} creada exitosamente.')
            return redirect('detalle_reserva', reserva_id=reserva.id)
    else:
        form = ReservaForm()
    
    return render(request, 'hotel/reservas/crear.html', {'form': form})


def detalle_reserva(request, reserva_id):
    """Ver detalles de una reserva"""
    reserva = get_object_or_404(Reserva, id=reserva_id)
    checkin = getattr(reserva, 'checkin', None)
    checkout = getattr(reserva, 'checkout', None)
    
    context = {
        'reserva': reserva,
        'checkin': checkin,
        'checkout': checkout,
    }
    return render(request, 'hotel/reservas/detalle.html', context)


def editar_reserva(request, reserva_id):
    """Editar una reserva existente"""
    reserva = get_object_or_404(Reserva, id=reserva_id)
    
    if request.method == 'POST':
        form = ReservaForm(request.POST, instance=reserva)
        if form.is_valid():
            form.save()
            messages.success(request, f'Reserva #{reserva.id} actualizada exitosamente.')
            return redirect('detalle_reserva', reserva_id=reserva.id)
    else:
        form = ReservaForm(instance=reserva)
    
    return render(request, 'hotel/reservas/editar.html', {'form': form, 'reserva': reserva})


def cancelar_reserva(request, reserva_id):
    """Cancelar una reserva"""
    reserva = get_object_or_404(Reserva, id=reserva_id)
    
    if request.method == 'POST':
        reserva.estado = 'cancelada'
        reserva.habitacion.estado = 'disponible'
        reserva.habitacion.save()
        reserva.save()
        messages.success(request, f'Reserva #{reserva.id} cancelada exitosamente.')
        return redirect('lista_reservas')
    
    return render(request, 'hotel/reservas/cancelar.html', {'reserva': reserva})


# ========== CONTROL DE HABITACIONES ==========

def lista_habitaciones(request):
    """Lista todas las habitaciones con su estado"""
    habitaciones = Habitacion.objects.all().annotate(
        reservas_activas=Count('reservas', filter=Q(reservas__estado__in=['pendiente', 'confirmada', 'checkin']))
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
            estado__in=['pendiente', 'confirmada', 'checkin'],
            fecha_entrada__lt=fecha_hasta,
            fecha_salida__gt=fecha_desde
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


def disponibilidad_habitaciones(request):
    """Ver disponibilidad de habitaciones en un rango de fechas"""
    fecha_desde = request.GET.get('fecha_desde', timezone.now().date().isoformat())
    fecha_hasta = request.GET.get('fecha_hasta', (timezone.now().date() + timedelta(days=7)).isoformat())
    
    habitaciones = Habitacion.objects.all()
    habitaciones_disponibles = []
    
    for habitacion in habitaciones:
        reservas_conflictivas = Reserva.objects.filter(
            habitacion=habitacion,
            estado__in=['pendiente', 'confirmada', 'checkin'],
            fecha_entrada__lt=fecha_hasta,
            fecha_salida__gt=fecha_desde
        )
        disponible = not reservas_conflictivas.exists() and habitacion.estado != 'mantenimiento'
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
    
    if hasattr(reserva, 'checkin'):
        messages.warning(request, 'Esta reserva ya tiene un check-in registrado.')
        return redirect('detalle_reserva', reserva_id=reserva.id)
    
    if request.method == 'POST':
        form = CheckInForm(request.POST)
        if form.is_valid():
            checkin = form.save(commit=False)
            checkin.reserva = reserva
            checkin.save()
            
            # Actualizar estado de reserva y habitación
            reserva.estado = 'checkin'
            reserva.save()
            reserva.habitacion.estado = 'ocupada'
            reserva.habitacion.save()
            
            messages.success(request, f'Check-in realizado exitosamente para la reserva #{reserva.id}.')
            return redirect('detalle_reserva', reserva_id=reserva.id)
    else:
        form = CheckInForm(initial={'fecha_hora': timezone.now()})
    
    return render(request, 'hotel/checkin/realizar.html', {'form': form, 'reserva': reserva})


def lista_checkouts(request):
    """Lista todos los check-outs"""
    checkouts = CheckOut.objects.all().select_related('reserva', 'reserva__huesped', 'reserva__habitacion')
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
    
    if not hasattr(reserva, 'checkin'):
        messages.warning(request, 'No se puede realizar check-out sin un check-in previo.')
        return redirect('detalle_reserva', reserva_id=reserva.id)
    
    if hasattr(reserva, 'checkout'):
        messages.warning(request, 'Esta reserva ya tiene un check-out registrado.')
        return redirect('detalle_reserva', reserva_id=reserva.id)
    
    if request.method == 'POST':
        form = CheckOutForm(request.POST)
        if form.is_valid():
            checkout = form.save(commit=False)
            checkout.reserva = reserva
            checkout.save()
            
            # Actualizar estado de reserva y habitación
            reserva.estado = 'checkout'
            reserva.save()
            reserva.habitacion.estado = 'limpieza'
            reserva.habitacion.save()
            
            messages.success(request, f'Check-out realizado exitosamente para la reserva #{reserva.id}.')
            return redirect('detalle_reserva', reserva_id=reserva.id)
    else:
        # Pre-llenar el total con el precio de la reserva
        form = CheckOutForm(initial={
            'fecha_hora': timezone.now(),
            'total_pagado': reserva.precio_total,
        })
    
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
    hoy = timezone.now().date()
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
        reservas_activas = Reserva.objects.filter(
            fecha_entrada__lte=fecha_actual,
            fecha_salida__gt=fecha_actual,
            estado__in=['confirmada', 'checkin']
        ).count()
        
        porcentaje = (reservas_activas / total_habitaciones * 100) if total_habitaciones > 0 else 0
        
        ocupacion_por_dia.append({
            'fecha': fecha_actual,
            'ocupadas': reservas_activas,
            'disponibles': total_habitaciones - reservas_activas,
            'porcentaje': round(porcentaje, 2),
        })
        fecha_actual += timedelta(days=1)
    
    # Estadísticas generales
    reservas_periodo = Reserva.objects.filter(
        fecha_entrada__gte=fecha_desde,
        fecha_entrada__lte=fecha_hasta
    )
    
    total_reservas = reservas_periodo.count()
    ingresos_totales = reservas_periodo.aggregate(Sum('precio_total'))['precio_total__sum'] or 0
    ocupacion_promedio = sum(d['porcentaje'] for d in ocupacion_por_dia) / len(ocupacion_por_dia) if ocupacion_por_dia else 0
    
    context = {
        'ocupacion_por_dia': ocupacion_por_dia,
        'fecha_desde': fecha_desde.isoformat(),
        'fecha_hasta': fecha_hasta.isoformat(),
        'total_reservas': total_reservas,
        'ingresos_totales': ingresos_totales,
        'ocupacion_promedio': round(ocupacion_promedio, 2),
        'total_habitaciones': total_habitaciones,
    }
    return render(request, 'hotel/reportes/ocupacion.html', context)


def reporte_ingresos(request):
    """Reporte de ingresos"""
    fecha_desde, fecha_hasta = _resolver_rango_fechas(request)
    
    # Ingresos por reservas
    reservas = Reserva.objects.filter(
        fecha_entrada__gte=fecha_desde,
        fecha_entrada__lte=fecha_hasta
    )
    
    ingresos_reservas = reservas.aggregate(Sum('precio_total'))['precio_total__sum'] or 0
    
    # Ingresos por check-outs (pagos reales)
    checkouts = CheckOut.objects.filter(
        fecha_hora__date__gte=fecha_desde,
        fecha_hora__date__lte=fecha_hasta
    )
    
    ingresos_checkouts = checkouts.aggregate(Sum('total_pagado'))['total_pagado__sum'] or 0
    
    # Ingresos por método de pago
    ingresos_por_metodo = checkouts.values('metodo_pago').annotate(
        total=Sum('total_pagado')
    ).order_by('-total')
    
    # Ingresos por tipo de habitación
    ingresos_por_tipo = reservas.values('habitacion__tipo').annotate(
        total=Sum('precio_total'),
        cantidad=Count('id')
    ).order_by('-total')
    
    context = {
        'fecha_desde': fecha_desde.isoformat(),
        'fecha_hasta': fecha_hasta.isoformat(),
        'ingresos_reservas': ingresos_reservas,
        'ingresos_checkouts': ingresos_checkouts,
        'ingresos_por_metodo': ingresos_por_metodo,
        'ingresos_por_tipo': ingresos_por_tipo,
    }
    return render(request, 'hotel/reportes/ingresos.html', context)


# ========== NUEVAS FUNCIONALIDADES DE RECEPCIÓN ==========

def checkin_rapido(request):
    """Lista de check-ins pendientes con acción rápida"""
    hoy = timezone.now().date()
    
    # Check-ins pendientes de hoy
    checkins_pendientes = Reserva.objects.filter(
        fecha_entrada__lte=hoy,
        estado=Reserva.ESTADO_CONFIRMADA
    ).select_related('huesped', 'habitacion').order_by('fecha_entrada')
    
    # Si hay un ID específico, hacer check-in directo
    reserva_id = request.GET.get('reserva_id')
    if reserva_id:
        reserva = get_object_or_404(Reserva, id=reserva_id, estado=Reserva.ESTADO_CONFIRMADA)
        
        if request.method == 'POST':
            empleado = request.POST.get('empleado', '').strip()
            documentos_recibidos = request.POST.get('documentos_recibidos') == 'on'
            deposito = request.POST.get('deposito', 0) or 0
            
            CheckIn.objects.create(
                reserva=reserva,
                fecha_hora=timezone.now(),
                empleado=empleado,
                documentos_recibidos=documentos_recibidos,
                deposito=deposito or 0,
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
        }
        return render(request, 'hotel/recepcion/checkin_rapido.html', context)
    
    context = {
        'checkins_pendientes': checkins_pendientes,
        'hoy': hoy,
    }
    return render(request, 'hotel/recepcion/checkin_rapido.html', context)


def checkout_rapido(request):
    """Lista de check-outs pendientes con acción rápida"""
    hoy = timezone.now().date()
    
    # Check-outs pendientes de hoy
    checkouts_pendientes = Reserva.objects.filter(
        fecha_salida__lte=hoy,
        estado=Reserva.ESTADO_CHECKIN
    ).select_related('huesped', 'habitacion', 'checkin').order_by('fecha_salida')
    
    # Si hay un ID específico, hacer check-out directo
    reserva_id = request.GET.get('reserva_id')
    if reserva_id:
        reserva = get_object_or_404(Reserva, id=reserva_id, estado=Reserva.ESTADO_CHECKIN)
        
        if not hasattr(reserva, 'checkin'):
            messages.warning(request, 'No se puede realizar check-out sin check-in previo.')
            return redirect('checkout_rapido')
        
        if request.method == 'POST':
            from decimal import Decimal
            empleado = request.POST.get('empleado', '').strip()
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
            
            # Calcular total considerando depósito
            deposito = reserva.checkin.deposito if hasattr(reserva, 'checkin') else Decimal('0')
            total_final = total_pagado - deposito
            
            CheckOut.objects.create(
                reserva=reserva,
                fecha_hora=timezone.now(),
                empleado=empleado,
                total_pagado=total_final if total_final > 0 else reserva.precio_total,
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
        deposito = reserva.checkin.deposito if hasattr(reserva, 'checkin') else 0
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
    """Vista tipo Kanban de habitaciones por estado"""
    estados = [
        ('disponible', 'Disponible', 'success'),
        ('ocupada', 'Ocupada', 'danger'),
        ('reservada', 'Reservada', 'warning'),
        ('limpieza', 'En Limpieza', 'info'),
        ('mantenimiento', 'Mantenimiento', 'dark'),
    ]
    
    habitaciones_disponibles = Habitacion.objects.filter(estado='disponible').annotate(
        reserva_activa=Count('reservas', filter=Q(reservas__estado__in=[
            Reserva.ESTADO_PENDIENTE, Reserva.ESTADO_CONFIRMADA, Reserva.ESTADO_CHECKIN
        ]))
    ).order_by('numero')
    
    habitaciones_ocupadas = Habitacion.objects.filter(estado='ocupada').annotate(
        reserva_activa=Count('reservas', filter=Q(reservas__estado__in=[
            Reserva.ESTADO_PENDIENTE, Reserva.ESTADO_CONFIRMADA, Reserva.ESTADO_CHECKIN
        ]))
    ).order_by('numero')
    
    habitaciones_reservadas = Habitacion.objects.filter(estado='reservada').annotate(
        reserva_activa=Count('reservas', filter=Q(reservas__estado__in=[
            Reserva.ESTADO_PENDIENTE, Reserva.ESTADO_CONFIRMADA, Reserva.ESTADO_CHECKIN
        ]))
    ).order_by('numero')
    
    habitaciones_limpieza = Habitacion.objects.filter(estado='limpieza').annotate(
        reserva_activa=Count('reservas', filter=Q(reservas__estado__in=[
            Reserva.ESTADO_PENDIENTE, Reserva.ESTADO_CONFIRMADA, Reserva.ESTADO_CHECKIN
        ]))
    ).order_by('numero')
    
    habitaciones_mantenimiento = Habitacion.objects.filter(estado='mantenimiento').annotate(
        reserva_activa=Count('reservas', filter=Q(reservas__estado__in=[
            Reserva.ESTADO_PENDIENTE, Reserva.ESTADO_CONFIRMADA, Reserva.ESTADO_CHECKIN
        ]))
    ).order_by('numero')
    
    context = {
        'estados': estados,
        'habitaciones_disponibles': habitaciones_disponibles,
        'habitaciones_ocupadas': habitaciones_ocupadas,
        'habitaciones_reservadas': habitaciones_reservadas,
        'habitaciones_limpieza': habitaciones_limpieza,
        'habitaciones_mantenimiento': habitaciones_mantenimiento,
    }
    return render(request, 'hotel/recepcion/tablero_habitaciones.html', context)


def walkin(request):
    """Check-in sin reserva previa (walk-in)"""
    if request.method == 'POST':
        documento = request.POST.get('documento_identidad', '').strip()
        nombre = request.POST.get('nombre', '').strip()
        apellidos = request.POST.get('apellidos', '').strip()
        email = request.POST.get('email', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        habitacion_id = request.POST.get('habitacion')
        fecha_entrada_str = request.POST.get('fecha_entrada')
        fecha_salida_str = request.POST.get('fecha_salida')
        numero_huespedes_str = request.POST.get('numero_huespedes', '1')
        empleado = request.POST.get('empleado', '').strip()
        documentos_recibidos = request.POST.get('documentos_recibidos') == 'on'
        deposito_str = request.POST.get('deposito', '0') or '0'
        
        try:
            # Convertir tipos de datos
            from decimal import Decimal
            fecha_entrada = datetime.strptime(fecha_entrada_str, '%Y-%m-%d').date()
            fecha_salida = datetime.strptime(fecha_salida_str, '%Y-%m-%d').date()
            numero_huespedes = int(numero_huespedes_str)
            deposito = Decimal(str(deposito_str))
            
            # Validar fechas
            if fecha_entrada >= fecha_salida:
                messages.error(request, 'La fecha de salida debe ser posterior a la fecha de entrada.')
                return redirect('walkin')
            
            # Buscar o crear huésped
            huesped, _ = Huesped.objects.get_or_create(
                documento_identidad=documento,
                defaults={
                    'nombre': nombre,
                    'apellidos': apellidos,
                    'email': email,
                    'telefono': telefono,
                }
            )
            
            habitacion = get_object_or_404(Habitacion, id=habitacion_id)
            
            # Validar capacidad
            if numero_huespedes > habitacion.capacidad:
                messages.error(request, f'El número de huéspedes ({numero_huespedes}) excede la capacidad de la habitación ({habitacion.capacidad}).')
                return redirect('walkin')
            
            # Crear reserva y check-in inmediato
            reserva = Reserva.objects.create(
                huesped=huesped,
                habitacion=habitacion,
                fecha_entrada=fecha_entrada,
                fecha_salida=fecha_salida,
                numero_huespedes=numero_huespedes,
                estado=Reserva.ESTADO_CHECKIN,
            )
            
            CheckIn.objects.create(
                reserva=reserva,
                fecha_hora=timezone.now(),
                empleado=empleado,
                documentos_recibidos=documentos_recibidos,
                deposito=deposito,
            )
            
            habitacion.estado = Habitacion.ESTADO_OCUPADA
            habitacion.save()
            
            messages.success(request, f'Walk-in registrado. Reserva #{reserva.id} con check-in automático.')
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
    
    fecha_hoy = timezone.now().date().isoformat()
    
    context = {
        'habitaciones': habitaciones_disponibles,
        'fecha_hoy': fecha_hoy,
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

