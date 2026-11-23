import os
import sys
from pathlib import Path


def configuracion_inicial(argumentos, raiz):
    from SENNOVA.desarrollo import archivo_perfil

    configuracion = os.environ.get("DJANGO_SETTINGS_MODULE")
    explicita = any(arg == "--settings" or arg.startswith("--settings=") for arg in argumentos)
    if not configuracion and not explicita and argumentos[1:2] == ["runserver"]:
        if not archivo_perfil(raiz).is_file():
            raise RuntimeError("Para preparar e iniciar GESICOM local ejecuta: python iniciar.py")
        return "SENNOVA.local_settings"
    return configuracion or "SENNOVA.settings"


def main():
    # Ensure project root (where manage.py lives) is on sys.path so apps
    # (like Gesicom) can be imported reliably when running management commands.
    project_root = Path(__file__).resolve().parent
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

    try:
        os.environ["DJANGO_SETTINGS_MODULE"] = configuracion_inicial(sys.argv, project_root)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 2
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
