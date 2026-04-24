from django.db import models

from .tenant_scope import get_current_tenant


class TenantScopedManager(models.Manager):
    """Filtra por `tenant` del contexto de petición."""

    def get_queryset(self):
        qs = super().get_queryset()
        tenant = get_current_tenant()
        if tenant is not None:
            return qs.filter(tenant=tenant)
        return qs.none()


class ThroughReservaTenantManager(models.Manager):
    """Check-in/out asociados a reservas del tenant actual."""

    def get_queryset(self):
        qs = super().get_queryset()
        tenant = get_current_tenant()
        if tenant is not None:
            return qs.filter(reserva__tenant=tenant)
        return qs.none()


class AllObjectsManager(models.Manager):
    """Acceso sin filtro (admin, migraciones, registro)."""

    use_in_migrations = True
