from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.validators import UnicodeUsernameValidator
from django import forms
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from .models import Membership, Tenant

SESSION_LOGIN_TENANT_ID = 'login_tenant_id'


class HotelSlugForm(forms.Form):
    slug = forms.SlugField(
        label='Identificador del hotel',
        help_text='Suele ser una sola palabra o varias separadas por guiones (ej. hotel-central).',
    )

    def clean_slug(self):
        slug = self.cleaned_data['slug'].strip().lower()
        if not Tenant.objects.filter(slug=slug).exists():
            raise forms.ValidationError('No existe un hotel con ese identificador. Revísalo o contacta al administrador.')
        return slug


class SignupForm(forms.Form):
    hotel_name = forms.CharField(max_length=200, label='Nombre del hotel')
    username = forms.CharField(
        max_length=150,
        label='Nombre de usuario',
        help_text='Será tu identificador para entrar (letras, números y @ . + - _).',
        validators=[UnicodeUsernameValidator()],
    )
    password1 = forms.CharField(widget=forms.PasswordInput, label='Contraseña')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirmar contraseña')

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Ya existe una cuenta con este nombre de usuario.')
        return username

    def clean(self):
        data = super().clean()
        p1 = data.get('password1')
        p2 = data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Las contraseñas no coinciden.')
        return data


def _safe_next(request, explicit_next=None):
    next_url = explicit_next or request.GET.get('next') or request.POST.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host(), *settings.ALLOWED_HOSTS},
        require_https=request.is_secure(),
    ):
        return next_url
    return None


def _next_for_login_template(request):
    n = _safe_next(request)
    if n:
        return n
    if request.method == 'POST':
        return _safe_next(request, request.POST.get('next'))
    return ''


@require_http_methods(['GET', 'POST'])
def accounts_hotel_identify(request):
    """Paso 1 del ingreso: identificar hotel (slug) antes de usuario y rol."""
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'GET' and request.GET.get('cambiar'):
        request.session.pop(SESSION_LOGIN_TENANT_ID, None)

    form = HotelSlugForm(request.POST or None)
    next_url = _safe_next(request)

    if request.method == 'POST' and form.is_valid():
        tenant = Tenant.objects.get(slug=form.cleaned_data['slug'])
        request.session[SESSION_LOGIN_TENANT_ID] = tenant.pk
        next_q = _safe_next(request, request.POST.get('next'))
        login_url = reverse('accounts_login')
        if next_q:
            return redirect(f'{login_url}?next={next_q}')
        return redirect('accounts_login')

    return render(
        request,
        'hotel/accounts/hotel_identify.html',
        {'form': form, 'next': next_url or ''},
    )


@require_http_methods(['GET'])
def accounts_ingreso_con_hotel(request, tenant_slug):
    """
    Enlace directo al paso 2 del ingreso: fija el hotel en sesión y abre el login con rol.
    Útil para compartir con recepción y limpieza (evita escribir el slug a mano).
    """
    if request.user.is_authenticated:
        return redirect('index')
    tenant = get_object_or_404(Tenant, slug=tenant_slug.strip().lower())
    request.session[SESSION_LOGIN_TENANT_ID] = tenant.pk
    next_q = _safe_next(request)
    login_url = reverse('accounts_login')
    if next_q:
        return redirect(f'{login_url}?next={next_q}')
    return redirect('accounts_login')


@require_http_methods(['GET', 'POST'])
def accounts_login(request):
    if request.user.is_authenticated:
        return redirect('index')

    tenant_id = request.session.get(SESSION_LOGIN_TENANT_ID)
    if not tenant_id:
        next_q = _safe_next(request)
        hotel_url = reverse('accounts_hotel_identify')
        if next_q:
            return redirect(f'{hotel_url}?next={next_q}')
        return redirect('accounts_hotel_identify')

    tenant = get_object_or_404(Tenant, pk=tenant_id)
    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        role_claim = request.POST.get('role', '').strip()
        valid_roles = {c[0] for c in Membership.ROLE_CHOICES}
        membership = Membership.objects.filter(user=user, tenant_id=tenant_id).select_related('tenant').first()

        if not membership:
            form.add_error(None, 'Tu usuario no tiene acceso a este hotel.')
        elif role_claim not in valid_roles:
            form.add_error(None, 'Indica con qué rol entras (administrador, recepción o limpieza).')
        elif membership.role != role_claim:
            form.add_error(
                None,
                'El rol que elegiste no coincide con el asignado a tu cuenta en este hotel. '
                'Si no estás seguro, pregunta al administrador.',
            )
        else:
            login(request, user)
            request.session['active_tenant_id'] = tenant_id
            request.session.pop(SESSION_LOGIN_TENANT_ID, None)
            next_url = _safe_next(request)
            if next_url:
                return redirect(next_url)
            messages.success(request, f'Sesión iniciada en {tenant.name} como {membership.get_role_display()}.')
            return redirect('index')

    return render(
        request,
        'hotel/accounts/login.html',
        {
            'form': form,
            'login_tenant': tenant,
            'role_choices': Membership.ROLE_CHOICES,
            'next': _next_for_login_template(request) or '',
            'posted_role': request.POST.get('role', '') if request.method == 'POST' else '',
        },
    )


@require_http_methods(['GET', 'POST'])
def accounts_signup(request):
    if request.user.is_authenticated:
        return redirect('index')
    form = SignupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data['username']
        user = User.objects.create_user(
            username=username,
            email='',
            password=form.cleaned_data['password1'],
        )
        tenant = Tenant(name=form.cleaned_data['hotel_name'])
        tenant.save()
        Membership.objects.create(
            user=user,
            tenant=tenant,
            role=Membership.ROLE_ADMIN,
        )
        login(request, user)
        request.session['active_tenant_id'] = tenant.pk
        request.session.pop(SESSION_LOGIN_TENANT_ID, None)
        messages.success(
            request,
            f'Cuenta y hotel creados. Tu usuario es «{username}» y el identificador del hotel «{tenant.slug}» '
            f'(para el ingreso en dos pasos). ¡Bienvenido!',
        )
        return redirect('index')
    return render(request, 'hotel/accounts/signup.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def accounts_logout(request):
    logout(request)
    request.session.pop('active_tenant_id', None)
    request.session.pop(SESSION_LOGIN_TENANT_ID, None)
    messages.info(request, 'Sesión cerrada.')
    return redirect('accounts_hotel_identify')


@require_http_methods(['GET', 'POST'])
def select_tenant(request):
    memberships = list(
        Membership.objects.filter(user=request.user).select_related('tenant').order_by('tenant__name')
    )
    if not memberships:
        messages.warning(
            request,
            'No tienes ningún hotel asignado. Contacta al administrador o crea una cuenta nueva.',
        )
        return redirect('accounts_logout')

    if request.method == 'POST':
        tid = request.POST.get('tenant_id')
        try:
            tid = int(tid)
        except (TypeError, ValueError):
            tid = None
        if tid and any(m.tenant_id == tid for m in memberships):
            request.session['active_tenant_id'] = tid
            next_url = request.session.pop('post_login_next', None)
            return redirect(next_url or 'index')
        messages.error(request, 'Selección no válida.')

    request.session.pop('active_tenant_id', None)
    return render(
        request,
        'hotel/accounts/select_tenant.html',
        {'memberships': memberships},
    )
