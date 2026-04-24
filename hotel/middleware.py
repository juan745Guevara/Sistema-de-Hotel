from django.shortcuts import redirect
from django.urls import reverse

from .tenant_scope import clear_current_tenant, set_current_tenant
from .models import Membership


def _path(request):
    return request.path or ''


def _is_admin(path):
    return path.startswith('/admin')


def _is_login_or_signup(path):
    return path.startswith('/accounts/login') or path.startswith('/accounts/signup')


def _is_select_tenant_or_logout(path):
    return path.startswith('/accounts/select-tenant') or path.startswith('/accounts/logout')


class TenantAuthMiddleware:
    """
    - Rutas públicas: login y registro.
    - Resto: requiere usuario autenticado.
    - Requiere hotel activo en sesión salvo selección de hotel o logout.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = _path(request)
        clear_current_tenant()
        request.tenant = None

        if _is_admin(path):
            return self.get_response(request)

        if not request.user.is_authenticated:
            if _is_login_or_signup(path):
                return self.get_response(request)
            login_url = reverse('accounts_login')
            if path != login_url:
                return redirect(f'{login_url}?next={request.get_full_path()}')
            return self.get_response(request)

        if _is_login_or_signup(path):
            return redirect(reverse('index'))

        tenant_id = request.session.get('active_tenant_id')
        if not tenant_id:
            if _is_select_tenant_or_logout(path):
                return self.get_response(request)
            return redirect(reverse('select_tenant'))

        membership = (
            Membership.objects.filter(user=request.user, tenant_id=tenant_id)
            .select_related('tenant')
            .first()
        )
        if not membership:
            request.session.pop('active_tenant_id', None)
            return redirect(reverse('select_tenant'))

        if _is_select_tenant_or_logout(path):
            return self.get_response(request)

        set_current_tenant(membership.tenant)
        request.tenant = membership.tenant
        return self.get_response(request)
