from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_safe

from cuentas.correos import encolar_aviso_cambio, invalidar_recuperaciones
from cuentas.forms import ConfirmarPasswordForm, EditarUsuarioForm
from cuentas.models import RegistroSeguridad
from cuentas.sesiones import cerrar_sesiones
from Gesicom.exportaciones import respuesta_csv
from Gesicom.interfaz import render_panel
from Gesicom.utils import require_group
from SENNOVA.database_security import inspeccionar_conexion
from SENNOVA.middleware import client_ip

from .auditoria import filas_auditoria, presentar_registro, registros_filtrados
from .directorio import filas_directorio, pagina_de_regreso, usuarios_de_pagina, usuarios_filtrados
from .forms import FiltrosAuditoriaForm, FiltrosUsuariosForm
from .selectors import centro_operaciones
from .services import cambiar_estados, cambiar_roles, registrar_cambio, validar_destino


def _requerir_administrador(usuario):
    """Verifica que el usuario tenga el rol de administrador o sea superuser."""
    return usuario.is_superuser or usuario.groups.filter(name="administrador").exists()


@login_required
@user_passes_test(_requerir_administrador, login_url="access_denied")
def panel_control(request):
    return render_panel(
        request, "admin_personalizado/dashboard_modern.html", centro_operaciones(request.GET.get("periodo"))
    )


@require_group("administrador")
@require_safe
@never_cache
def base_datos(request):
    return render_panel(
        request,
        "admin_personalizado/base_datos.html",
        {"informe_sql": inspeccionar_conexion(), "comprobado_en": timezone.now()},
    )


@require_group("administrador")
@require_safe
def actividad(request):
    form = FiltrosAuditoriaForm(request.GET)
    pagina = Paginator(registros_filtrados(form), 25).get_page(request.GET.get("page"))
    return render_panel(
        request,
        "admin_personalizado/actividad.html",
        {
            "filtros_form": form,
            "pagina": pagina,
            "registros": [presentar_registro(item) for item in pagina],
            "url_exportar": reverse("admin_personalizado:actividad_csv") + form.consulta_url()
            if form.is_valid()
            else None,
        },
    )


@require_group("administrador")
@require_safe
def actividad_csv(request):
    form = FiltrosAuditoriaForm(request.GET)
    if not form.is_valid():
        return render(
            request,
            "error_filtros.html",
            {
                "filtros_form": form,
                "volver": reverse("admin_personalizado:actividad") + form.consulta_url(),
                "regreso_error": reverse("admin_personalizado:actividad"),
                "regreso_texto": "Volver a actividad",
                "seccion_error": "GESICOM / ADMINISTRACIÓN / ACTIVIDAD",
            },
            status=400,
        )
    return respuesta_csv(filas_auditoria(registros_filtrados(form)), "actividad-gesicom.csv")


@login_required
@user_passes_test(_requerir_administrador, login_url="access_denied")
@sensitive_post_parameters("contrasena_actual")
def permisos(request):
    from django import forms

    from .permisos import ConflictoPermisos, PermisosGrupoForm, actualizar_permisos, grupo_protegido

    grupos = Group.objects.order_by("name")
    raw = request.POST.get("group") if request.method == "POST" else request.GET.get("group")
    seleccionado = None
    estado = 200
    form = None
    editable = False
    if raw:
        try:
            pk = forms.IntegerField(min_value=1, max_value=2**63 - 1).clean(raw)
            seleccionado = Group.objects.filter(pk=pk).first()
            if seleccionado is None:
                raise ValidationError("El grupo ya no está disponible.")
        except ValidationError:
            messages.error(request, "Selecciona un grupo válido.")
            estado = 400
    elif request.method == "POST":
        messages.error(request, "Selecciona el grupo que deseas actualizar.")
        estado = 400
    if seleccionado:
        editable = request.user.is_superuser or not grupo_protegido(seleccionado)
        form = PermisosGrupoForm(request.POST if request.method == "POST" else None, grupo=seleccionado)
        if request.method == "POST" and form.is_valid():
            try:
                cambios = actualizar_permisos(
                    request.user,
                    seleccionado.pk,
                    form.cleaned_data["revision_actual"],
                    form.cambios(),
                    form.cleaned_data["contrasena_actual"],
                )
            except ConflictoPermisos as error:
                form.add_error(None, error)
                estado = 409
            except ValidationError as error:
                form.add_error(None, error)
            else:
                messages.success(
                    request, f"Permisos guardados: {cambios} cambios." if cambios else "Los permisos no tienen cambios."
                )
                return redirect(reverse("admin_personalizado:permisos") + f"?group={seleccionado.pk}")
        if not editable:
            for campo in form.fields.values():
                campo.disabled = True
    return render(
        request,
        "admin_personalizado/permisos.html",
        {
            "grupos": grupos,
            "grupo_seleccionado": seleccionado,
            "form": form,
            "puede_editar": editable,
            "conflicto": estado == 409,
        },
        status=estado,
    )


