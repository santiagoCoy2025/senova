"""Mutaciones de cuentas: validación, bloqueo de filas, auditoría y revocación."""

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, prefetch_related_objects

from cuentas.correos import invalidar_recuperaciones
from cuentas.models import RegistroSeguridad
from cuentas.sesiones import cerrar_sesiones


def _actor_autorizado(actor):
    actual = (
        User.objects.filter(pk=actor.pk, is_active=True)
        .filter(Q(is_superuser=True) | Q(groups__name="administrador"))
        .values("is_superuser")
        .first()
    )
    if actual is None:
        raise ValidationError("No tienes permiso para administrar cuentas.")
    return actual["is_superuser"]


def _proteger_cuenta(usuario, superadministrador):
    if (usuario.is_superuser or usuario.is_staff) and not superadministrador:
        raise ValidationError("Solo un superadministrador puede modificar esta cuenta protegida.")


def validar_destino(actor, usuario):
    _proteger_cuenta(usuario, _actor_autorizado(actor))


def registrar_cambio(actor, usuario, accion):
    RegistroSeguridad.objects.create(
        actor=actor, accion=f"admin:{accion}", ruta=f"/administrador/usuario/{usuario.pk}/"
    )


def _cuentas_bloqueadas(ids):
    try:
        ids = {int(pk) for pk in ids}
    except (TypeError, ValueError):
        raise ValidationError("Selecciona cuentas válidas.") from None
    if not ids or len(ids) > 100 or min(ids) < 1:
        raise ValidationError("Selecciona entre 1 y 100 cuentas por operación.")
    usuarios = list(User.objects.select_for_update().filter(pk__in=ids).order_by("pk"))
    if len(usuarios) != len(ids):
        raise ValidationError("Una de las cuentas ya no está disponible. Actualiza la lista.")
    return usuarios


@transaction.atomic
def cambiar_estados(actor, ids, *, activo):
    superadministrador = _actor_autorizado(actor)
    usuarios = _cuentas_bloqueadas(ids)
    for usuario in usuarios:
        _proteger_cuenta(usuario, superadministrador)
        if usuario.pk == actor.pk and not activo:
            raise ValidationError("No puedes desactivar tu propia cuenta.")
    cambios = 0
    for usuario in usuarios:
        if usuario.is_active == activo:
            continue
        usuario.is_active = activo
        usuario.save(update_fields=["is_active"])
        if not activo:
            invalidar_recuperaciones(usuario)
            cerrar_sesiones(usuario)
        registrar_cambio(actor, usuario, "activar" if activo else "desactivar")
        cambios += 1
    return cambios


@transaction.atomic
def cambiar_roles(actor, cambios):
    if not cambios:
        return 0
    superadministrador = _actor_autorizado(actor)
    usuarios = _cuentas_bloqueadas(cambios)
    prefetch_related_objects(usuarios, "groups")
    disponibles = {grupo.pk: grupo for grupo in Group.objects.all()}
    for usuario in usuarios:
        _proteger_cuenta(usuario, superadministrador)
        ids = set(cambios[usuario.pk])
        if not ids.issubset(disponibles):
            raise ValidationError("Uno de los roles ya no existe. Actualiza la lista.")
        if usuario.pk == actor.pk and not superadministrador:
            if not any(disponibles[pk].name == "administrador" for pk in ids):
                raise ValidationError("No puedes retirar tu propio rol de administrador.")
    actualizados = 0
    for usuario in usuarios:
        ids = set(cambios[usuario.pk])
        if {grupo.pk for grupo in usuario.groups.all()} != ids:
            usuario.groups.set(ids)
            registrar_cambio(actor, usuario, "roles")
            actualizados += 1
    return actualizados
