#!/usr/bin/env python3
"""Prepara .venv para VS Code en Windows, macOS y Linux, sin servicios externos."""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import venv
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from SENNOVA.desarrollo import crear_configuracion_local, entorno_local, python_del_entorno

PYTHON_SOPORTADOS = {(3, 12), (3, 13), (3, 14), (3, 15)}


def verificar_entorno(raiz):
    carpeta = raiz / ".venv"
    python = python_del_entorno(raiz)
    if not (carpeta / "pyvenv.cfg").is_file() or not python.is_file():
        raise RuntimeError(".venv existe pero está incompleto. Renómbralo y vuelve a ejecutar este comando.")
    try:
        salida = subprocess.check_output(
            [
                str(python),
                "-c",
                "import json,sys; print(json.dumps({'version':list(sys.version_info[:2]),"
                "'prefix':sys.prefix,'base':sys.base_prefix}))",
            ],
            text=True,
            cwd=raiz,
        )
        info = json.loads(salida)
        valido = (
            tuple(info["version"]) in PYTHON_SOPORTADOS
            and tuple(info["version"]) == tuple(sys.version_info[:2])
            and Path(info["prefix"]).resolve() == carpeta.resolve()
            and info["prefix"] != info["base"]
        )
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        raise RuntimeError(
            "No se pudo verificar .venv. Renómbralo y vuelve a prepararlo con tu Python compatible."
        ) from error
    if not valido:
        raise RuntimeError(
            ".venv debe ser un entorno aislado de la misma versión de Python que ejecuta el instalador "
            "(3.12 a 3.15). Si corresponde a otra versión, renómbralo antes de volver a preparar el proyecto."
        )
    return python


def crear_entorno(raiz, *, reparar=False):
    carpeta = raiz / ".venv"
    if carpeta.exists() or carpeta.is_symlink():
        try:
            return verificar_entorno(raiz)
        except RuntimeError:
            if not reparar:
                raise
        destino = raiz / ".local" / "entornos" / f"venv-{uuid4().hex}"
        destino.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        carpeta.rename(destino)
        print(f"Entorno anterior conservado en {destino}", flush=True)
    print(f"Creando .venv con Python {sys.version_info.major}.{sys.version_info.minor}...", flush=True)
    venv.EnvBuilder(with_pip=True).create(carpeta)
    return verificar_entorno(raiz)


def ejecutar(argumentos, raiz, *, entorno=None):
    subprocess.run([str(argumento) for argumento in argumentos], cwd=raiz, env=entorno, check=True)


def instalar_extensiones(raiz):
    """Usa la CLI oficial sin interpretar rutas con espacios como comandos de shell."""
    codigo = shutil.which("code")
    if not codigo:
        print("Extensiones: abre VS Code y usa Extensions: Show Recommended Extensions para instalarlas.")
        return
    argumentos = [codigo]
    entorno = dict(os.environ)
    if Path(codigo).suffix.lower() in {".cmd", ".bat"}:
        instalacion = Path(codigo).parent.parent
        ejecutable = instalacion / "Code.exe"
        cli = instalacion / "resources" / "app" / "out" / "cli.js"
        if not ejecutable.is_file() or not cli.is_file():
            print("Extensiones: instálalas desde Extensions: Show Recommended Extensions en VS Code.")
            return
        argumentos = [str(ejecutable), str(cli)]
        entorno["ELECTRON_RUN_AS_NODE"] = "1"
    extensiones = json.loads((raiz / ".vscode" / "extensions.json").read_text(encoding="utf-8"))["recommendations"]
    for extension in extensiones:
        if not re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_.-]+", extension):
            raise RuntimeError("Identificador de extensión no válido en .vscode/extensions.json.")
    try:
        ejecutar(
            [*argumentos, *(dato for extension in extensiones for dato in ("--install-extension", extension))],
            raiz,
            entorno=entorno,
        )
    except (OSError, subprocess.CalledProcessError):
        print("No se pudieron descargar las extensiones. Instálalas desde las recomendaciones de VS Code.")


