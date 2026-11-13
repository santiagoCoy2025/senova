"""Lectura y presentación de auditoría; no modifica ni elimina eventos."""

import datetime
import re

from django.db.models import Q
from django.db.models.functions import Right
from django.utils import timezone

from cuentas.models import RegistroSeguridad

CODIGO_HTTP = re.compile(r"[1-5][0-9]{2}")
SUFIJO_HTTP = r"^:[1-5][0-9]{2}$"
IDENTIDAD_ACTOR = ("actor__id", "actor__username", "actor__first_name", "actor__last_name")
ETIQUETAS = {
    "login": "Inicio de sesión",
    "login_root": "Inicio de sesión",
    "logout": "Cierre de sesión",
    "olvide_password": "Solicitud de recuperación",
    "verificar_pin": "Verificación del PIN",
    "restablecer_password": "Restablecimiento de contraseña",
    "editar_perfil": "Actualización del perfil",
    "revocar_sesion": "Cierre de una sesión",
    "cerrar_otras_sesiones": "Cierre de otras sesiones",
    "set_aprobada": "Revisión de evidencia",
    "admin:activar": "Activación de cuenta",
    "admin:desactivar": "Desactivación de cuenta",
    "admin:roles": "Cambio de roles",
    "admin:perfil": "Actualización de una cuenta",
    "admin:password": "Cambio de contraseña",
    "admin:permisos_grupo": "Cambio de permisos de grupo",
    "admin:exportar_directorio": "Solicitud de exportación de usuarios",
    "admin:cuenta": "Actualización desde Django admin",
}


def codigo_http(accion):
    sufijo = accion.rsplit(":", 1)[-1]
    return sufijo if CODIGO_HTTP.fullmatch(sufijo) and ":" in accion else None


def etiqueta_accion(accion):
    nombre = accion.rsplit(":", 1)[0] if codigo_http(accion) else accion
    if nombre in ETIQUETAS:
        return ETIQUETAS[nombre]
    if nombre.startswith("admin_personalizado:"):
        return "Gestión de cuentas"
    if nombre.startswith("notificaciones:"):
        return "Comunicaciones y plazos"
    if nombre.startswith("mantenimiento:"):
        return "Mantenimiento de cuentas"
    return "Actividad registrada"


def registros_filtrados(form):
    consulta = (
        RegistroSeguridad.objects.select_related("actor")
        .only("pk", "accion", "creado_en", "ruta", "direccion_ip", *IDENTIDAD_ACTOR)
        .order_by("-creado_en", "-pk")
    )
    if not form.is_valid():
        return consulta.none()
    datos = form.cleaned_data
    if q := datos["q"]:
        consulta = consulta.filter(
            Q(actor__username__icontains=q)
            | Q(actor__first_name__icontains=q)
            | Q(actor__last_name__icontains=q)
            | Q(accion__icontains=q)
            | Q(ruta__icontains=q)
        )
    estado = datos["estado"]
    consulta = consulta.alias(sufijo_http=Right("accion", 4))
    if estado == "incidencias":
        consulta = consulta.filter(sufijo_http__regex=r"^:[45][0-9]{2}$")
    elif estado == "http":
        consulta = consulta.filter(sufijo_http__regex=SUFIJO_HTTP)
    elif estado == "internos":
        consulta = consulta.exclude(sufijo_http__regex=SUFIJO_HTTP)
    if desde := datos["desde"]:
        consulta = consulta.filter(
            creado_en__gte=timezone.make_aware(datetime.datetime.combine(desde, datetime.time.min))
        )
    if hasta := datos["hasta"]:
        fin = hasta + datetime.timedelta(days=1)
        consulta = consulta.filter(creado_en__lt=timezone.make_aware(datetime.datetime.combine(fin, datetime.time.min)))
    return consulta


def presentar_registro(registro):
    codigo = codigo_http(registro.accion)
    return {
        "pk": registro.pk,
        "etiqueta": etiqueta_accion(registro.accion),
        "accion": registro.accion,
        "actor": (registro.actor.get_full_name() or registro.actor.username)
        if registro.actor
        else "Sin cuenta asociada",
        "cuenta": registro.actor.username if registro.actor else "",
        "fecha": registro.creado_en,
        "codigo": codigo,
        "incidencia": bool(codigo and int(codigo) >= 400),
        "ruta": registro.ruta,
        "ip": registro.direccion_ip,
    }


def filas_auditoria(consulta):
    yield ["Fecha (Colombia)", "Responsable", "Cuenta", "Actividad", "Acción registrada", "HTTP", "Ruta", "IP"]
    for registro in consulta.iterator(chunk_size=200):
        item = presentar_registro(registro)
        yield [
            timezone.localtime(item["fecha"]).strftime("%Y-%m-%d %H:%M:%S %z"),
            item["actor"],
            item["cuenta"],
            item["etiqueta"],
            item["accion"],
            item["codigo"] or "",
            item["ruta"],
            item["ip"] or "",
        ]
