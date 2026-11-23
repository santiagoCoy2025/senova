"""La preparación local conserva secretos y limita el inicio rápido a SQLite."""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from scripts import configurar_entorno, ejecutar_local
from SENNOVA.desarrollo import archivo_perfil, entorno_local


class EntornoDesarrolloTests(SimpleTestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory(prefix="gesicom con espacios á ")
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)

    def test_una_configuracion_existente_se_conserva_exactamente(self):
        archivo = self.raiz / ".env"
        contenido = b'# Privado\nDB_ENGINE=mysql\nDB_PASSWORD="clave de prueba con espacios"\n'
        archivo.write_bytes(contenido)
        self.assertTrue(configurar_entorno.crear_configuracion_local(self.raiz))
        self.assertFalse(configurar_entorno.crear_configuracion_local(self.raiz))
        self.assertEqual(archivo.read_bytes(), contenido)

    def test_la_configuracion_nueva_tiene_secreto_propio_y_correo_solo_local(self):
        self.assertTrue(configurar_entorno.crear_configuracion_local(self.raiz))
        archivo = archivo_perfil(self.raiz)
        valores = dict(linea.split("=", 1) for linea in archivo.read_text().splitlines() if "=" in linea)
        self.assertEqual(valores["DB_ENGINE"], "sqlite")
        self.assertEqual(valores["REDIS_URL"], "")
        self.assertEqual(valores["EMAIL_BACKEND"], "django.core.mail.backends.console.EmailBackend")
        self.assertGreaterEqual(len(valores["DJANGO_SECRET_KEY"]), 40)
        otra = self.raiz / "otra copia"
        otra.mkdir()
        configurar_entorno.crear_configuracion_local(otra)
        self.assertNotEqual(archivo.read_text(), archivo_perfil(otra).read_text())
        if os.name != "nt":
            self.assertEqual(archivo.stat().st_mode & 0o777, 0o600)

    @patch("scripts.configurar_entorno.ejecutar")
    @patch("scripts.configurar_entorno.crear_entorno")
    def test_preparar_un_proyecto_existente_aisla_la_base_y_conserva_env(self, crear, ejecutar):
        archivo = self.raiz / ".env"
        contenido = "DB_ENGINE=mysql\nDJANGO_DEBUG=False\n"
        archivo.write_text(contenido)
        crear.return_value = self.raiz / ".venv" / "bin" / "python"
        with contextlib.redirect_stdout(io.StringIO()):
            configurar_entorno.preparar(self.raiz, inicio_rapido=True)
        self.assertEqual(archivo.read_text(), contenido)
        self.assertEqual(ejecutar.call_count, 7)
        instalar, comprobar = [llamada.args[0] for llamada in ejecutar.call_args_list[:2]]
        self.assertIn("--only-binary=:all:", instalar)
        self.assertNotIn(self.raiz / "requirements-mysql.txt", instalar)
        self.assertIn("--require-virtualenv", instalar)
        self.assertIn(self.raiz / "requirements-dev.txt", instalar)
        self.assertEqual(comprobar[-1], "check")
        self.assertNotIn(self.raiz / "manage.py", comprobar)

    @patch("scripts.configurar_entorno.ejecutar")
    @patch("scripts.configurar_entorno.crear_entorno")
    def test_el_inicio_nuevo_no_usa_conexiones_heredadas_del_proceso(self, crear, ejecutar):
        crear.return_value = self.raiz / ".venv" / "bin" / "python"
        heredadas = {
            "DB_ENGINE": "mysql",
            "REDIS_URL": "redis://servidor.example.invalid:6379/0",
            "EMAIL_BACKEND": "SENNOVA.email_backend.SMTPBackend",
            "DJANGO_SETTINGS_MODULE": "configuracion_externa",
        }
        with patch.dict(os.environ, heredadas), contextlib.redirect_stdout(io.StringIO()):
            configurar_entorno.preparar(self.raiz, inicio_rapido=True)
            self.assertEqual(os.environ["DB_ENGINE"], "mysql")
        comandos = [c for c in ejecutar.call_args_list if self.raiz / "manage.py" in c.args[0]]
        self.assertEqual(len(comandos), 5)
        for llamada in comandos:
            entorno = llamada.kwargs["entorno"]
            self.assertEqual(entorno["DB_ENGINE"], "sqlite")
            self.assertEqual(entorno["REDIS_URL"], "")
            self.assertEqual(entorno["EMAIL_BACKEND"], "django.core.mail.backends.console.EmailBackend")
            self.assertEqual(entorno["DJANGO_SETTINGS_MODULE"], "SENNOVA.local_settings")
            self.assertEqual(entorno["DJANGO_ENV_FILE"], str(archivo_perfil(self.raiz)))
            self.assertEqual(llamada.args[1], self.raiz)
        self.assertTrue(any("crear_usuarios_revision" in c.args[0] for c in comandos))

    def test_un_directorio_incompleto_no_se_borra_ni_se_reemplaza(self):
        carpeta = self.raiz / ".venv"
        carpeta.mkdir()
        marcador = carpeta / "conservar.txt"
        marcador.write_text("Datos previos")
        with self.assertRaisesRegex(RuntimeError, "incompleto"):
            configurar_entorno.crear_entorno(self.raiz)
        self.assertEqual(marcador.read_text(), "Datos previos")

    def preparar_estructura(self):
        carpeta = self.raiz / ".venv"
        python = configurar_entorno.python_del_entorno(self.raiz)
        python.parent.mkdir(parents=True)
        python.touch()
        (carpeta / "pyvenv.cfg").write_text(f"version = {sys.version_info.major}.{sys.version_info.minor}.0\n")
        return carpeta, python

    @patch("scripts.configurar_entorno.subprocess.check_output")
    def test_no_se_instalan_paquetes_en_un_python_global_o_de_otra_version(self, salida):
        carpeta, _ = self.preparar_estructura()
        for version, prefix, base in [
            ([3, 11], str(carpeta), "/python-base"),
            (list(sys.version_info[:2]), "/python-global", "/python-global"),
        ]:
            with self.subTest(version=version, prefix=prefix):
                salida.return_value = json.dumps({"version": version, "prefix": prefix, "base": base})
                with self.assertRaisesRegex(RuntimeError, "aislado"):
                    configurar_entorno.crear_entorno(self.raiz)

    @patch("scripts.configurar_entorno.venv.EnvBuilder")
    @patch("scripts.configurar_entorno.subprocess.check_output")
    def test_un_entorno_aislado_existente_se_reutiliza(self, salida, builder):
        carpeta, python = self.preparar_estructura()
        salida.return_value = json.dumps(
            {"version": list(sys.version_info[:2]), "prefix": str(carpeta), "base": "/python-base"}
        )
        self.assertEqual(configurar_entorno.crear_entorno(self.raiz), python)
        builder.assert_not_called()

    @patch("scripts.configurar_entorno.preparar")
    def test_otra_version_falla_antes_de_crear_archivos_o_instalar(self, preparar):
        with (
            patch("scripts.configurar_entorno.sys.version_info", (3, 11, 0)),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(configurar_entorno.main([]), 2)
        preparar.assert_not_called()

    @patch("scripts.configurar_entorno.preparar")
    def test_python_315_y_las_versiones_compatibles_pueden_preparar_el_proyecto(self, preparar):
        for version in [(3, 12, 0), (3, 13, 0), (3, 14, 0), (3, 15, 1)]:
            with self.subTest(version=version), patch("scripts.configurar_entorno.sys.version_info", version):
                self.assertEqual(configurar_entorno.main(["--inicio-rapido"]), 0)
                preparar.assert_called_with(
                    configurar_entorno.ROOT,
                    inicio_rapido=True,
                    mysql=False,
                    extensiones=False,
                    solo_ejecucion=False,
                    reparar_entorno=False,
                )

    @patch("scripts.configurar_entorno.subprocess.check_output")
    def test_un_entorno_de_otro_python_no_se_usa_silenciosamente(self, salida):
        carpeta, _ = self.preparar_estructura()
        version = [3, 15] if sys.version_info[:2] != (3, 15) else [3, 12]
        salida.return_value = json.dumps({"version": version, "prefix": str(carpeta), "base": "/python-base"})
        with self.assertRaisesRegex(RuntimeError, "misma versión"):
            configurar_entorno.crear_entorno(self.raiz)

    @patch("scripts.configurar_entorno.ejecutar")
    @patch("scripts.configurar_entorno.crear_entorno")
    def test_una_preparacion_parcial_puede_repetirse_sin_cambiar_el_secreto(self, crear, ejecutar):
        crear.return_value = self.raiz / ".venv" / "bin" / "python"
        configurar_entorno.crear_configuracion_local(self.raiz)
        antes = archivo_perfil(self.raiz).read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            configurar_entorno.preparar(self.raiz, inicio_rapido=True)
        self.assertEqual(archivo_perfil(self.raiz).read_bytes(), antes)
        comandos = [c.args[0] for c in ejecutar.call_args_list if self.raiz / "manage.py" in c.args[0]]
        self.assertIn("createcachetable", comandos[0])
        self.assertIn("migrate", comandos[1])
        self.assertIn("crear_usuarios_revision", comandos[3])

    def test_el_perfil_real_no_carga_mysql_ni_credenciales_heredadas(self):
        configurar_entorno.crear_configuracion_local(self.raiz)
        (self.raiz / ".env").write_text("DB_ENGINE=mysql\nDJANGO_DEBUG=False\n", encoding="utf-8")
        codigo = """
import json, sys
from pathlib import Path
import SENNOVA.desarrollo as desarrollo
desarrollo.RAIZ = Path(sys.argv[1])
from SENNOVA import local_settings as s
print(json.dumps({
    'motor': s.DATABASES['default']['ENGINE'], 'base': str(s.DATABASES['default']['NAME']),
    'media': str(s.MEDIA_ROOT), 'estaticos': str(s.STATIC_ROOT),
    'debug': s.DEBUG, 'https': s.SECURE_SSL_REDIRECT, 'correo': s.EMAIL_BACKEND,
    'sin_credenciales': not s.EMAIL_HOST_PASSWORD and not s.EMAIL_OAUTH2_ACCESS_TOKEN,
    'mysql_cargado': 'MySQLdb' in sys.modules,
}))
"""
        entorno = {
            **os.environ,
            "DB_ENGINE": "mysql",
            "DJANGO_DEBUG": "False",
            "DJANGO_SECRET_KEY": "clave-heredada-no-usar",
            "REDIS_URL": "redis://example.invalid:6379/0",
            "EMAIL_BACKEND": "SENNOVA.email_backend.SMTPBackend",
            "EMAIL_HOST_PASSWORD": "no-usar",
            "EMAIL_OAUTH2_ACCESS_TOKEN": "no-usar",
            "DJANGO_ENV_FILE": "archivo-inexistente",
        }
        salida = subprocess.check_output(
            [sys.executable, "-c", codigo, str(self.raiz)], cwd=configurar_entorno.ROOT, env=entorno, text=True
        )
        datos = json.loads(salida)
        self.assertEqual(datos["motor"], "django.db.backends.sqlite3")
        self.assertEqual(Path(datos["base"]), self.raiz / ".local/desarrollo/db.sqlite3")
        self.assertEqual(Path(datos["media"]), self.raiz / ".local/desarrollo/media")
        self.assertEqual(Path(datos["estaticos"]), self.raiz / ".local/desarrollo/staticfiles")
        self.assertTrue(datos["debug"])
        self.assertTrue(datos["sin_credenciales"])
        self.assertFalse(datos["https"])
        self.assertFalse(datos["mysql_cargado"])
        self.assertEqual(datos["correo"], "django.core.mail.backends.console.EmailBackend")

    @patch("scripts.configurar_entorno.shutil.which", return_value=None)
    @patch("scripts.configurar_entorno.ejecutar")
    def test_no_tener_code_en_path_no_impide_preparar_la_aplicacion(self, ejecutar, which):
        with contextlib.redirect_stdout(io.StringIO()) as salida:
            configurar_entorno.instalar_extensiones(self.raiz)
        ejecutar.assert_not_called()
        self.assertIn("Recommended Extensions", salida.getvalue())

    @patch("scripts.configurar_entorno.shutil.which")
    @patch("scripts.configurar_entorno.ejecutar")
    def test_la_cli_windows_admite_rutas_con_espacios_sin_shell(self, ejecutar, which):
        instalacion = self.raiz / "Microsoft VS Code"
        (instalacion / "bin").mkdir(parents=True)
        (instalacion / "Code.exe").touch()
        cli = instalacion / "resources/app/out/cli.js"
        cli.parent.mkdir(parents=True)
        cli.touch()
        which.return_value = str(instalacion / "bin/code.cmd")
        (self.raiz / ".vscode").mkdir()
        (self.raiz / ".vscode/extensions.json").write_text('{"recommendations": ["ms-python.python"]}')
        configurar_entorno.instalar_extensiones(self.raiz)
        argumentos = ejecutar.call_args.args[0]
        self.assertEqual(argumentos[:2], [str(instalacion / "Code.exe"), str(cli)])
        self.assertEqual(argumentos[2:], ["--install-extension", "ms-python.python"])
        self.assertEqual(ejecutar.call_args.kwargs["entorno"]["ELECTRON_RUN_AS_NODE"], "1")

    def test_el_arranque_sin_perfil_ofrece_la_preparacion_correcta(self):
        with self.assertRaisesRegex(RuntimeError, "configurar_entorno"):
            ejecutar_local.iniciar(self.raiz)

    def test_el_puerto_alternativo_se_aplica_a_enlaces_y_origenes_csrf(self):
        entorno = entorno_local(self.raiz, puerto=8001)
        self.assertEqual(entorno["PUBLIC_BASE_URL"], "http://127.0.0.1:8001")
        self.assertEqual(entorno["CSRF_TRUSTED_ORIGINS"], "http://localhost:8001,http://127.0.0.1:8001")
        for puerto in (0, 1023, 65536):
            with self.subTest(puerto=puerto), self.assertRaises(ValueError):
                entorno_local(self.raiz, puerto=puerto)

    @patch("scripts.ejecutar_local.subprocess.Popen")
    def test_si_falla_el_segundo_proceso_se_detiene_el_primero(self, popen):
        _, python = self.preparar_estructura()
        configurar_entorno.crear_configuracion_local(self.raiz)
        from unittest.mock import Mock

        servidor = Mock()
        servidor.poll.return_value = None
        popen.side_effect = [servidor, OSError("No se pudo iniciar el trabajador")]
        with self.assertRaises(OSError):
            ejecutar_local.iniciar(self.raiz)
        servidor.terminate.assert_called_once()
        servidor.wait.assert_called_once_with(timeout=10)
        self.assertEqual(popen.call_args_list[0].args[0][0], str(python))
        self.assertEqual(popen.call_args_list[0].kwargs["env"]["DJANGO_SETTINGS_MODULE"], "SENNOVA.local_settings")
