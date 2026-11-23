"""Inicio local y reparación del entorno sin cambiar datos ni ajustes de MySQL."""

import contextlib
import io
import json
import os
import socket
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

import iniciar
import manage
from scripts import configurar_entorno
from SENNOVA.desarrollo import archivo_perfil, python_del_entorno


class InicioSencilloTests(SimpleTestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory(prefix="GESICOM inicio á con espacios ")
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)

    @patch("iniciar.configurar_entorno.main", return_value=0)
    def test_la_preparacion_sencilla_no_inicia_servidor_ni_instala_herramientas(self, preparar):
        with patch("iniciar.socket.socket") as red:
            self.assertEqual(iniciar.main(["--preparar", "--extensiones"]), 0)
        red.assert_not_called()
        argumentos = preparar.call_args.args[0]
        self.assertIn("--solo-ejecucion", argumentos)
        self.assertIn("--reparar-entorno", argumentos)
        self.assertIn("--inicio-rapido", argumentos)
        self.assertIn("--extensiones", argumentos)
        self.assertNotIn("--ejecutar", argumentos)

    @patch("iniciar.configurar_entorno.main", return_value=0)
    def test_un_puerto_ocupado_no_cambia_entorno_ni_datos(self, preparar):
        with socket.socket() as servidor:
            servidor.bind(("127.0.0.1", 0))
            servidor.listen(1)
            puerto = servidor.getsockname()[1]
            with contextlib.redirect_stderr(io.StringIO()) as errores:
                self.assertEqual(iniciar.main(["--puerto", str(puerto)]), 2)
        preparar.assert_not_called()
        self.assertIn("--puerto 8001", errores.getvalue())

    @patch("iniciar.configurar_entorno.main", return_value=7)
    def test_un_fallo_de_preparacion_se_transmite_al_lanzador(self, preparar):
        self.assertEqual(iniciar.main(["--preparar"]), 7)

    @patch("iniciar.configurar_entorno.main", return_value=0)
    def test_un_puerto_cerrado_recientemente_no_impide_reiniciar(self, preparar):
        with socket.socket() as servidor:
            servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            servidor.bind(("127.0.0.1", 0))
            servidor.listen(1)
            puerto = servidor.getsockname()[1]
            with socket.create_connection(("127.0.0.1", puerto), timeout=1) as cliente:
                conexion, _ = servidor.accept()
                conexion.close()
                self.assertEqual(cliente.recv(1), b"")
        self.assertEqual(iniciar.main(["--puerto", str(puerto)]), 0)
        self.assertIn("--ejecutar", preparar.call_args.args[0])

    @patch.dict(os.environ, {"DJANGO_SETTINGS_MODULE": ""})
    def test_runserver_de_una_copia_preparada_elige_el_perfil_aislado(self):
        archivo_perfil(self.raiz).parent.mkdir(parents=True)
        archivo_perfil(self.raiz).touch()
        (self.raiz / ".env").write_text("DB_ENGINE=mysql\n", encoding="utf-8")
        self.assertEqual(manage.configuracion_inicial(["manage.py", "runserver"], self.raiz), "SENNOVA.local_settings")

    @patch.dict(os.environ, {"DJANGO_SETTINGS_MODULE": ""})
    def test_runserver_sin_preparacion_indica_el_comando_sencillo(self):
        with self.assertRaisesRegex(RuntimeError, "python iniciar.py"):
            manage.configuracion_inicial(["manage.py", "runserver"], self.raiz)

    def test_runserver_respeta_una_configuracion_explicita_del_proceso(self):
        with patch.dict(os.environ, {"DJANGO_SETTINGS_MODULE": "SENNOVA.settings"}):
            self.assertEqual(manage.configuracion_inicial(["manage.py", "runserver"], self.raiz), "SENNOVA.settings")

    @patch.dict(os.environ, {"DJANGO_SETTINGS_MODULE": ""})
    def test_las_opciones_explicitas_y_los_comandos_operativos_conservan_su_configuracion(self):
        archivo_perfil(self.raiz).parent.mkdir(parents=True)
        archivo_perfil(self.raiz).touch()
        for args in [
            ["runserver", "--settings=SENNOVA.settings"],
            ["runserver", "--settings", "SENNOVA.settings"],
            ["migrate"],
            ["procesar_notificaciones"],
            ["collectstatic"],
            ["check"],
        ]:
            with self.subTest(args=args):
                self.assertEqual(manage.configuracion_inicial(["manage.py", *args], self.raiz), "SENNOVA.settings")

    def crear_estructura(self, carpeta=None):
        carpeta = carpeta or self.raiz / ".venv"
        python = python_del_entorno(self.raiz)
        python.parent.mkdir(parents=True, exist_ok=True)
        python.touch()
        (carpeta / "pyvenv.cfg").write_text("version de prueba\n", encoding="utf-8")

    def informacion(self, *, version=None):
        return json.dumps(
            {
                "version": version or list(sys.version_info[:2]),
                "prefix": str(self.raiz / ".venv"),
                "base": str(self.raiz / "Python base"),
            }
        )

    @patch("scripts.configurar_entorno.venv.EnvBuilder")
    @patch("scripts.configurar_entorno.subprocess.check_output")
    def test_un_entorno_incompleto_se_conserva_antes_de_repararlo(self, salida, builder):
        viejo = self.raiz / ".venv"
        viejo.mkdir()
        (viejo / "conservar.txt").write_bytes(b"Contenido anterior")
        privado = self.raiz / ".env"
        privado.write_bytes(b"DB_ENGINE=mysql\nDB_PASSWORD=solo-prueba\n")
        base = archivo_perfil(self.raiz).parent / "db.sqlite3"
        base.parent.mkdir(parents=True)
        base.write_bytes(b"Datos locales previos")
        builder.return_value.create.side_effect = self.crear_estructura
        salida.return_value = self.informacion()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(configurar_entorno.crear_entorno(self.raiz, reparar=True), python_del_entorno(self.raiz))
        respaldos = list((self.raiz / ".local/entornos").glob("venv-*"))
        self.assertEqual(len(respaldos), 1)
        self.assertEqual((respaldos[0] / "conservar.txt").read_bytes(), b"Contenido anterior")
        self.assertEqual(privado.read_bytes(), b"DB_ENGINE=mysql\nDB_PASSWORD=solo-prueba\n")
        self.assertEqual(base.read_bytes(), b"Datos locales previos")

    @patch("scripts.configurar_entorno.venv.EnvBuilder")
    @patch("scripts.configurar_entorno.subprocess.check_output")
    def test_un_entorno_de_otra_version_se_conserva_al_repararlo(self, salida, builder):
        self.crear_estructura()
        (self.raiz / ".venv/conservar.txt").write_bytes(b"Otra version")
        otra = [3, 12] if sys.version_info[:2] != (3, 12) else [3, 15]
        salida.side_effect = [self.informacion(version=otra), self.informacion()]
        builder.return_value.create.side_effect = self.crear_estructura
        with contextlib.redirect_stdout(io.StringIO()):
            configurar_entorno.crear_entorno(self.raiz, reparar=True)
        self.assertEqual(len(list((self.raiz / ".local/entornos").glob("venv-*/conservar.txt"))), 1)

    @patch("scripts.configurar_entorno.venv.EnvBuilder")
    @patch("scripts.configurar_entorno.subprocess.check_output")
    def test_un_entorno_valido_no_se_reemplaza_aunque_se_pida_reparar(self, salida, builder):
        self.crear_estructura()
        salida.return_value = self.informacion()
        configurar_entorno.crear_entorno(self.raiz, reparar=True)
        builder.assert_not_called()
        self.assertFalse((self.raiz / ".local/entornos").exists())

    @patch("scripts.configurar_entorno.venv.EnvBuilder")
    def test_si_falla_la_reparacion_se_conserva_el_respaldo(self, builder):
        (self.raiz / ".venv").mkdir()
        (self.raiz / ".venv/conservar.txt").write_bytes(b"No perder")
        builder.return_value.create.side_effect = OSError("No se pudo crear")
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(OSError):
            configurar_entorno.crear_entorno(self.raiz, reparar=True)
        respaldos = list((self.raiz / ".local/entornos").glob("venv-*/conservar.txt"))
        self.assertEqual(len(respaldos), 1)
        self.assertEqual(respaldos[0].read_bytes(), b"No perder")

    @patch("scripts.configurar_entorno.ejecutar")
    @patch("scripts.configurar_entorno.crear_entorno")
    def test_la_instalacion_minima_no_pide_las_herramientas_de_desarrollo(self, crear, ejecutar):
        crear.return_value = python_del_entorno(self.raiz)
        with contextlib.redirect_stdout(io.StringIO()):
            configurar_entorno.preparar(self.raiz, solo_ejecucion=True)
        instalar = ejecutar.call_args_list[0].args[0]
        self.assertIn(self.raiz / "requirements.txt", instalar)
        self.assertNotIn(self.raiz / "requirements-dev.txt", instalar)
        self.assertNotIn(self.raiz / "requirements-mysql.txt", instalar)
        self.assertIn("--only-binary=:all:", instalar)

    @patch("scripts.configurar_entorno.ejecutar")
    @patch("scripts.configurar_entorno.preparar")
    def test_el_puerto_elegido_llega_a_la_web_y_al_trabajador(self, preparar, ejecutar):
        self.assertEqual(configurar_entorno.main(["--ejecutar", "--solo-ejecucion", "--puerto", "8002"]), 0)
        argumentos = ejecutar.call_args.args[0]
        self.assertEqual(argumentos[-2:], ["--puerto", "8002"])
        self.assertTrue(preparar.call_args.kwargs["solo_ejecucion"])
