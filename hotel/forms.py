from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Habitacion, Huesped, Membership, Reserva, CheckIn, CheckOut


class HuespedForm(forms.ModelForm):
    """Registro básico de huésped: DNI, nombres, apellidos y lugar de procedencia."""

    class Meta:
        model = Huesped
        fields = ['documento_identidad', 'nombre', 'apellidos', 'lugar_procedencia']
        widgets = {
            'documento_identidad': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'lugar_procedencia': forms.TextInput(attrs={'class': 'form-control'}),
        }


class HabitacionForm(forms.ModelForm):
    class Meta:
        model = Habitacion
        fields = ['numero', 'tipo', 'estado', 'capacidad', 'precio_noche', 'descripcion', 'servicios']
        labels = {
            'precio_noche': 'Precio por noche (soles)',
        }
        help_texts = {
            'precio_noche': 'Monto en soles (S/).',
        }
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
    """Siempre registra o actualiza el huésped por DNI + datos (sin desplegable de huéspedes)."""

    habitacion = forms.ModelChoiceField(
        label='Habitación',
        queryset=Habitacion.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    huesped_documento = forms.CharField(
        label='DNI',
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. 12345678'}),
    )
    huesped_nombre = forms.CharField(
        label='Nombres',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    huesped_apellidos = forms.CharField(
        label='Apellidos',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    huesped_lugar_procedencia = forms.CharField(
        label='Lugar de procedencia',
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ciudad o país de origen'}),
    )

    class Meta:
        model = Reserva
        fields = ['habitacion', 'fecha_entrada', 'fecha_salida', 'numero_huespedes', 'notas']
        widgets = {
            'fecha_entrada': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_salida': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'numero_huespedes': forms.NumberInput(attrs={'class': 'form-control'}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        qs = Habitacion.objects.all().order_by('numero')
        self.fields['habitacion'].queryset = qs
        self.fields['habitacion'].label_from_instance = (
            lambda obj: f'Hab. {obj.numero} — {obj.get_tipo_display()} ({obj.get_estado_display()})'
        )

        if self.instance.pk and self.instance.huesped_id:
            h = self.instance.huesped
            self.fields['huesped_documento'].initial = h.documento_identidad
            self.fields['huesped_nombre'].initial = h.nombre
            self.fields['huesped_apellidos'].initial = h.apellidos
            self.fields['huesped_lugar_procedencia'].initial = h.lugar_procedencia

        self.order_fields(
            [
                'huesped_documento',
                'huesped_nombre',
                'huesped_apellidos',
                'huesped_lugar_procedencia',
                'habitacion',
                'fecha_entrada',
                'fecha_salida',
                'numero_huespedes',
                'notas',
            ]
        )

    def clean(self):
        cleaned_data = super().clean()
        fecha_entrada = cleaned_data.get('fecha_entrada')
        fecha_salida = cleaned_data.get('fecha_salida')
        habitacion = cleaned_data.get('habitacion')
        numero_huespedes = cleaned_data.get('numero_huespedes')

        doc = (cleaned_data.get('huesped_documento') or '').strip()
        if doc:
            cleaned_data['huesped_documento'] = doc
            if self.instance.pk and self.instance.huesped_id:
                actual = self.instance.huesped
                if doc != actual.documento_identidad:
                    if Huesped.objects.filter(documento_identidad=doc).exclude(pk=actual.pk).exists():
                        self.add_error(
                            'huesped_documento',
                            'Ya existe otro huésped con este DNI en el hotel.',
                        )

        if fecha_entrada and fecha_salida:
            if fecha_entrada >= fecha_salida:
                raise ValidationError('La fecha de salida debe ser posterior a la fecha de entrada.')

            # Comparar con el calendario local del hotel (TIME_ZONE), no con la fecha UTC.
            if not self.instance.pk and fecha_entrada < timezone.localdate():
                raise ValidationError('La fecha de entrada no puede ser en el pasado.')

        if habitacion and numero_huespedes:
            if numero_huespedes > habitacion.capacidad:
                raise ValidationError(
                    f'El número de huéspedes ({numero_huespedes}) excede la capacidad de la habitación ({habitacion.capacidad}).'
                )

        if habitacion and fecha_entrada and fecha_salida:
            reservas_conflictivas = Reserva.objects.filter(
                habitacion=habitacion,
                estado__in=[
                    Reserva.ESTADO_PENDIENTE,
                    Reserva.ESTADO_CONFIRMADA,
                    Reserva.ESTADO_CHECKIN,
                ],
                fecha_entrada__lt=fecha_salida,
                fecha_salida__gt=fecha_entrada,
            )
            if self.instance.pk:
                reservas_conflictivas = reservas_conflictivas.exclude(pk=self.instance.pk)

            if reservas_conflictivas.exists():
                otra = reservas_conflictivas.first()
                raise ValidationError(
                    f'La habitación no está disponible en esas fechas: ya hay una reserva activa '
                    f'(#{otra.id}, {otra.get_estado_display()}, {otra.fecha_entrada} → {otra.fecha_salida}).'
                )

        return cleaned_data

    def save(self, commit=True):
        reserva = super().save(commit=False)
        d = self.cleaned_data
        doc = d['huesped_documento']

        if not self.instance.pk:
            huesped, created = Huesped.objects.get_or_create(
                documento_identidad=doc,
                defaults={
                    'nombre': d['huesped_nombre'],
                    'apellidos': d['huesped_apellidos'],
                    'lugar_procedencia': d['huesped_lugar_procedencia'],
                    'email': '',
                    'telefono': '',
                },
            )
            if not created:
                huesped.nombre = d['huesped_nombre']
                huesped.apellidos = d['huesped_apellidos']
                huesped.lugar_procedencia = d['huesped_lugar_procedencia']
                huesped.save(
                    update_fields=['nombre', 'apellidos', 'lugar_procedencia', 'fecha_actualizacion']
                )
            reserva.huesped = huesped
        else:
            huesped = self.instance.huesped
            huesped.documento_identidad = doc
            huesped.nombre = d['huesped_nombre']
            huesped.apellidos = d['huesped_apellidos']
            huesped.lugar_procedencia = d['huesped_lugar_procedencia']
            huesped.save(
                update_fields=[
                    'documento_identidad',
                    'nombre',
                    'apellidos',
                    'lugar_procedencia',
                    'fecha_actualizacion',
                ]
            )
            reserva.huesped = huesped

        if commit:
            reserva.save()
        return reserva


class CheckInForm(forms.ModelForm):
    """La fecha y hora de entrada y el empleado se asignan al confirmar (servidor / usuario de la sesión)."""

    class Meta:
        model = CheckIn
        fields = ['documentos_recibidos', 'deposito', 'metodo_deposito', 'notas']
        labels = {
            'deposito': 'Depósito (soles)',
            'metodo_deposito': 'Método del depósito',
        }
        help_texts = {
            'deposito': 'Monto en soles (S/).',
            'metodo_deposito': 'Solo si hay depósito: Yape, efectivo o transferencia.',
        }
        widgets = {
            'documentos_recibidos': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'deposito': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'metodo_deposito': forms.Select(attrs={'class': 'form-control'}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['metodo_deposito'].required = False
        self.fields['metodo_deposito'].choices = [
            ('', '— (sin depósito) —'),
        ] + list(CheckIn.METODO_DEPOSITO_CHOICES)

    def clean(self):
        from decimal import Decimal

        cleaned = super().clean()
        dep = cleaned.get('deposito')
        if dep is None:
            dep = Decimal('0')
        met = cleaned.get('metodo_deposito')
        if met in (None, ''):
            met = None
            cleaned['metodo_deposito'] = None
        if dep > 0 and not met:
            raise ValidationError(
                {'metodo_deposito': 'Si hay depósito, indique si fue por Yape, efectivo o transferencia.'}
            )
        if dep <= 0:
            cleaned['metodo_deposito'] = None
        return cleaned


class CheckOutForm(forms.ModelForm):
    """La fecha y hora de salida se guardan al confirmar (servidor). Quién registra va por la sesión."""

    class Meta:
        model = CheckOut
        fields = ['total_pagado', 'metodo_pago', 'danos_observados', 'calificacion', 'notas']
        labels = {
            'total_pagado': 'Total pagado (soles)',
        }
        help_texts = {
            'total_pagado': 'Monto en soles (S/).',
        }
        widgets = {
            'total_pagado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'metodo_pago': forms.Select(attrs={'class': 'form-control'}),
            'danos_observados': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'calificacion': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class CrearPersonalHotelForm(forms.Form):
    """Alta de recepción o limpieza en el hotel actual (solo usa el administrador)."""

    username = forms.CharField(
        max_length=150,
        label='Nombre de usuario',
        help_text='Identificador para iniciar sesión (paso 2), junto con la contraseña.',
        validators=[UnicodeUsernameValidator()],
    )
    role = forms.ChoiceField(
        label='Rol',
        choices=[
            (Membership.ROLE_RECEPCION, 'Recepción'),
            (Membership.ROLE_LIMPIEZA, 'Personal de limpieza'),
        ],
    )
    password1 = forms.CharField(
        label='Contraseña inicial',
        min_length=8,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
        help_text='Mínimo 8 caracteres. Comunícala de forma segura a la persona.',
    )
    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
    )

    def __init__(self, *args, tenant, **kwargs):
        self.tenant = tenant
        super().__init__(*args, **kwargs)
        for fname, field in self.fields.items():
            w = field.widget
            if isinstance(w, (forms.TextInput, forms.EmailInput, forms.NumberInput)):
                w.attrs.setdefault('class', 'form-control')
            if isinstance(w, forms.Select):
                w.attrs.setdefault('class', 'form-select')

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError(
                'Este nombre de usuario ya está registrado. Cada persona debe tener un usuario distinto; '
                'si necesitas enlazar un usuario existente con este hotel, hazlo desde el administrador de Django.'
            )
        return username

    def clean(self):
        data = super().clean()
        p1, p2 = data.get('password1'), data.get('password2')
        if p1 and p2 and p1 != p2:
            raise ValidationError('Las contraseñas no coinciden.')
        return data


