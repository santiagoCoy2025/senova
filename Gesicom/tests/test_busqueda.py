"""Regresiones de aislamiento y acceso a la búsqueda global."""

import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from notificaciones.models import Notificacion, PlazoReporte

from ..models import Envio


class BusquedaTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("buscador", email="uno@example.com")
        self.other = User.objects.create_user("otro", email="dos@example.com")
        self.user.groups.add(Group.objects.get(name="instructor"))
        self.envio = Envio.objects.create(usuario=self.user, nombre="Atlas propio", tipo_evidencia="Documento")
        self.privado = Envio.objects.create(usuario=self.other, nombre="Atlas privado", tipo_evidencia="Documento")
        self.notice = Notificacion.objects.create(
            usuario=self.user, tipo="novedad", titulo="Atlas personal", mensaje=""
        )
        Notificacion.objects.create(usuario=self.other, tipo="novedad", titulo="Atlas ajeno", mensaje="")
        self.publico = PlazoReporte.objects.create(
            titulo="Atlas público", fecha_limite=timezone.now() + timedelta(days=2)
        )
        self.restringido = PlazoReporte.objects.create(titulo="Atlas restringido", fecha_limite=timezone.now())
        self.restringido.grupos.add(Group.objects.get(name="investigador"))
        self.client.force_login(self.user)
        self.url = reverse("busqueda_global")

    def resultados(self, q="Atlas"):
        response = self.client.get(self.url, {"q": q})
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        return response.json()["resultados"]

    def test_scope_never_includes_other_users_private_records(self):
        titles = {r["titulo"] for r in self.resultados()}
        self.assertEqual(titles, {"Atlas propio", "Atlas personal", "Atlas público"})

    def test_reviewers_can_search_all_evidence_but_not_other_inboxes_or_users(self):
        self.user.groups.set([Group.objects.get(name="coordinador")])
        results = self.resultados()
        self.assertIn("Atlas privado", {r["titulo"] for r in results})
        self.assertNotIn("Atlas ajeno", {r["titulo"] for r in results})
        self.assertFalse(any(r["tipo"] == "Usuarios" for r in self.resultados("otro")))

    def test_admin_search_is_permission_aware_on_every_request(self):
        group = Group.objects.get(name="administrador")
        self.user.groups.add(group)
        results = self.resultados("otro")
        self.assertEqual(
            [r["url"] for r in results], [reverse("admin_personalizado:detalle_usuario", args=[self.other.pk])]
        )
        self.user.groups.remove(group)
        self.assertEqual(self.resultados("otro"), [])

    def test_links_to_notifications_and_deadlines_stay_scoped(self):
        notice_url = reverse("notificaciones:bandeja")
        response = self.client.get(notice_url, {"aviso": self.notice.pk})
        self.assertContains(response, "Atlas personal")
        self.assertNotContains(response, "Atlas ajeno")
        foreign = Notificacion.objects.get(titulo="Atlas ajeno")
        response = self.client.get(notice_url, {"aviso": foreign.pk})
        self.assertEqual(response.context["avisos"].paginator.count, 0)
        response = self.client.get(reverse("notificaciones:mis_plazos"), {"plazo": self.restringido.pk})
        self.assertEqual(response.context["plazos"].paginator.count, 0)

    def test_rate_limit_is_per_account_and_expires(self):
        cache.set(f"busqueda:{self.user.pk}", 60, timeout=60)
        response = self.client.get(self.url, {"q": "Atlas"})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "60")
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url, {"q": "Atlas"}).status_code, 200)
        cache.delete(f"busqueda:{self.user.pk}")
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url, {"q": "Atlas"}).status_code, 200)

    def test_short_queries_anonymous_and_post(self):
        self.assertEqual(self.resultados("a"), [])
        self.assertEqual(self.client.post(self.url, {"q": "Atlas"}).status_code, 405)
        self.client.logout()
        response = self.client.get(self.url, {"q": "Atlas"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["login_url"], reverse("login"))

    def test_each_result_type_is_bounded(self):
        Envio.objects.bulk_create(
            [Envio(usuario=self.user, nombre=f"Atlas {i}", tipo_evidencia="Doc") for i in range(40)]
        )
        results = self.resultados()
        self.assertEqual(len([r for r in results if r["tipo"] == "Evidencias"]), 5)
        self.assertLessEqual(len(results), 18)

    def test_unavailable_rate_limiter_returns_json_without_records(self):
        with patch("Gesicom.busqueda.cache.add", side_effect=ConnectionError):
            response = self.client.get(self.url, {"q": "Atlas"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("resultados", response.json())

    def test_entradas_invalidas_no_se_recortan_ni_consultan_registros(self):
        for termino in ["Atlas" + "x" * 100, "Atlas\x00"]:
            with patch("Gesicom.busqueda.cache.add") as limite:
                response = self.client.get(self.url, {"q": termino})
            self.assertEqual(response.status_code, 400)
            self.assertNotIn("resultados", response.json())
            self.assertIn("no-store", response["Cache-Control"])
            limite.assert_not_called()

    def test_termino_corto_no_usa_cuota_ni_lee_registros(self):
        from ..busqueda import buscar

        for termino in ["", "  ", " a "]:
            request = RequestFactory().get(self.url, {"q": termino})
            request.user = self.user
            with self.assertNumQueries(0), patch("Gesicom.busqueda.cache.add") as limite:
                self.assertEqual(buscar(request).content, b'{"resultados": []}')
            limite.assert_not_called()

    def test_comillas_y_operadores_sql_son_datos(self):
        self.assertEqual(self.resultados("' OR 1=1 --"), [])
        self.assertEqual(self.resultados("  Atlas  "), self.resultados("Atlas"))

    def test_plazos_comparten_orden_estable_y_no_duplican_grupos(self):
        self.user.groups.add(Group.objects.get(name="investigador"))
        self.restringido.activo = False
        self.restringido.save(update_fields=["activo"])
        fecha = timezone.now() + timedelta(days=1)
        nuevos = [PlazoReporte.objects.create(titulo=f"Atlas orden {i}", fecha_limite=fecha) for i in range(6)]
        nuevos[0].grupos.set(self.user.groups.all())
        plazos = [r["url"] for r in self.resultados() if r["tipo"] == "Plazos"]
        self.assertEqual(plazos, [reverse("notificaciones:mis_plazos") + f"?plazo={p.pk}" for p in nuevos[:4]])

    def test_personal_sin_rol_no_consulta_usuarios(self):
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.assertFalse(any(r["tipo"] == "Usuarios" for r in self.resultados("otro")))
        self.user.is_superuser = True
        self.user.save(update_fields=["is_superuser"])
        self.assertEqual([r["tipo"] for r in self.resultados("otro")], ["Usuarios"])

    def test_respuesta_solo_contiene_campos_de_presentacion(self):
        self.envio.nombre = '<img src=x onerror="alert(1)"> Atlas'
        self.envio.save(update_fields=["nombre"])
        resultados = self.resultados()
        self.assertEqual(resultados[0]["titulo"], self.envio.nombre)
        for resultado in resultados:
            self.assertSetEqual(set(resultado), {"titulo", "detalle", "url", "tipo"})

    def test_alternativa_html_de_busqueda_esta_disponible_desde_el_servidor(self):
        response = self.client.get(reverse("evidencias_list"))
        self.assertContains(response, "data-search-fallback", count=1)
        self.assertContains(response, 'id="fallback-search"')
        self.assertContains(response, 'id="global-search"', count=1)

    def test_consultas_acotadas_no_cargan_descripciones_mensajes_ni_hashes(self):
        from ..busqueda import buscar

        self.user.groups.add(Group.objects.get(name="administrador"))
        User.objects.bulk_create([User(username=f"atlas_escala_{i:04}", password="!") for i in range(1200)])
        Envio.objects.bulk_create(
            [Envio(usuario=self.user, nombre=f"Atlas escala {i}", observaciones="X" * 3000) for i in range(1200)]
        )
        PlazoReporte.objects.bulk_create(
            [
                PlazoReporte(titulo=f"Atlas escala {i}", descripcion="X" * 3000, fecha_limite=timezone.now())
                for i in range(1200)
            ]
        )
        Notificacion.objects.bulk_create(
            [
                Notificacion(usuario=self.user, tipo="novedad", titulo=f"Atlas escala {i}", mensaje="X" * 3000)
                for i in range(1200)
            ]
        )
        request = RequestFactory().get(self.url, {"q": "Atlas"})
        request.user = User.objects.get(pk=self.user.pk)
        with CaptureQueriesContext(connection) as consultas:
            response = buscar(request)
        self.assertEqual(len(json.loads(response.content)["resultados"]), 18)
        self.assertEqual(len(consultas), 5)
        for consulta in consultas:
            seleccion = consulta["sql"].split(" FROM ", 1)[0]
            for campo in ["password", "descripcion", "mensaje", "observaciones", "archivo_evidencia"]:
                self.assertNotIn(connection.ops.quote_name(campo), seleccion)
        lecturas = [c["sql"] for c in consultas if "LIMIT" in c["sql"]]
        self.assertEqual(len(lecturas), 4)
        self.assertTrue(all("OFFSET" not in sql for sql in lecturas))
        print("ESCALA búsqueda / 1200 registros por tipo: 18 resultados, 5 consultas y sin contenidos extensos.")
