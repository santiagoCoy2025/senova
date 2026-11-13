from django.urls import path

from . import views

app_name = "admin_personalizado"

urlpatterns = [
    path("", views.panel_control, name="dashboard"),
    path("actividad/", views.actividad, name="actividad"),
    path("actividad.csv", views.actividad_csv, name="actividad_csv"),
    path("usuarios/", views.gestionar_usuarios, name="usuarios"),
    path("usuarios.csv", views.usuarios_csv, name="usuarios_csv"),
    path("gestionar-usuarios/", views.gestionar_usuarios, name="gestionar_usuarios"),
    path("usuario/<int:usuario_id>/", views.detalle_usuario, name="detalle_usuario"),
    path("usuario/<int:usuario_id>/asignar-grupo/", views.asignar_grupo, name="asignar_grupo"),
    path("usuario/<int:usuario_id>/activar-desactivar/", views.activar_desactivar, name="activar_desactivar"),
    path("crear-usuario/", views.crear_usuario, name="crear_usuario"),
    path("permisos/", views.permisos, name="permisos"),
    path("base-datos/", views.base_datos, name="base_datos"),
]
