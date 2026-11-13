"""Búsqueda breve y autenticada; aplica la misma visibilidad que cada módulo."""

from urllib.parse import urlencode

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from notificaciones.models import Notificacion, PlazoReporte
from notificaciones.services import plazos_para_usuario

from .forms import BusquedaGlobalForm
from .selectors import _visible_envios
from .utils import is_admin_or_group


@never_cache
@require_GET
def buscar(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Ingresa de nuevo para buscar.", "login_url": reverse("login")}, status=401)
    form = BusquedaGlobalForm(request.GET)
    if not form.is_valid():
        return JsonResponse({"error": "Escribe una búsqueda válida de hasta 100 caracteres."}, status=400)
    termino = form.cleaned_data["q"]
    if len(termino) < 2:
        return JsonResponse({"resultados": []})
    # Límite por cuenta, compartido entre procesos mediante Redis; no penaliza una red del centro.
    clave = f"busqueda:{request.user.pk}"
    try:
        if cache.add(clave, 1, timeout=60):
            intentos = 1
        else:
            try:
                intentos = cache.incr(clave)
            except ValueError:
                cache.add(clave, 1, timeout=60)
                intentos = 1
    except Exception:
        return JsonResponse(
            {"error": "La búsqueda está temporalmente ocupada. Intenta de nuevo más tarde."}, status=503
        )
    if intentos > 60:
        response = JsonResponse({"error": "Espera un minuto antes de volver a buscar."}, status=429)
        response["Retry-After"] = "60"
        return response
    resultados = []
    envios = _visible_envios(request.user).filter(
        Q(nombre__icontains=termino) | Q(proyecto__icontains=termino) | Q(tipo_evidencia__icontains=termino)
    )
    for envio in envios.only("pk", "nombre", "proyecto", "tipo_evidencia")[:5]:
        resultados.append(
            {
                "titulo": envio.nombre or envio.tipo_evidencia,
                "detalle": f"Evidencia · {envio.proyecto or 'Sin proyecto'}",
                "url": reverse("ver_evidencia", args=[envio.pk]),
                "tipo": "Evidencias",
            }
        )
    admin = is_admin_or_group(request.user, [])
    if admin:
        usuarios = (
            User.objects.filter(
                Q(username__icontains=termino)
                | Q(first_name__icontains=termino)
                | Q(last_name__icontains=termino)
                | Q(email__icontains=termino)
            )
            .order_by("username")
            .only("pk", "username", "first_name", "last_name")[:5]
        )
        for usuario in usuarios:
            resultados.append(
                {
                    "titulo": usuario.get_full_name() or usuario.username,
                    "detalle": f"Usuario · @{usuario.username}",
                    "url": reverse("admin_personalizado:detalle_usuario", args=[usuario.pk]),
                    "tipo": "Usuarios",
                }
            )
    plazos = PlazoReporte.objects.filter(activo=True) if admin else plazos_para_usuario(request.user, pendientes=False)
    plazos = (
        plazos.filter(Q(titulo__icontains=termino) | Q(proyecto__icontains=termino))
        .only("pk", "titulo", "proyecto")
        .order_by("fecha_limite", "pk")
    )
    for plazo in plazos[:4]:
        resultados.append(
            {
                "titulo": plazo.titulo,
                "detalle": f"Plazo · {plazo.proyecto or 'Todos los proyectos'}",
                "url": reverse("notificaciones:editar_plazo", args=[plazo.pk])
                if admin
                else reverse("notificaciones:mis_plazos") + "?" + urlencode({"plazo": plazo.pk}),
                "tipo": "Plazos",
            }
        )
    avisos = Notificacion.objects.filter(usuario=request.user, titulo__icontains=termino)
    for aviso in avisos.only("pk", "titulo")[:4]:
        resultados.append(
            {
                "titulo": aviso.titulo,
                "detalle": "Notificación personal",
                "url": reverse("notificaciones:bandeja") + "?" + urlencode({"aviso": aviso.pk}),
                "tipo": "Notificaciones",
            }
        )
    return JsonResponse({"resultados": resultados})