def preparar(raiz, *, inicio_rapido=False, mysql=False, extensiones=False, solo_ejecucion=False, reparar_entorno=False):
    python = crear_entorno(raiz, reparar=reparar_entorno)
    privados = raiz / ".local"
    privados.mkdir(exist_ok=True, mode=0o700)
    print("Instalando paquetes precompilados para GESICOM...", flush=True)
    requisitos = ["-r", raiz / ("requirements.txt" if solo_ejecucion else "requirements-dev.txt")]
    if mysql:
        requisitos.extend(["-r", raiz / "requirements-mysql.txt"])
    ejecutar(
        [
            python,
            "-m",
            "pip",
            "--require-virtualenv",
            "--cache-dir",
            privados / "cache" / "pip",
            "install",
            "--disable-pip-version-check",
            "--only-binary=:all:",
            *requisitos,
        ],
        raiz,
    )
    ejecutar([python, "-m", "pip", "--require-virtualenv", "--cache-dir", privados / "cache" / "pip", "check"], raiz)
    if inicio_rapido:
        crear_configuracion_local(raiz)
        entorno = entorno_local(raiz)
        for comando in [
            ["createcachetable"],
            ["migrate", "--noinput"],
            ["collectstatic", "--noinput"],
            ["crear_usuarios_revision", "--archivo", ".local/desarrollo/credenciales_revision.json"],
            ["check"],
        ]:
            ejecutar([python, raiz / "manage.py", *comando], raiz, entorno=entorno)
        print("Perfil SQLite listo. Cuentas: .local/desarrollo/credenciales_revision.json")
        print("La configuración .env y los datos de otros perfiles se conservan.")
    if extensiones:
        instalar_extensiones(raiz)
    if solo_ejecucion:
        print(".venv preparado con las bibliotecas de ejecución.")
    else:
        print(".venv preparado. En VS Code: Python: Select Interpreter, elige .venv y después F5.")
    print("Selecciona GESICOM: aplicación y correos locales; los PIN aparecen en la consola del trabajador.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inicio-rapido", action="store_true", help="Prepara el perfil privado SQLite, incluso si existe .env."
    )
    parser.add_argument(
        "--mysql", action="store_true", help="Añade el cliente MySQL opcional si hay rueda para tu sistema."
    )
    parser.add_argument(
        "--extensiones",
        action="store_true",
        help="Instala las extensiones recomendadas si está disponible la CLI de VS Code.",
    )
    parser.add_argument(
        "--ejecutar", action="store_true", help="Prepara el perfil local e inicia la aplicación y el trabajador."
    )
    parser.add_argument("--solo-ejecucion", action="store_true", help="Instala solo las dependencias de la aplicación.")
    parser.add_argument(
        "--reparar-entorno", action="store_true", help="Conserva y reemplaza un .venv incompatible o incompleto."
    )
    parser.add_argument("--puerto", type=int, default=8000, help="Puerto del servidor local.")
    args = parser.parse_args(argv)
    if not 1024 <= args.puerto <= 65535:
        parser.error("El puerto debe estar entre 1024 y 65535.")
    if tuple(sys.version_info[:2]) not in PYTHON_SOPORTADOS:
        print(
            "Usa Python 3.12 a 3.15 de 64 bits; por ejemplo: py -3.15 scripts/configurar_entorno.py en Windows.",
            file=sys.stderr,
        )
        return 2
    try:
        preparar(
            ROOT,
            inicio_rapido=args.inicio_rapido or args.ejecutar,
            mysql=args.mysql,
            extensiones=args.extensiones,
            solo_ejecucion=args.solo_ejecucion,
            reparar_entorno=args.reparar_entorno,
        )
        if args.ejecutar:
            ejecutar(
                [python_del_entorno(ROOT), ROOT / "scripts" / "ejecutar_local.py", "--puerto", str(args.puerto)], ROOT
            )
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"No se pudo completar la preparación: {error}", file=sys.stderr)
        print("Consulta docs/VSCODE.md. El inicio local no requiere Docker, MySQL ni compiladores.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