@login_required
@user_passes_test(_requerir_administrador, login_url="access_denied")
@sensitive_post_parameters()
def gestionar_usuarios(request):
    grupos = list(Group.objects.order_by("name"))
    filtros = FiltrosUsuariosForm(request.GET, grupos=grupos)
    regreso = reverse("admin_personalizado:gestionar_usuarios") + filtros.consulta_url(
        pagina=pagina_de_regreso(request.GET.get("page"))
    )
    if request.method == "POST":
        form = ConfirmarPasswordForm(request.POST, usuario=request.user)
        if not form.is_valid():
            messages.error(request, "Confirma tu contraseña actual para administrar las cuentas.")
            return redirect(regreso)
        try:
            accion = request.POST.get("accion", "roles")
            if accion in {"activar", "desactivar"}:
                total = cambiar_estados(request.user, request.POST.getlist("usuarios"), activo=accion == "activar")
                messages.success(request, f"Se cambió el estado de {total} cuentas.")
            elif accion == "roles":
                cambios = {}
                for key, value in request.POST.items():
                    if key.startswith("role_") and value != "__keep__":
                        try:
                            pk = int(key.removeprefix("role_"))
                            cambios[pk] = [int(value)] if value else []
                        except ValueError:
                            raise ValidationError("Selecciona un usuario y un rol válidos.") from None
                total = cambiar_roles(request.user, cambios)
                messages.success(request, f"Se actualizaron los roles de {total} cuentas.")
            else:
                raise ValidationError("Selecciona una acción válida.")
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        return redirect(regreso)
    busqueda = request.GET.get("q", "").strip()[:100]
    estado = request.GET.get("estado", "")
    rol = request.GET.get("rol", "")
    lista = usuarios_de_pagina(usuarios_filtrados(filtros))
    return render_panel(
        request,
        "admin_personalizado/gestionar_usuarios_modern.html",
        {
            "usuarios": Paginator(lista, 25).get_page(request.GET.get("page")),
            "busqueda": busqueda,
            "estado": estado,
            "rol": rol,
            "grupos_disponibles": grupos,
            "filtros_form": filtros,
            "regreso_directorio": regreso,
            "url_exportar": reverse("admin_personalizado:usuarios_csv") + filtros.consulta_url()
            if filtros.is_valid()
            else None,
            "mensaje_filtros": "No se muestran cuentas hasta corregir los filtros.",
        },
    )


