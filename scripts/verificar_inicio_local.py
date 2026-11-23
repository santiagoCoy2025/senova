#!/usr/bin/env python3
"""Prueba HTTP reproducible del perfil local, sin Docker ni servicios externos."""

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.ejecutar_local import detener
from SENNOVA.desarrollo import VARIABLES_LOCALES, archivo_perfil, entorno_local, python_del_entorno


def verificar(raiz=ROOT, *, solo_ejecucion=False):
    python = python_del_entorno(raiz)
    entorno = entorno_local(raiz)
    entorno["PYTHONUTF8"] = "1"
    perfil_antes = archivo_perfil(raiz).read_bytes()
    archivo_original = raiz / ".env"
    original_antes = archivo_original.read_bytes() if archivo_original.exists() else None
    codigo = """
import importlib.util, json, django
from pathlib import Path
django.setup()
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
assert importlib.util.find_spec('MySQLdb') is None, 'El entorno portátil debe instalarse sin mysqlclient'
assert importlib.util.find_spec('gunicorn') is None, 'Gunicorn pertenece al perfil de producción'
assert settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3'
assert Path(settings.DATABASES['default']['NAME']).parent == settings.BASE_DIR / '.local' / 'desarrollo'
assert get_user_model().objects.filter(username__startswith='revision.').count() == 6
assert settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend'
assert not settings.EMAIL_HOST_PASSWORD
assert cache.get('notificaciones:trabajador'), 'La señal del trabajador debe compartirse entre procesos'
print(json.dumps({'usuarios_revision': 6, 'cache_compartida': True, 'sin_cliente_mysql': True}))
"""
    subprocess.run(
        [str(python), "manage.py", "procesar_notificaciones", "--lote", "1"], cwd=raiz, env=entorno, check=True
    )
    if solo_ejecucion:
        codigo += "\nassert all(importlib.util.find_spec(m) is None for m in ('debugpy', 'ruff', 'pip_audit')), 'El inicio mínimo no debe instalar las herramientas de desarrollo'\n"
    subprocess.run([str(python), "-c", codigo], cwd=raiz, env=entorno, check=True)
    subprocess.run(
        [
            str(python),
            "manage.py",
            "test",
            "SENNOVA.tests.test_entorno_desarrollo",
            "SENNOVA.tests.test_inicio_sencillo",
            "ADMIN.tests.test_auditoria.AuditoriaTests.test_pagination_is_stable_and_export_includes_all_pages_without_n_plus_one",
            "notificaciones.tests.test_bandeja_interactiva.BandejaInteractivaTests.test_large_filtered_update_and_page_avoid_one_query_per_notice",
            "--settings=SENNOVA.test_settings",
            "--noinput",
        ],
        cwd=raiz,
        env=entorno,
        check=True,
    )
    comprobar_http(raiz, entorno, ["-m", "waitress"])
    variables = set(VARIABLES_LOCALES) | {
        "DJANGO_ENV_FILE",
        "DJANGO_LOG_DIR",
        "GESICOM_LOCAL_PORT",
        "DJANGO_SECRET_KEY",
    }
    limpio = {clave: valor for clave, valor in os.environ.items() if clave not in variables}
    comprobar_http(raiz, limpio, ["manage.py", "runserver"])
    assert archivo_perfil(raiz).read_bytes() == perfil_antes, "El secreto local debe conservarse"
    original_despues = archivo_original.read_bytes() if archivo_original.exists() else None
    assert original_despues == original_antes, ".env debe conservarse exactamente"
    print(
        "Inicio portátil verificado: SQLite, seis roles, trabajador, caché compartida, HTTP y configuración conservada."
    )


def comprobar_http(raiz, entorno, comando):
    with socket.socket() as reserva:
        reserva.bind(("127.0.0.1", 0))
        puerto = reserva.getsockname()[1]
    argumentos = (
        [f"--listen=127.0.0.1:{puerto}", "SENNOVA.wsgi:application"]
        if comando == ["-m", "waitress"]
        else [f"127.0.0.1:{puerto}", "--noreload"]
    )
    diagnostico = """
import faulthandler, runpy, sys
faulthandler.dump_traceback_later(45)
objetivo = sys.argv.pop(1)
sys.argv[0] = objetivo
runpy.run_path(objetivo, run_name="__main__")
"""
    prefijo = ["-c", diagnostico] if comando == ["manage.py", "runserver"] else []
    with tempfile.TemporaryFile() as registro:
        proceso = subprocess.Popen(
            [str(python_del_entorno(raiz)), "-u", *prefijo, *comando, *argumentos],
            cwd=raiz,
            env=entorno,
            stdout=registro,
            stderr=subprocess.STDOUT,
        )
        try:
            limite = time.monotonic() + 60
            while True:
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/health/", timeout=2) as respuesta:
                        assert json.load(respuesta)["estado"] == "ok"
                    break
                except (urllib.error.URLError, TimeoutError):
                    if proceso.poll() is not None or time.monotonic() >= limite:
                        registro.seek(0)
                        salida = registro.read().decode("utf-8", errors="replace")
                        ruta = raiz / ".local" / "desarrollo" / "diagnostico-http.log"
                        ruta.write_text(salida, encoding="utf-8")
                        ruta.chmod(0o600)
                        if os.environ.get("GITHUB_ACTIONS") == "true":
                            print(salida[-6000:], file=sys.stderr)
                        raise RuntimeError(
                            f"El servidor local no completó el arranque: {ruta}. Última respuesta: {proceso.poll()}."
                        ) from None
                    time.sleep(0.25)
            with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/login/", timeout=5) as respuesta:
                assert respuesta.status == 200
                assert b"csrfmiddlewaretoken" in respuesta.read()
        finally:
            detener([proceso])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solo-ejecucion", action="store_true")
    verificar(solo_ejecucion=parser.parse_args().solo_ejecucion)
