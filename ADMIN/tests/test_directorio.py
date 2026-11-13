"""Directorio, conservación de filtros y operaciones administrativas acotadas."""

import csv
import datetime
import io
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth.models import Group, User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from cuentas.models import RegistroSeguridad

from ..directorio import filas_directorio, usuarios_de_pagina, usuarios_filtrados
from ..forms import FiltrosUsuariosForm
from ..services import cambiar_roles

PASSWORD = "DirectorioLocalDePruebas42!"


class NavegacionDirectorioTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("directorio_admin", password=PASSWORD)
        self.admin.groups.add(Group.objects.get(name="administrador"))
        self.member = User.objects.create_user("directorio_persona")
        self.client.force_login(self.admin)
        self.url = reverse("admin_personalizado:gestionar_usuarios")

    def test_guardar_conserva_filtros_y_pagina(self):
        response = self.client.post(
            self.url + "?q=directorio&estado=activo&page=2",
            {"accion": "roles", "contrasena_actual": PASSWORD, f"role_{self.member.pk}": "__keep__"},
        )
        self.assertRedirects(response, self.url + "?q=directorio&estado=activo&page=2", fetch_redirect_response=False)

    def test_roles_sin_cambios_no_consultan_un_grupo_por_cuenta(self):
        grupo = Group.objects.get(name="usuario")
        User.objects.bulk_create([User(username=f"directorio_lote_{i}") for i in range(100)])
        miembros = list(User.objects.filter(username__startswith="directorio_lote_"))
        User.groups.through.objects.bulk_create(
            [User.groups.through(user_id=u.pk, group_id=grupo.pk) for u in miembros]
        )
        with CaptureQueriesContext(connection) as consultas:
            self.assertEqual(cambiar_roles(self.admin, {u.pk: [grupo.pk] for u in miembros}), 0)
        lecturas = [c for c in consultas if c["sql"].lstrip().upper().startswith("SELECT")]
        self.assertLessEqual(len(lecturas), 5)
        print(f"ESCALA roles / 100 cuentas sin cambios: {len(lecturas)} consultas SELECT.")

    def test_password_incorrecto_conserva_contexto_y_no_cambia_cuentas(self):
        response = self.client.post(
            self.url + "?q=persona&estado=activo&page=3",
            {"accion": "desactivar", "usuarios": [self.member.pk], "contrasena_actual": "incorrecta"},
        )
        self.assertRedirects(response, self.url + "?q=persona&estado=activo&page=3", fetch_redirect_response=False)
        self.member.refresh_from_db()
        self.assertTrue(self.member.is_active)

    def test_regreso_ignora_destinos_y_parametros_ajenos_y_normaliza_pagina(self):
        response = self.client.post(
            self.url + "?q=directorio&next=https://example.invalid/ajeno&password=privada&page=-5",
            {"accion": "roles", "contrasena_actual": PASSWORD},
        )
        self.assertEqual(urlsplit(response["Location"]).path, self.url)
        self.assertEqual(parse_qs(urlsplit(response["Location"]).query), {"q": ["directorio"]})

    def test_alias_de_directorio_conserva_filtros_al_guardar(self):
        response = self.client.post(
            reverse("admin_personalizado:usuarios") + "?q=directorio&estado=activo",
            {"accion": "roles", "contrasena_actual": PASSWORD},
        )
        self.assertRedirects(response, self.url + "?q=directorio&estado=activo", fetch_redirect_response=False)


def contenido(response):
    return b"".join(response.streaming_content) if response.streaming else response.content


def csv_filas(response):
    return list(csv.reader(io.StringIO(contenido(response).decode("utf-8-sig"))))


class ExportacionDirectorioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("export_operador", password=PASSWORD)
        cls.admin.groups.add(Group.objects.get(name="administrador"))
        cls.root = User.objects.create_superuser("export_raiz", "raiz@example.invalid", PASSWORD)
        cls.staff = User.objects.create_user("export_personal", is_staff=True)
        cls.usuario = User.objects.create_user("export_sin_rol", email="solo_lectura@example.invalid")
        cls.grupo = Group.objects.get(name="usuario")
        cls.otro = Group.objects.get(name="instructor")
        for i in range(37):
            u = User.objects.create_user(f"equipo_csv_{i:02}", email=f"csv{i}@example.invalid", is_active=i % 2 == 0)
            u.groups.set([cls.grupo] if i % 3 else [cls.grupo, cls.otro])
        cls.url = reverse("admin_personalizado:usuarios_csv")
        cls.directory = reverse("admin_personalizado:gestionar_usuarios")

    def setUp(self):
        self.client.force_login(self.admin)

    def test_solo_administracion_o_superuser_pueden_exportar(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        for rol in ["usuario", "instructor", "investigador", "coordinador", "dinamizador"]:
            self.usuario.groups.set([Group.objects.get(name=rol)])
            self.client.force_login(self.usuario)
            self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_login(self.root)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_json_y_permisos_de_django_no_evitan_el_control_de_rol(self):
        from django.contrib.auth.models import Permission

        self.staff.user_permissions.add(Permission.objects.get(codename="view_user", content_type__app_label="auth"))
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.url, HTTP_ACCEPT="application/json").status_code, 403)

    def test_retirar_rol_impide_la_siguiente_descarga(self):
        self.admin.groups.clear()
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertFalse(RegistroSeguridad.objects.filter(accion="admin:exportar_directorio").exists())

    def test_archivo_incluye_todas_las_paginas_en_orden_de_identificador(self):
        params = {"q": "equipo_csv_"}
        pagina = self.client.get(self.directory, params)
        response = self.client.get(self.url, {**params, "page": "2"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn('filename="usuarios-gesicom.csv"', response["Content-Disposition"])
        datos = csv_filas(response)
        self.assertEqual(len(datos), 38)
        self.assertEqual(pagina.context["usuarios"].paginator.count, 37)
        self.assertEqual([int(f[0]) for f in datos[1:]], sorted(int(f[0]) for f in datos[1:]))
        self.assertEqual(len(datos[0]), 7)

    def test_busqueda_estado_y_rol_coinciden_con_el_directorio(self):
        params = {"q": "equipo_csv_", "estado": "activo", "rol": str(self.otro.pk)}
        pagina = self.client.get(self.directory, params)
        registros = csv_filas(self.client.get(self.url, params))[1:]
        esperado = set(
            User.objects.filter(username__startswith="equipo_csv_", is_active=True, groups=self.otro).values_list(
                "pk", flat=True
            )
        )
        self.assertSetEqual({int(f[0]) for f in registros}, esperado)
        self.assertEqual(len(registros), pagina.context["usuarios"].paginator.count)
        self.assertTrue(all(f[5] == "Activo" for f in registros))
        self.assertTrue(all(f[4] == "instructor | usuario" for f in registros))

    def test_filtros_invalidos_no_generan_csv_ni_auditoria(self):
        for params in [{"estado": "otro"}, {"rol": "999999999"}, {"q": "x" * 101}]:
            response = self.client.get(self.url, params)
            self.assertEqual(response.status_code, 400)
            self.assertTrue(response["Content-Type"].startswith("text/html"))
            self.assertNotIn("csv0@example.invalid", response.content.decode())
            pagina = self.client.get(self.directory, params)
            self.assertEqual(pagina.context["usuarios"].paginator.count, 0)
            self.assertIsNone(pagina.context["url_exportar"])
        self.assertFalse(RegistroSeguridad.objects.filter(accion="admin:exportar_directorio").exists())

    def test_csv_vacio_conserva_cabeceras(self):
        self.assertEqual(len(csv_filas(self.client.get(self.url, {"q": "sin-ningun-registro"}))), 1)

    def test_no_se_exportan_hashes_privilegios_claves_o_datos_de_sesion(self):
        self.admin.refresh_from_db()
        body = contenido(self.client.get(self.url)).decode("utf-8-sig")
        for secreto in [self.admin.password, PASSWORD, self.client.session.session_key, "is_superuser", "is_staff"]:
            self.assertNotIn(secreto, body)

    def test_csv_conserva_unicode_comillas_y_neutraliza_formulas(self):
        u = User.objects.create_user("=equipo_csv_formula", first_name="+Nómina", last_name='Gómez, "Luz"')
        grupo = Group.objects.create(name="@rol_de_prueba")
        u.groups.set([grupo])
        datos = csv_filas(self.client.get(self.url, {"q": "equipo_csv_formula"}))[1]
        self.assertEqual(datos[1], "'=equipo_csv_formula")
        self.assertEqual(datos[2], '\'+Nómina Gómez, "Luz"')
        self.assertEqual(datos[4], "'@rol_de_prueba")

    def test_fecha_de_colombia_no_depende_de_la_zona_activada(self):
        User.objects.filter(pk=self.usuario.pk).update(
            date_joined=datetime.datetime(2026, 11, 14, 4, 59, 59, tzinfo=datetime.UTC)
        )
        with timezone.override("Asia/Tokyo"):
            datos = csv_filas(self.client.get(self.url, {"q": self.usuario.username}))
        self.assertEqual(datos[1][6], "2026-11-13 23:59:59 -0500")

    def test_solicitud_valida_se_audita_sin_guardar_la_busqueda(self):
        self.client.get(self.url, {"q": "csv0@example.invalid"})
        registro = RegistroSeguridad.objects.get(accion="admin:exportar_directorio")
        self.assertEqual(registro.actor, self.admin)
        self.assertEqual(registro.ruta, self.url)
        self.assertEqual(registro.direccion_ip, "127.0.0.1")

    def test_head_y_post_no_crean_solicitudes_de_exportacion(self):
        self.assertEqual(self.client.head(self.url).status_code, 200)
        self.assertEqual(self.client.post(self.url).status_code, 405)
        self.assertFalse(RegistroSeguridad.objects.filter(accion="admin:exportar_directorio").exists())

    def test_enlace_y_accion_reflejan_los_filtros_aplicados(self):
        params = {"q": "equipo_csv_", "estado": "activo", "rol": str(self.grupo.pk), "page": "2"}
        response = self.client.get(self.directory, params, HTTP_X_WORKSPACE_FRAGMENT="1")
        enlace = response.context["url_exportar"]
        self.assertEqual(parse_qs(urlsplit(enlace).query), {k: [v] for k, v in params.items() if k != "page"})
        self.assertEqual(
            parse_qs(urlsplit(response.context["regreso_directorio"]).query), {k: [v] for k, v in params.items()}
        )
        self.assertEqual(response["X-Workspace-Fragment"], "1")
        self.assertContains(response, "Descargar CSV filtrado", count=1)

    def test_consulta_de_pagina_no_carga_hashes_y_roles_no_generan_n_mas_uno(self):
        filtros = FiltrosUsuariosForm({"q": "equipo_csv_"}, grupos=list(Group.objects.all()))
        with CaptureQueriesContext(connection) as consultas:
            registros = list(usuarios_de_pagina(usuarios_filtrados(filtros))[:25])
            for usuario in registros:
                usuario.get_full_name()
                list(usuario.groups.all())
        self.assertEqual(len(consultas), 2)
        self.assertTrue(all("password" in usuario.get_deferred_fields() for usuario in registros))
        self.assertTrue(all(connection.ops.quote_name("password") not in c["sql"] for c in consultas))


class LotesDirectorioTests(TestCase):
    def test_exportacion_limita_sql_y_no_incluye_altas_posteriores_al_corte(self):
        User.objects.bulk_create([User(username=f"lote_directorio_{i:04}") for i in range(1200)], batch_size=500)
        filtros = FiltrosUsuariosForm({"q": "lote_directorio_"}, grupos=list(Group.objects.all()))
        consulta = usuarios_filtrados(filtros)
        generador = filas_directorio(consulta)
        next(generador)
        with CaptureQueriesContext(connection) as consultas:
            primero = next(generador)
        alta = User.objects.create_user("lote_directorio_nuevo")
        with CaptureQueriesContext(connection) as restantes:
            datos = [primero, *generador]
        todas = [*consultas, *restantes]
        self.assertEqual(len(datos), 1200)
        self.assertNotIn(alta.pk, [fila[0] for fila in datos])
        self.assertEqual(len(todas), 7)
        lecturas_usuario = [
            c["sql"]
            for c in todas
            if "FROM " + connection.ops.quote_name("auth_user") in c["sql"] and "MAX(" not in c["sql"]
        ]
        self.assertEqual(len(lecturas_usuario), 3)
        self.assertTrue(all("LIMIT 500" in sql.upper() and "OFFSET" not in sql.upper() for sql in lecturas_usuario))
        self.assertTrue(all(connection.ops.quote_name("password") not in c["sql"] for c in todas))
        print("ESCALA CSV directorio / 1200 usuarios: 7 consultas, lotes SQL de hasta 500 y sin OFFSET.")