@require_group("administrador")
@require_safe
@never_cache
def usuarios_csv(request):
    filtros = FiltrosUsuariosForm(request.GET, grupos=list(Group.objects.order_by("name")))
    if not filtros.is_valid():
        return render(
            request,
            "error_filtros.html",
            {
                "filtros_form": filtros,
                "volver": reverse("admin_personalizado:gestionar_usuarios"),
                "regreso_error": reverse("admin_personalizado:gestionar_usuarios"),
                "regreso_texto": "Volver al directorio",
                "seccion_error": "GESICOM / ADMINISTRACIÓN / USUARIOS",
            },
            status=400,
        )
    if request.method == "GET":
        RegistroSeguridad.objects.create(
            actor=request.user,
            accion="admin:exportar_directorio",
            ruta=request.path,
            direccion_ip=client_ip(request),
        )
    return respuesta_csv(filas_directorio(usuarios_filtrados(filtros)), "usuarios-gesicom.csv")


@login_required
@user_passes_test(_requerir_administrador, login_url="access_denied")
def crear_usuario(request):
    from cuentas.forms import CrearUsuarioForm

    form = CrearUsuarioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                usuario = form.save()
            messages.success(request, f'Usuario "{usuario.username}" creado correctamente.')
            return redirect("admin_personalizado:detalle_usuario", usuario_id=usuario.pk)
        except IntegrityError:
            form.add_error(None, "El usuario o correo ya está registrado.")
    return render(
        request,
        "admin_personalizado/crear_usuario.html",
        {
            "grupos_disponibles": Group.objects.order_by("name"),
            "errores": [str(error) for items in form.errors.values() for error in items]
            if request.method == "POST"
            else [],
            "nombre_usuario": request.POST.get("username", ""),
            "correo": request.POST.get("email", ""),
            "nombre": request.POST.get("first_name", ""),
            "apellido": request.POST.get("last_name", ""),
        },
    )


@login_required
@user_passes_test(_requerir_administrador, login_url="access_denied")
@sensitive_post_parameters()
def detalle_usuario(request, usuario_id):
    from Gesicom.models import Envio

    usuario = get_object_or_404(User, pk=usuario_id)
    if request.method == "POST":
        if not ConfirmarPasswordForm(request.POST, usuario=request.user).is_valid():
            messages.error(request, "Confirma tu contraseña actual para modificar esta cuenta.")
            return redirect("admin_personalizado:detalle_usuario", usuario_id=usuario_id)
        try:
            with transaction.atomic():
                usuario = User.objects.select_for_update().get(pk=usuario_id)
                validar_destino(request.user, usuario)
                accion = request.POST.get("action")
                if accion == "update_profile":
                    form = EditarUsuarioForm(request.POST, instance=usuario)
                    correo_anterior = usuario.email
                    if not form.is_valid():
                        raise ValidationError([str(e) for errors in form.errors.values() for e in errors])
                    form.save()
                    if correo_anterior.casefold() != usuario.email.casefold():
                        invalidar_recuperaciones(usuario)
                        encolar_aviso_cambio(usuario, correo_anterior)
                        cerrar_sesiones(
                            usuario, conservar=request.session.session_key if usuario.pk == request.user.pk else None
                        )
                    registrar_cambio(request.user, usuario, "perfil")
                    messages.success(request, "Datos del usuario actualizados.")
                elif accion == "update_status":
                    cambiar_estados(request.user, [usuario.pk], activo=request.POST.get("is_active") == "on")
                    messages.success(request, "Estado de la cuenta actualizado.")
                elif accion == "update_groups":
                    try:
                        ids = [int(pk) for pk in request.POST.getlist("grupos")]
                    except ValueError:
                        raise ValidationError("Selecciona roles válidos.") from None
                    cambiar_roles(request.user, {usuario.pk: ids})
                    messages.success(request, "Roles de la cuenta actualizados.")
                elif accion == "change_password":
                    form = SetPasswordForm(
                        usuario,
                        {
                            "new_password1": request.POST.get("nueva_password", ""),
                            "new_password2": request.POST.get("confirmar_password", ""),
                        },
                    )
                    if not form.is_valid():
                        raise ValidationError([str(e) for errors in form.errors.values() for e in errors])
                    form.save()
                    invalidar_recuperaciones(usuario)
                    encolar_aviso_cambio(usuario)
                    if usuario.pk == request.user.pk:
                        update_session_auth_hash(request, usuario)
                    cerrar_sesiones(
                        usuario, conservar=request.session.session_key if usuario.pk == request.user.pk else None
                    )
                    registrar_cambio(request.user, usuario, "password")
                    messages.success(request, "Contraseña actualizada. Las otras sesiones se cerraron.")
                else:
                    raise ValidationError("Selecciona una acción válida.")
        except IntegrityError:
            messages.error(request, "El correo ya está registrado. Usa otra dirección.")
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        return redirect("admin_personalizado:detalle_usuario", usuario_id=usuario_id)
    evidencias = Envio.objects.filter(usuario=usuario).order_by("-fecha_envio", "-pk")
    totales = evidencias.aggregate(
        total=Count("pk"),
        archivos=Count("pk", filter=~Q(archivo_evidencia="") & Q(archivo_evidencia__isnull=False)),
        enlaces=Count("pk", filter=~Q(link_evidencia="") & Q(link_evidencia__isnull=False)),
    )
    busqueda = request.GET.get("q", "").strip()[:100]
    if busqueda:
        evidencias = evidencias.filter(Q(nombre__icontains=busqueda) | Q(tipo_evidencia__icontains=busqueda))
    return render(
        request,
        "admin_personalizado/detalle_usuario_modern.html",
        {
            "usuario": usuario,
            "grupos_disponibles": Group.objects.order_by("name"),
            "grupos_usuario": usuario.groups.all(),
            "evidencias": Paginator(evidencias, 25).get_page(request.GET.get("page")),
            "total_evidencias": totales["total"],
            "evidencias_con_archivo": totales["archivos"],
            "evidencias_con_link": totales["enlaces"],
            "busqueda": busqueda,
            "cuenta_protegida": (usuario.is_staff or usuario.is_superuser) and not request.user.is_superuser,
        },
    )


