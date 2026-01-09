from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Habitacion, Huesped, Reserva, CheckIn, CheckOut
from .forms import HuespedForm, HabitacionForm, ReservaForm, CheckInForm, CheckOutForm


def index(request):
    """Página principal del sistema"""
    hoy = timezone.now().date()
    
    # Estadísticas rápidas
    total_habitaciones = Habitacion.objects.count()
    habitaciones_disponibles = Habitacion.objects.filter(estado='disponible').count()
    reservas_hoy = Reserva.objects.filter(fecha_entrada=hoy, estado__in=['confirmada', 'checkin']).count()
    checkins_pendientes = Reserva.objects.filter(fecha_entrada=hoy, estado='confirmada').count()
    checkouts_hoy = Reserva.objects.filter(fecha_salida=hoy, estado='checkin').count()
    
    # Reservas recientes
    reservas_recientes = Reserva.objects.all().order_by('-fecha_creacion')[:10]
    
    context = {
        'total_habitaciones': total_habitaciones,
        'habitaciones_disponibles': habitaciones_disponibles,
        'reservas_hoy': reservas_hoy,
        'checkins_pendientes': checkins_pendientes,
        'checkouts_hoy': checkouts_hoy,
        'reservas_recientes': reservas_recientes,
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

def lista_huespedes(request):
    """Lista todos los huéspedes"""
    huespedes = Huesped.objects.all()
    
    busqueda = request.GET.get('busqueda')
    if busqueda:
        huespedes = huespedes.filter(
            Q(nombre__icontains=busqueda) |
            Q(apellidos__icontains=busqueda) |
            Q(email__icontains=busqueda) |
            Q(documento_identidad__icontains=busqueda)
        )
    
    huespedes = huespedes.order_by('apellidos', 'nombre')
    
    context = {
        'huespedes': huespedes,
        'busqueda': busqueda,
    }
    return render(request, 'hotel/huespedes/lista.html', context)


def detalle_huesped(request, huesped_id):
    """Ver detalles de un huésped"""
    huesped = get_object_or_404(Huesped, id=huesped_id)
    reservas = huesped.reservas.all().order_by('-fecha_creacion')
    
    # Estadísticas del huésped
    total_reservas = reservas.count()
    total_noches = sum(r.numero_noches for r in reservas if r.numero_noches)
    reservas_activas = reservas.filter(estado__in=['pendiente', 'confirmada', 'checkin']).count()
    
    context = {
        'huesped': huesped,
        'reservas': reservas,
        'total_reservas': total_reservas,
        'total_noches': total_noches,
        'reservas_activas': reservas_activas,
    }
    return render(request, 'hotel/huespedes/detalle.html', context)


def crear_huesped(request):
    """Crear un nuevo huésped"""
    if request.method == 'POST':
        form = HuespedForm(request.POST)
        if form.is_valid():
            huesped = form.save()
            messages.success(request, f'Huésped {huesped.nombre_completo} creado exitosamente.')
            return redirect('detalle_huesped', huesped_id=huesped.id)
    else:
        form = HuespedForm()
    
    return render(request, 'hotel/huespedes/crear.html', {'form': form})


def editar_huesped(request, huesped_id):
    """Editar un huésped existente"""
    huesped = get_object_or_404(Huesped, id=huesped_id)
    
    if request.method == 'POST':
        form = HuespedForm(request.POST, instance=huesped)
        if form.is_valid():
            form.save()
            messages.success(request, f'Huésped {huesped.nombre_completo} actualizado exitosamente.')
            return redirect('detalle_huesped', huesped_id=huesped.id)
    else:
        form = HuespedForm(instance=huesped)
    
    return render(request, 'hotel/huespedes/editar.html', {'form': form, 'huesped': huesped})


# ========== REPORTES Y ANÁLISIS ==========

def reportes(request):
    """Página principal de reportes"""
    return render(request, 'hotel/reportes/index.html')


def reporte_ocupacion(request):
    """Reporte de ocupación del hotel"""
    fecha_desde = request.GET.get('fecha_desde', (timezone.now().date() - timedelta(days=30)).isoformat())
    fecha_hasta = request.GET.get('fecha_hasta', timezone.now().date().isoformat())
    
    # Calcular ocupación por día
    ocupacion_por_dia = []
    fecha_actual = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
    fecha_fin = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
    
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
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'total_reservas': total_reservas,
        'ingresos_totales': ingresos_totales,
        'ocupacion_promedio': round(ocupacion_promedio, 2),
        'total_habitaciones': total_habitaciones,
    }
    return render(request, 'hotel/reportes/ocupacion.html', context)


def reporte_ingresos(request):
    """Reporte de ingresos"""
    fecha_desde = request.GET.get('fecha_desde', (timezone.now().date() - timedelta(days=30)).isoformat())
    fecha_hasta = request.GET.get('fecha_hasta', timezone.now().date().isoformat())
    
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
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'ingresos_reservas': ingresos_reservas,
        'ingresos_checkouts': ingresos_checkouts,
        'ingresos_por_metodo': ingresos_por_metodo,
        'ingresos_por_tipo': ingresos_por_tipo,
    }
    return render(request, 'hotel/reportes/ingresos.html', context)


def reporte_huespedes(request):
    """Reporte de huéspedes"""
    # Top huéspedes por número de reservas
    top_huespedes_list = Huesped.objects.annotate(
        total_reservas=Count('reservas'),
        total_gastado=Sum('reservas__precio_total')
    ).order_by('-total_reservas')[:10]
    
    # Calcular total_noches para cada huésped
    top_huespedes = []
    for huesped in top_huespedes_list:
        reservas = huesped.reservas.all()
        total_noches = sum(r.numero_noches for r in reservas if r.numero_noches)
        top_huespedes.append({
            'id': huesped.id,
            'nombre_completo': huesped.nombre_completo,
            'total_reservas': huesped.total_reservas,
            'total_noches': total_noches,
            'total_gastado': huesped.total_gastado or 0,
        })
    
    # Estadísticas generales
    total_huespedes = Huesped.objects.count()
    huespedes_activos = Huesped.objects.filter(
        reservas__estado__in=['pendiente', 'confirmada', 'checkin']
    ).distinct().count()
    
    # Nacionalidades más comunes
    nacionalidades = Huesped.objects.values('nacionalidad').annotate(
        cantidad=Count('id')
    ).order_by('-cantidad')[:10]
    
    context = {
        'top_huespedes': top_huespedes,
        'total_huespedes': total_huespedes,
        'huespedes_activos': huespedes_activos,
        'nacionalidades': nacionalidades,
    }
    return render(request, 'hotel/reportes/huespedes.html', context)

