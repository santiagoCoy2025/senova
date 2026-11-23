# Ejecutar GESICOM en Visual Studio Code

El inicio local funciona en **Windows, macOS y Linux** con Python **3.12 a 3.15 de 64 bits**. No requiere WSL, Docker, MySQL, Redis, GCC, `pkg-config` ni bibliotecas de desarrollo de Linux. Usa SQLite y un servidor Waitress compatible con los tres sistemas. MySQL y Redis siguen disponibles en el perfil de despliegue.

En macOS, la instalación desde ruedas de este perfil requiere **Apple Silicon (ARM64)**: `cryptography` 50 no publica ruedas para Intel. En Mac Intel utiliza el perfil Docker o una instalación explícita de la biblioteca actual compilada para tu equipo; el inicio sencillo no intenta compilarla ni instala una versión anterior vulnerable.

Abre en VS Code la carpeta que contiene `manage.py`, `scripts/` y `requirements.txt`. Las rutas con espacios, incluidas las carpetas de OneDrive, se pasan como argumentos independientes.

## Instalar y ejecutar en Windows

En PowerShell, desde la carpeta del proyecto:

```powershell
python iniciar.py
```

También puedes hacer doble clic en **INICIAR_WINDOWS.cmd** desde la carpeta extraída. El lanzador entra en la carpeta correcta aunque tenga espacios y busca `python`; si no existe ese comando, intenta `py`.

Si `python` no corresponde a la versión deseada, usa `py -3.15` en su lugar. El comando crea `.venv`, instala únicamente las bibliotecas de ejecución desde ruedas, prepara las cuentas y abre el servidor en http://127.0.0.1:8000/. Con **Ctrl+C** se detienen la web y el trabajador de notificaciones.

Para volver a ejecutar después de la instalación:

```powershell
.\.venv\Scripts\python.exe scripts/ejecutar_local.py
```

No hace falta activar `Activate.ps1` ni modificar la política de ejecución de PowerShell. Si el puerto está ocupado, añade `--puerto 8001` al segundo comando y abre esa dirección.

## Instalar y ejecutar en macOS o Linux

```bash
python3.15 iniciar.py
```

Después de la instalación:

```bash
.venv/bin/python scripts/ejecutar_local.py
```

El instalador reutiliza un entorno válido de la misma versión de Python con la que lo ejecutas. Para otra versión compatible ajusta el comando. El inicio sencillo comprueba `.venv`. Si está incompleto o es incompatible, mueve la copia anterior a `.local/entornos/venv-<identificador>/` antes de crear el nuevo entorno. No elimina esa copia ni modifica `.env`, SQLite o los archivos de usuarios. Si ya es válido, lo reutiliza. El instalador avanzado conserva su modo estricto; para autorizar el mismo respaldo usa `--reparar-entorno`.

Solo se admiten paquetes precompilados en la instalación local (`--only-binary=:all:`). Si no existe una rueda para tu arquitectura o versión, la preparación se detiene antes de intentar compilar y muestra el paquete que falta. Usa una distribución estándar de Python de 64 bits con `venv` y `pip` disponibles.

## Datos y credenciales del perfil local

`--inicio-rapido` prepara siempre un perfil independiente, incluso si ya ejecutaste `configurar_local.py` y tu `.env` tiene MySQL configurado. Guarda sus archivos en:

```text
.local/desarrollo/
  perfil.env                    clave local privada y configuración
  db.sqlite3                    datos de desarrollo
  credenciales_revision.json    usuario y contraseña de cada rol
  media/                        archivos subidos en desarrollo
  staticfiles/                  recursos recopilados
  logs/                         diagnóstico local
```

Abre `credenciales_revision.json` en tu equipo para consultar las seis cuentas. Las contraseñas son aleatorias y no se publican. La preparación puede repetirse tras una instalación parcial: conserva el secreto, las cuentas y contraseñas existentes, y aplica las migraciones pendientes.