@login_required
@user_passes_test(_requerir_administrador, login_url="access_denied")
@sensitive_post_parameters()
def asignar_grupo(request, usuario_id):
    usuario = get_object_or_404(User, pk=usuario_id)
    if request.method == "POST":
        try:
            if not ConfirmarPasswordForm(request.POST, usuario=request.user).is_valid():
                raise ValidationError("Confirma tu contraseña actual para cambiar los roles.")
            with transaction.atomic():
                usuario = User.objects.select_for_update().get(pk=usuario_id)
                grupo = Group.objects.get(pk=request.POST.get("grupo_id"))
                ids = set(usuario.groups.values_list("pk", flat=True))
                if request.POST.get("accion") == "agregar":
                    ids.add(grupo.pk)
                elif request.POST.get("accion") == "quitar":
                    ids.discard(grupo.pk)
                else:
                    raise ValidationError("Selecciona una acción válida.")
                cambiar_roles(request.user, {usuario.pk: ids})
            messages.success(request, "Roles de la cuenta actualizados.")
        except (Group.DoesNotExist, ValueError, TypeError):
            messages.error(request, "El grupo seleccionado no existe.")
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
    return redirect("admin_personalizado:detalle_usuario", usuario_id=usuario_id)


@login_required
@user_passes_test(_requerir_administrador, login_url="access_denied")
@sensitive_post_parameters()
def activar_desactivar(request, usuario_id):
    get_object_or_404(User, pk=usuario_id)
    if request.method == "POST":
        try:
            if not ConfirmarPasswordForm(request.POST, usuario=request.user).is_valid():
                raise ValidationError("Confirma tu contraseña actual para cambiar el estado.")
            accion = request.POST.get("accion")
            if accion not in {"activar", "desactivar"}:
                raise ValidationError("Selecciona una acción válida.")
            cambiar_estados(request.user, [usuario_id], activo=accion == "activar")
            messages.success(request, "Estado de la cuenta actualizado.")
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
    return redirect("admin_personalizado:detalle_usuario", usuario_id=usuario_id)
