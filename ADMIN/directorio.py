"""Consulta común y exportación acotada del directorio administrativo."""

from zoneinfo import ZoneInfo

from django.contrib.auth.models import Group, User
from django.db.models import Max, Prefetch, Q
from django.utils import timezone

LOTE_EXPORTACION = 500
CAMPOS_DIRECTORIO = ("id", "username", "first_name", "last_name", "email", "is_active", "date_joined")


def usuarios_filtrados(form):
    consulta = User.objects.order_by("-date_joined", "-pk")
    if not form.is_valid():
        return consulta.none()
    datos = form.cleaned_data
    if q := datos["q"]:
        consulta = consulta.filter(
            Q(username__icontains=q) | Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
        )
    if estado := datos["estado"]:
        consulta = consulta.filter(is_active=estado == "activo")
    if rol := datos["rol"]:
        consulta = consulta.filter(groups__pk=rol)
    return consulta


def _con_roles(consulta):
    return consulta.prefetch_related(Prefetch("groups", queryset=Group.objects.only("pk", "name").order_by("name")))


def usuarios_de_pagina(consulta):
    return _con_roles(consulta.only(*CAMPOS_DIRECTORIO, "is_staff", "is_superuser"))


def pagina_de_regreso(valor):
    try:
        numero = int(valor or 1)
        return numero if 1 <= numero <= 2**31 - 1 else 1
    except (ValueError, TypeError):
        return 1


def filas_directorio(consulta):
    """Cada SELECT lleva LIMIT; no acumula todo el directorio ni usa OFFSET."""
    yield [
        "Identificador",
        "Usuario",
        "Nombre completo",
        "Correo electrónico",
        "Roles",
        "Estado",
        "Registro (Colombia)",
    ]
    tope = consulta.aggregate(ultimo=Max("pk"))["ultimo"]
    if tope is None:
        return
    ultimo = 0
    zona = ZoneInfo("America/Bogota")
    while ultimo < tope:
        lote = list(
            _con_roles(consulta.filter(pk__gt=ultimo, pk__lte=tope).order_by("pk").only(*CAMPOS_DIRECTORIO))[
                :LOTE_EXPORTACION
            ]
        )
        if not lote:
            return
        for usuario in lote:
            yield [
                usuario.pk,
                usuario.username,
                usuario.get_full_name(),
                usuario.email,
                " | ".join(grupo.name for grupo in usuario.groups.all()),
                "Activo" if usuario.is_active else "Inactivo",
                timezone.localtime(usuario.date_joined, zona).strftime("%Y-%m-%d %H:%M:%S %z"),
            ]
        ultimo = lote[-1].pk
        if len(lote) < LOTE_EXPORTACION:
            return
