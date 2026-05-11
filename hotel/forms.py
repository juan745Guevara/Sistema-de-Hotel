import re
from datetime import timedelta
from decimal import Decimal

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Habitacion, Huesped, Membership, Reserva, CheckIn, CheckOut


def normalizar_y_validar_documento_huesped(tipo: str, raw: str) -> str:
    """
    Valida y normaliza el número según el tipo.
    DNI Perú: 8 dígitos. CE / pasaporte / otro: alfanumérico, 4–50 caracteres.
    """
    if tipo == Huesped.TIPO_DOC_DNI:
        num = re.sub(r'\D', '', raw or '')
        if not re.fullmatch(r'\d{8}', num):
            raise ValidationError('El DNI peruano debe tener exactamente 8 dígitos.')
        return num
    s = (raw or '').strip().upper().replace(' ', '')
    if len(s) < 4:
        raise ValidationError('El documento debe tener al menos 4 caracteres.')
    if len(s) > 50:
        raise ValidationError('El documento no puede superar 50 caracteres.')
    if not re.fullmatch(r'[A-Z0-9.\-]+', s):
        raise ValidationError('Use solo letras, números, puntos o guiones.')
    return s


class HuespedForm(forms.ModelForm):
    """Registro básico de huésped: tipo de documento, número, nombres y procedencia."""

    class Meta:
        model = Huesped
        fields = ['tipo_documento', 'documento_identidad', 'nombre', 'apellidos', 'lugar_procedencia']
        widgets = {
            'tipo_documento': forms.Select(attrs={'class': 'form-select'}),
            'documento_identidad': forms.TextInput(
                attrs={'class': 'form-control', 'autocomplete': 'off'}
            ),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'given-name'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'family-name'}),
            'lugar_procedencia': forms.TextInput(
                attrs={'class': 'form-control', 'autocomplete': 'address-level2'}
            ),
        }

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get('tipo_documento')
        raw = cleaned.get('documento_identidad')
        try:
            cleaned['documento_identidad'] = normalizar_y_validar_documento_huesped(tipo, raw)
        except ValidationError as e:
            self.add_error('documento_identidad', e.messages[0])
        return cleaned


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
    """Registra o actualiza el huésped por tipo + número de documento y datos."""

    habitacion = forms.ModelChoiceField(
        label='Habitación',
        queryset=Habitacion.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    huesped_tipo_documento = forms.ChoiceField(
        label='Tipo de documento del huésped',
        choices=Huesped.TIPO_DOCUMENTO_CHOICES,
        initial=Huesped.TIPO_DOC_DNI,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    huesped_documento = forms.CharField(
        label='Número de documento',
        max_length=50,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Ej. 12345678 o número de CE / pasaporte',
                'autocomplete': 'off',
            }
        ),
    )
    huesped_nombre = forms.CharField(
        label='Nombres',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'given-name'}),
    )
    huesped_apellidos = forms.CharField(
        label='Apellidos',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'family-name'}),
    )
    huesped_lugar_procedencia = forms.CharField(
        label='Lugar de procedencia',
        max_length=200,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Ciudad o país de origen',
                'autocomplete': 'address-level2',
            }
        ),
    )

    huesped_nacionalidad = forms.ChoiceField(
        label='Nacionalidad',
        required=False,
        choices=[('', '—')] + list(Huesped.NACIONALIDADES_CHOICES),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    huesped_fecha_nacimiento = forms.DateField(
        label='Fecha de nacimiento',
        required=False,
        widget=forms.DateInput(
            attrs={'class': 'form-control', 'type': 'date', 'autocomplete': 'bday'}
        ),
    )

    huesped_sexo = forms.ChoiceField(
        label='Sexo',
        required=False,
        choices=[('', '—')] + list(getattr(Huesped, 'SEXO_CHOICES', [])),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = Reserva
        fields = ['habitacion', 'fecha_entrada', 'fecha_salida', 'numero_huespedes', 'notas']
        widgets = {
            'fecha_entrada': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date', 'autocomplete': 'off'}
            ),
            'fecha_salida': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date', 'autocomplete': 'off'}
            ),
            'numero_huespedes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        help_texts = {
            'fecha_entrada': 'Primer día de la estadía (ingreso habitual ese día).',
            'fecha_salida': (
                'Día de checkout. Política del hotel: cada noche incluye la habitación hasta las '
                '12:00 (mediodía) de este día. Ej.: 1 noche = entrada un día y salida el día siguiente '
                'al mediodía; 2 noches = salida dos días después al mediodía, etc.'
            ),
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
            self.fields['huesped_tipo_documento'].initial = h.tipo_documento
            self.fields['huesped_documento'].initial = h.documento_identidad
            self.fields['huesped_nombre'].initial = h.nombre
            self.fields['huesped_apellidos'].initial = h.apellidos
            self.fields['huesped_lugar_procedencia'].initial = h.lugar_procedencia
            self.fields['huesped_nacionalidad'].initial = h.nacionalidad
            self.fields['huesped_fecha_nacimiento'].initial = h.fecha_nacimiento
            self.fields['huesped_sexo'].initial = h.sexo
        elif not self.instance.pk:
            # Defaults para que DNI pase válido incluso sin interacción del usuario.
            self.fields['huesped_nacionalidad'].initial = Huesped.NACIONALIDAD_PERU

        self.order_fields(
            [
                'huesped_tipo_documento',
                'huesped_documento',
                'huesped_nombre',
                'huesped_apellidos',
                'huesped_lugar_procedencia',
                'huesped_nacionalidad',
                'huesped_fecha_nacimiento',
                'huesped_sexo',
                'habitacion',
                'fecha_entrada',
                'fecha_salida',
                'numero_huespedes',
                'notas',
            ]
        )

        if not self.instance.pk:
            hoy = timezone.localdate()
            self.fields['fecha_entrada'].initial = hoy
            self.fields['fecha_salida'].initial = hoy + timedelta(days=1)
            self.fields['numero_huespedes'].initial = 1

    def clean(self):
        cleaned_data = super().clean()
        fecha_entrada = cleaned_data.get('fecha_entrada')
        fecha_salida = cleaned_data.get('fecha_salida')
        habitacion = cleaned_data.get('habitacion')
        numero_huespedes = cleaned_data.get('numero_huespedes')

        tipo = cleaned_data.get('huesped_tipo_documento') or Huesped.TIPO_DOC_DNI
        doc_raw = cleaned_data.get('huesped_documento')
        try:
            doc = normalizar_y_validar_documento_huesped(tipo, doc_raw)
        except ValidationError as e:
            self.add_error('huesped_documento', e.messages[0])
            return cleaned_data
        cleaned_data['huesped_documento'] = doc

        # Regla pedida: si el tipo de documento es DNI, nacionalidad = Perú.
        if tipo == Huesped.TIPO_DOC_DNI:
            cleaned_data['huesped_nacionalidad'] = Huesped.NACIONALIDAD_PERU
        else:
            nac = cleaned_data.get('huesped_nacionalidad') or ''
            allowed = {c[0] for c in Huesped.NACIONALIDADES_CHOICES}
            if nac not in allowed:
                self.add_error('huesped_nacionalidad', 'Seleccione una nacionalidad válida.')
            cleaned_data['huesped_nacionalidad'] = nac

        if self.instance.pk and self.instance.huesped_id:
            actual = self.instance.huesped
            if (
                doc != actual.documento_identidad
                or tipo != actual.tipo_documento
            ) and Huesped.objects.filter(
                tipo_documento=tipo, documento_identidad=doc
            ).exclude(pk=actual.pk).exists():
                self.add_error(
                    'huesped_documento',
                    'Ya existe otro huésped con este tipo y número de documento en el hotel.',
                )

        if fecha_entrada and fecha_salida:
            if fecha_entrada >= fecha_salida:
                raise ValidationError('La salida debe ser después de la entrada.')

            # Comparar con el calendario local del hotel (TIME_ZONE), no con la fecha UTC.
            hoy = timezone.localdate()
            if not self.instance.pk and fecha_entrada < hoy:
                raise ValidationError('La entrada no puede estar en el pasado.')
            if self.instance.pk and fecha_entrada < hoy and fecha_entrada != self.instance.fecha_entrada:
                raise ValidationError(
                    'La nueva fecha de entrada no puede estar en el pasado.'
                )

        if habitacion and numero_huespedes:
            if numero_huespedes > habitacion.capacidad:
                raise ValidationError(
                    f'La habitación permite hasta {habitacion.capacidad} huésped(es). '
                    f'Ingresaste {numero_huespedes}.'
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
                    f'La habitación ya está ocupada en ese rango. '
                    f'Reserva detectada: #{otra.id} ({otra.fecha_entrada} a {otra.fecha_salida}).'
                )

        return cleaned_data

    def save(self, commit=True):
        reserva = super().save(commit=False)
        d = self.cleaned_data
        doc = d['huesped_documento']
        tipo = d['huesped_tipo_documento']

        if not self.instance.pk:
            huesped, created = Huesped.objects.get_or_create(
                tipo_documento=tipo,
                documento_identidad=doc,
                defaults={
                    'nombre': d['huesped_nombre'],
                    'apellidos': d['huesped_apellidos'],
                    'lugar_procedencia': d['huesped_lugar_procedencia'],
                    'nacionalidad': d.get('huesped_nacionalidad') or 'Perú',
                    'fecha_nacimiento': d.get('huesped_fecha_nacimiento'),
                    'sexo': d.get('huesped_sexo') or None,
                    'email': '',
                    'telefono': '',
                },
            )
            if not created:
                huesped.nombre = d['huesped_nombre']
                huesped.apellidos = d['huesped_apellidos']
                huesped.lugar_procedencia = d['huesped_lugar_procedencia']
                huesped.tipo_documento = tipo
                huesped.documento_identidad = doc
                huesped.nacionalidad = d.get('huesped_nacionalidad') or Huesped.NACIONALIDAD_PERU
                huesped.fecha_nacimiento = d.get('huesped_fecha_nacimiento')
                huesped.sexo = d.get('huesped_sexo') or None
                huesped.save(
                    update_fields=[
                        'nombre',
                        'apellidos',
                        'lugar_procedencia',
                        'tipo_documento',
                        'documento_identidad',
                        'nacionalidad',
                        'fecha_nacimiento',
                        'sexo',
                        'fecha_actualizacion',
                    ]
                )
            reserva.huesped = huesped
        else:
            huesped = self.instance.huesped
            huesped.tipo_documento = tipo
            huesped.documento_identidad = doc
            huesped.nombre = d['huesped_nombre']
            huesped.apellidos = d['huesped_apellidos']
            huesped.lugar_procedencia = d['huesped_lugar_procedencia']
            huesped.nacionalidad = d.get('huesped_nacionalidad') or 'Perú'
            huesped.fecha_nacimiento = d.get('huesped_fecha_nacimiento')
            huesped.sexo = d.get('huesped_sexo') or None
            huesped.save(
                update_fields=[
                    'tipo_documento',
                    'documento_identidad',
                    'nombre',
                    'apellidos',
                    'lugar_procedencia',
                    'nacionalidad',
                    'fecha_nacimiento',
                    'sexo',
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
        fields = [
            'documentos_recibidos',
            'deposito',
            'metodo_deposito',
            'mixto_efectivo',
            'mixto_tarjeta',
            'mixto_yape',
            'mixto_transferencia',
            'notas',
        ]
        labels = {
            'deposito': 'Depósito (soles)',
            'metodo_deposito': 'Método del depósito',
            'mixto_efectivo': 'Mixto: efectivo (S/)',
            'mixto_tarjeta': 'Mixto: tarjeta (S/)',
            'mixto_yape': 'Mixto: Yape (S/)',
            'mixto_transferencia': 'Mixto: transferencia (S/)',
        }
        help_texts = {
            'deposito': 'Monto en soles (S/).',
            'metodo_deposito': 'Si hay depósito: efectivo, Yape, transferencia o mixto (con desglose).',
            'mixto_efectivo': 'Solo si el método es Mixto: debe sumar al depósito y usar al menos dos medios.',
            'mixto_tarjeta': 'Solo si el método es Mixto.',
            'mixto_yape': 'Solo si el método es Mixto.',
            'mixto_transferencia': 'Solo si el método es Mixto.',
        }
        widgets = {
            'documentos_recibidos': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'deposito': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'metodo_deposito': forms.Select(attrs={'class': 'form-control', 'id': 'id_metodo_deposito_checkin'}),
            'mixto_efectivo': forms.NumberInput(
                attrs={'class': 'form-control mixto-dep-monto-input', 'step': '0.01', 'min': '0'}
            ),
            'mixto_tarjeta': forms.NumberInput(
                attrs={'class': 'form-control mixto-dep-monto-input', 'step': '0.01', 'min': '0'}
            ),
            'mixto_yape': forms.NumberInput(
                attrs={'class': 'form-control mixto-dep-monto-input', 'step': '0.01', 'min': '0'}
            ),
            'mixto_transferencia': forms.NumberInput(
                attrs={'class': 'form-control mixto-dep-monto-input', 'step': '0.01', 'min': '0'}
            ),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['metodo_deposito'].required = False
        self.fields['metodo_deposito'].choices = [
            ('', '— (sin depósito) —'),
        ] + list(CheckIn.METODO_DEPOSITO_CHOICES)

    def clean(self):
        cleaned = super().clean()
        dep = cleaned.get('deposito')
        if dep is None:
            dep = Decimal('0')
        met = cleaned.get('metodo_deposito')
        if met in (None, ''):
            met = None
            cleaned['metodo_deposito'] = None
        if dep <= 0:
            cleaned['metodo_deposito'] = None
            cleaned['mixto_efectivo'] = Decimal('0')
            cleaned['mixto_tarjeta'] = Decimal('0')
            cleaned['mixto_yape'] = Decimal('0')
            cleaned['mixto_transferencia'] = Decimal('0')
            return cleaned
        if not met:
            raise ValidationError(
                {
                    'metodo_deposito': [
                        'Si hay depósito, indique el método (efectivo, Yape, transferencia o mixto).'
                    ]
                }
            )
        if met != CheckIn.DEPOSITO_MIXTO:
            cleaned['mixto_efectivo'] = Decimal('0')
            cleaned['mixto_tarjeta'] = Decimal('0')
            cleaned['mixto_yape'] = Decimal('0')
            cleaned['mixto_transferencia'] = Decimal('0')
            return cleaned
        err = CheckIn.validar_desglose_mixto_deposito(
            dep,
            cleaned.get('mixto_efectivo'),
            cleaned.get('mixto_tarjeta'),
            cleaned.get('mixto_yape'),
            cleaned.get('mixto_transferencia'),
        )
        if err:
            raise ValidationError({'mixto_efectivo': [err]})
        return cleaned


class CheckOutForm(forms.ModelForm):
    """La fecha y hora de salida se guardan al confirmar (servidor). Quién registra va por la sesión."""

    class Meta:
        model = CheckOut
        fields = [
            'total_pagado',
            'metodo_pago',
            'mixto_efectivo',
            'mixto_tarjeta',
            'mixto_yape',
            'mixto_transferencia',
            'danos_observados',
            'notas',
        ]
        labels = {
            'total_pagado': 'Total pagado (soles)',
            'mixto_efectivo': 'Mixto: efectivo (S/)',
            'mixto_tarjeta': 'Mixto: tarjeta (S/)',
            'mixto_yape': 'Mixto: Yape (S/)',
            'mixto_transferencia': 'Mixto: transferencia (S/)',
        }
        help_texts = {
            'total_pagado': 'Monto en soles (S/).',
            'mixto_efectivo': 'Solo si el método es Mixto: debe sumar al total y usar al menos dos medios.',
            'mixto_tarjeta': 'Solo si el método es Mixto.',
            'mixto_yape': 'Solo si el método es Mixto.',
            'mixto_transferencia': 'Solo si el método es Mixto.',
        }
        widgets = {
            'total_pagado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'metodo_pago': forms.Select(attrs={'class': 'form-control', 'id': 'id_metodo_pago_checkout'}),
            'mixto_efectivo': forms.NumberInput(
                attrs={'class': 'form-control mixto-monto-input', 'step': '0.01', 'min': '0'}
            ),
            'mixto_tarjeta': forms.NumberInput(
                attrs={'class': 'form-control mixto-monto-input', 'step': '0.01', 'min': '0'}
            ),
            'mixto_yape': forms.NumberInput(
                attrs={'class': 'form-control mixto-monto-input', 'step': '0.01', 'min': '0'}
            ),
            'mixto_transferencia': forms.NumberInput(
                attrs={'class': 'form-control mixto-monto-input', 'step': '0.01', 'min': '0'}
            ),
            'danos_observados': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned = super().clean()
        metodo = cleaned.get('metodo_pago')
        if metodo != CheckOut.METODO_MIXTO:
            cleaned['mixto_efectivo'] = Decimal('0')
            cleaned['mixto_tarjeta'] = Decimal('0')
            cleaned['mixto_yape'] = Decimal('0')
            cleaned['mixto_transferencia'] = Decimal('0')
            return cleaned
        total = cleaned.get('total_pagado')
        err = CheckOut.validar_desglose_mixto(
            total,
            cleaned.get('mixto_efectivo'),
            cleaned.get('mixto_tarjeta'),
            cleaned.get('mixto_yape'),
            cleaned.get('mixto_transferencia'),
        )
        if err:
            raise ValidationError({'mixto_efectivo': [err]})
        return cleaned


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