El perfil `SENNOVA.local_settings` fuerza SQLite, depuración local y correo en consola. Ignora las conexiones SMTP, MySQL y Redis heredadas. **No altera `.env`, los datos de MySQL ni los archivos de otros perfiles**. La caché se guarda en la misma base SQLite y permite compartir las sesiones y la señal del trabajador entre procesos. Los PIN y avisos de prueba aparecen en la consola del trabajador; no se envían a Internet.

SQLite permite revisar y desarrollar la aplicación en un equipo. Para despliegues con muchos usuarios se conserva MySQL 8.4, Redis y las cuentas SQL con permisos separados.

## Ejecutar con F5

1. Ejecuta `python scripts/configurar_entorno.py --inicio-rapido --extensiones` para preparar las herramientas y extensiones de desarrollo.
2. Abre **Python: Select Interpreter** con `Ctrl+Shift+P` y elige `.venv\Scripts\python.exe` en Windows o `.venv/bin/python` en macOS/Linux.
3. En **Ejecutar y depurar**, selecciona **GESICOM: aplicación y correos locales** y pulsa **F5**.
4. Abre http://127.0.0.1:8000/ e ingresa con las cuentas del archivo privado.

El perfil conjunto prepara primero `.venv` mediante una sola tarea y después inicia Waitress con Django y el trabajador; **detener** finaliza ambos. Los perfiles individuales permiten depurar cada proceso por separado. Todas las configuraciones locales apuntan al perfil aislado y al intérprete de `.venv`.

Puedes añadir `--extensiones` al inicio sencillo para instalar las recomendaciones sin las herramientas de análisis. `--extensiones` usa la CLI oficial `code` si está disponible. Si no está en `PATH` o la descarga falla, abre **Extensions: Show Recommended Extensions** e instala las recomendaciones: Python, Pylance, Python Debugger, Ruff y Django. No se instalan extensiones desde fuentes externas al catálogo configurado en VS Code.

## Tareas y comprobaciones

**Terminal > Ejecutar tarea** ofrece preparación de `.venv`, comprobación de Django, migraciones locales, recopilación de estáticos, pruebas con SQLite y Ruff. Las pruebas usan una base independiente y no modifican la base de desarrollo. Las pruebas exclusivas del cliente MySQL requieren su perfil opcional; la integración continua las ejecuta con MySQL y Python 3.12 y 3.15.

