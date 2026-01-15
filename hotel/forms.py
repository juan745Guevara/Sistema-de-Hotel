from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Habitacion, Huesped, Reserva, CheckIn, CheckOut


class HuespedForm(forms.ModelForm):
    class Meta:
        model = Huesped
        fields = ['nombre', 'apellidos', 'email', 'telefono', 'documento_identidad', 
                  'nacionalidad', 'fecha_nacimiento', 'preferencias', 'notas']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'documento_identidad': forms.TextInput(attrs={'class': 'form-control'}),
            'nacionalidad': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_nacimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'preferencias': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class HabitacionForm(forms.ModelForm):
    class Meta:
        model = Habitacion
        fields = ['numero', 'tipo', 'estado', 'capacidad', 'precio_noche', 'descripcion', 'servicios']
        widgets = {
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'capacidad': forms.NumberInput(attrs={'class': 'form-control'}),
            'precio_noche': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'servicios': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ReservaForm(forms.ModelForm):
    class Meta:
        model = Reserva
        fields = ['huesped', 'habitacion', 'fecha_entrada', 'fecha_salida', 'numero_huespedes', 'notas']
        widgets = {
            'huesped': forms.Select(attrs={'class': 'form-control'}),
            'habitacion': forms.Select(attrs={'class': 'form-control'}),
            'fecha_entrada': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_salida': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'numero_huespedes': forms.NumberInput(attrs={'class': 'form-control'}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        fecha_entrada = cleaned_data.get('fecha_entrada')
        fecha_salida = cleaned_data.get('fecha_salida')
        habitacion = cleaned_data.get('habitacion')
        numero_huespedes = cleaned_data.get('numero_huespedes')
        
        if fecha_entrada and fecha_salida:
            if fecha_entrada >= fecha_salida:
                raise ValidationError('La fecha de salida debe ser posterior a la fecha de entrada.')
            
            if fecha_entrada < timezone.now().date():
                raise ValidationError('La fecha de entrada no puede ser en el pasado.')
        
        if habitacion and numero_huespedes:
            if numero_huespedes > habitacion.capacidad:
                raise ValidationError(f'El número de huéspedes ({numero_huespedes}) excede la capacidad de la habitación ({habitacion.capacidad}).')
        
        # Verificar disponibilidad de la habitación
        if habitacion and fecha_entrada and fecha_salida:
            reservas_conflictivas = Reserva.objects.filter(
                habitacion=habitacion,
                estado__in=['pendiente', 'confirmada', 'checkin'],
                fecha_entrada__lt=fecha_salida,
                fecha_salida__gt=fecha_entrada
            )
            # Excluir la reserva actual si estamos editando
            if self.instance.pk:
                reservas_conflictivas = reservas_conflictivas.exclude(pk=self.instance.pk)
            
            if reservas_conflictivas.exists():
                raise ValidationError('La habitación no está disponible en las fechas seleccionadas.')
        
        return cleaned_data


class CheckInForm(forms.ModelForm):
    class Meta:
        model = CheckIn
        fields = ['fecha_hora', 'empleado', 'documentos_recibidos', 'deposito', 'notas']
        widgets = {
            'fecha_hora': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'empleado': forms.TextInput(attrs={'class': 'form-control'}),
            'documentos_recibidos': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'deposito': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class CheckOutForm(forms.ModelForm):
    class Meta:
        model = CheckOut
        fields = ['fecha_hora', 'empleado', 'total_pagado', 'metodo_pago', 'danos_observados', 'calificacion', 'notas']
        widgets = {
            'fecha_hora': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'empleado': forms.TextInput(attrs={'class': 'form-control'}),
            'total_pagado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'metodo_pago': forms.Select(attrs={'class': 'form-control'}),
            'danos_observados': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'calificacion': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


