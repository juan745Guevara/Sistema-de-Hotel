from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django import forms
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from .models import Membership, Tenant


class SignupForm(forms.Form):
    hotel_name = forms.CharField(max_length=200, label='Nombre del hotel')
    email = forms.EmailField(label='Correo electrónico')
    password1 = forms.CharField(widget=forms.PasswordInput, label='Contraseña')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirmar contraseña')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con este correo.')
        return email

    def clean(self):
        data = super().clean()
        p1 = data.get('password1')
        p2 = data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Las contraseñas no coinciden.')
        return data


@require_http_methods(['GET', 'POST'])
def accounts_login(request):
    if request.user.is_authenticated:
        return redirect('index')
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        memberships = list(
            Membership.objects.filter(user=request.user).select_related('tenant')
        )
        if len(memberships) == 1:
            request.session['active_tenant_id'] = memberships[0].tenant_id
            next_url = request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host(), *settings.ALLOWED_HOSTS},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect('index')
        request.session.pop('active_tenant_id', None)
        next_url = request.GET.get('next')
        if next_url:
            request.session['post_login_next'] = next_url
        return redirect('select_tenant')
    return render(request, 'hotel/accounts/login.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def accounts_signup(request):
    if request.user.is_authenticated:
        return redirect('index')
    form = SignupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        user = User.objects.create_user(
            username=email,
            email=email,
            password=form.cleaned_data['password1'],
        )
        tenant = Tenant(name=form.cleaned_data['hotel_name'])
        tenant.save()
        Membership.objects.create(
            user=user,
            tenant=tenant,
            role=Membership.ROLE_OWNER,
        )
        login(request, user)
        request.session['active_tenant_id'] = tenant.pk
        messages.success(request, 'Cuenta y hotel creados. ¡Bienvenido!')
        return redirect('index')
    return render(request, 'hotel/accounts/signup.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def accounts_logout(request):
    logout(request)
    request.session.pop('active_tenant_id', None)
    messages.info(request, 'Sesión cerrada.')
    return redirect('accounts_login')


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