Windows:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe manage.py check --settings=SENNOVA.local_settings
python scripts/verificar_inicio_local.py
```

La última comprobación exige una instalación portátil limpia sin `mysqlclient` ni Gunicorn; verifica el servidor HTTP, la base local y el trabajador con caché compartida. GitHub Actions ejecuta esta instalación en Windows, macOS y Linux, en una carpeta con espacios.

## Usar MySQL o Docker de forma opcional

El perfil de despliegue se describe en el [inicio con Docker](../README.md#inicio-local-con-docker). Requiere instalar y arrancar Docker Desktop o Docker Engine antes de ejecutar sus comandos. Si PowerShell indica **«docker no se reconoce»**, utiliza el inicio local de esta guía o instala Docker por separado si necesitas ese perfil.

Las dependencias están separadas:

| Archivo | Uso |
| --- | --- |
| `requirements.txt` | Django y ejecución portátil con Waitress, sin cliente SQL nativo |
| `requirements-dev.txt` | Perfil portátil y herramientas de pruebas, depuración y análisis |
| `requirements-quality.txt` | Formateador opcional de plantillas; PyYAML puede requerir compilación en Python reciente |
| `requirements-mysql.txt` | Perfil opcional con `mysqlclient` |
| `requirements-production.txt` | MySQL y Gunicorn para el contenedor de despliegue |

Con un perfil local ya preparado, `python manage.py runserver` usa `SENNOVA.local_settings` cuando no has indicado una configuración. Si falta el perfil, explica cómo ejecutar `python iniciar.py`. Para trabajar con MySQL conserva una selección explícita mediante `--settings=SENNOVA.settings` o `DJANGO_SETTINGS_MODULE`. Los comandos de migración, trabajador y despliegue mantienen su configuración anterior.

Para conectar directamente a un MySQL existente puedes ejecutar `python scripts/configurar_entorno.py --mysql`; el instalador solo acepta ruedas, disponibles para plataformas compatibles. Si no hay rueda, utiliza el contenedor que incorpora las bibliotecas nativas. Para compilar el perfil MySQL manualmente en Linux/macOS sí necesitas sus cabeceras y herramientas; no forman parte del inicio local.

La configuración MySQL original utiliza `SENNOVA.settings`, y las migraciones y pruebas requieren las cuentas dedicadas de [database/README.md](../database/README.md). Las tareas y F5 predeterminados continúan en el perfil local aislado.

## Resolver errores

| Mensaje o síntoma | Solución |
| --- | --- |
| `docker no se reconoce` | Ejecuta `python iniciar.py`; Docker es opcional. |
| `.local ya existe` al copiar instrucciones antiguas | No necesitas crearla a mano; la preparación local reutiliza sus carpetas. |
| `pkg-config`, GCC o cabeceras de MySQL | Actualiza el código y usa los requisitos portátiles. No instales `requirements-production.txt` para el inicio local. |
| `No module named django`, `waitress`, `PIL` o `cryptography` | Repite la preparación y ejecuta el Python de `.venv`. |
| `Import ... could not be resolved` en Pylance | Selecciona `.venv` y ejecuta **Developer: Reload Window** si recuerda otro intérprete. |
| PowerShell bloquea `Activate.ps1` | Usa `.\.venv\Scripts\python.exe` directamente. |
| `.venv` incompleto o de otro Python | Ejecuta `python iniciar.py` para conservarla y preparar un entorno compatible. |
| No existe el perfil local | Ejecuta la preparación con `--inicio-rapido`; crear solo el `.env` de MySQL no prepara este perfil. |
| Puerto 8000 ocupado | Detén la otra instancia o usa `scripts/ejecutar_local.py --puerto 8001`. |
| No aparece el PIN | Mantén activo el trabajador y consulta su terminal. |

Comparte únicamente las líneas necesarias del error, sin credenciales ni el contenido de `.env` o `perfil.env`.

## Comandos del inicio sencillo

```powershell
# Preparar y arrancar web y notificaciones
python iniciar.py

# Preparar sin arrancar, por ejemplo antes de F5
python iniciar.py --preparar

# Elegir otro puerto
python iniciar.py --puerto 8001
```

El puerto se comprueba antes de instalar o reparar el entorno. El lanzador mantiene el error visible si falla; no confirma que el servidor esté listo cuando termina con un error. Las herramientas de depuración, Ruff y auditoría siguen disponibles en `requirements-dev.txt`, pero no se necesitan para ejecutar la página.

## Si VS Code solicita WSL

El proyecto configura PowerShell y Codex en modo Windows mediante estas preferencias de `.vscode/settings.json`:

```json
{
  "terminal.integrated.defaultProfile.windows": "PowerShell",
  "chatgpt.runCodexInWindowsSubsystemForLinux": false
}
```

Para aplicarlas en tu equipo:

1. Actualiza la extensión oficial Codex de OpenAI desde Extensiones de VS Code.
2. Si la esquina inferior izquierda muestra una conexión WSL, ejecuta **Remote: Close Remote Connection** y abre la carpeta del proyecto desde su ruta de Windows, por ejemplo `C:\Users\...`.
3. En Ajustes busca **Run Codex in Windows Subsystem For Linux** y comprueba que esté desactivado.
4. Ejecuta **Developer: Reload Window**, abre una terminal PowerShell y ejecuta `python iniciar.py`.

La preferencia de Codex está documentada en la [referencia oficial del editor](https://developers.openai.com/codex/ide/settings/). Codex también dispone de un [entorno aislado nativo de Windows](https://developers.openai.com/codex/windows/); esta configuración conserva sus límites de seguridad. No hace falta cambiar el aislamiento a acceso total para iniciar GESICOM.

Las preferencias del repositorio se aplican al abrir esta carpeta; no modifican directamente las preferencias personales ni la instalación de VS Code de otro equipo.
