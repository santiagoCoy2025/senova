# GESICOM · SENA / SENNOVA

Gestión de evidencias, reportes, novedades y plazos con Django 5.2 LTS, MySQL 8.4 y Redis. Las evidencias pendientes o rechazadas admiten correcciones con historial y control de versiones. La interfaz utiliza Work Sans, el logosímbolo del SENA y una estructura compartida para todos los roles.

## Inicio local con Docker

Clona la rama de trabajo integrada y entra en el proyecto:

```bash
git clone --branch develop https://github.com/santiagoCoy2025/senova.git
cd senova
```

Requiere Docker Compose y Python 3 para generar la configuración privada.

```bash
python scripts/configurar_local.py
docker compose -f compose.yml -f compose.dev.yml up -d database redis mailpit
python scripts/preparar_mysql.py --aplicar --con-pruebas
docker compose -f compose.yml -f compose.dev.yml up --build -d
docker compose exec app python manage.py crear_usuarios_revision
mkdir -p .local
docker compose cp app:/app/.local/credenciales_revision.json .local/credenciales_revision.json
```

- Aplicación: http://127.0.0.1:8000/
- Panel administrativo: http://127.0.0.1:8000/administrador/
- Buzón local de pruebas: http://127.0.0.1:8025/
- MySQL de desarrollo: `127.0.0.1:3307`, base `senova`.

El perfil `compose.dev.yml` captura los mensajes en Mailpit y **no los envía a Internet**. Permite revisar el PIN y los avisos sin una credencial institucional. Las cuentas de revisión y los secretos se generan localmente: no hay contraseñas predeterminadas en el repositorio. El archivo `.local/credenciales_revision.json` contiene una cuenta por cada uno de los seis roles.

Los datos de MySQL, archivos y credenciales de revisión se conservan en volúmenes. El trabajador de notificaciones se inicia junto con la aplicación. En un equipo con una instancia existente, utiliza sus servicios o detén esa instancia antes de abrir los mismos puertos.

## Funcionalidades

- Inicio de sesión por usuario o correo y panel según el rol.
- Registro y edición de perfil con validación de correo y contraseña.
- Recuperación en tres pasos: solicitud, PIN de **6 dígitos**, y nueva contraseña después de verificarlo.
- Recuperación disponible con y sin JavaScript, con progreso por pasos, caducidad visible y conservación del avance verificado.
- Ante una respuesta incierta se ofrece comprobar el siguiente paso; los envíos de recuperación no se repiten automáticamente.
- PIN válido durante 10 minutos, máximo 5 intentos, hash en la base de datos y autorización ligada a la sesión.
- Envío del PIN mediante cola, con cifrado temporal y eliminación del contenido al terminar el envío.
- Invalidación automática del PIN si cambian el correo o la contraseña de la cuenta.
- Confirmación de contraseña actual para modificar usuario, correo o contraseña; aviso de los cambios al correo anterior y al nuevo.
- Centro de seguridad con sesiones por dispositivo, cierre individual o de otras sesiones y caducidad por inactividad.
- Evidencias mediante archivo de hasta 10 MB o enlace; búsqueda, filtros, estados y paginación.
- Archivos protegidos: solo el propietario y los roles revisores pueden consultarlos.
- Reportes con gráficos y descargas CSV que respetan los filtros y neutralizan fórmulas de hojas de cálculo.
- Publicación de novedades por grupo o para todos los usuarios activos.
- Plazos de reportes con aviso inicial, recordatorio y notificación de vencimiento.
- Asociación del reporte con su plazo, identificación de entregas tardías y suspensión de recordatorios cuando ya se entregó.
- Calendario mensual personal en Mis plazos, con estados, filtros y descarga privada `.ics` para importación manual.
- Bandeja personal, lectura de avisos y preferencias de correo.
- Filtros por fechas de Colombia y cambios de lectura individuales o masivos sin recargar la bandeja.
- Reloj con hora y fecha de Colombia en el pie de la aplicación, adaptable a móvil.
- Cola de correo con lotes, bloqueo entre trabajadores y reintentos con espera.
- Administración de usuarios, roles y permisos; edición de datos, estado, roles y contraseña.
- Directorio con CSV de todos los resultados filtrados y conservación de filtros y página al guardar.
- Historial administrativo con búsqueda, fechas de Colombia, detalles y CSV filtrado de todos los resultados.
- Consulta administrativa de permisos mínimos, TLS e integridad de MySQL, sin modificar la base.

## Roles y acceso

| Rol | Evidencias y reportes | Revisar estado | Editar observaciones | Administrar |
| --- | --- | --- | --- | --- |
| Usuario, instructor, investigador | Propios | No | No | No |
| Coordinador, dinamizador | Todos | Sí | No | No |
| Administrador / superusuario | Todos | Sí | Sí | Usuarios, roles, novedades y plazos |

Los paneles de evidencias reutilizan una sola plantilla. El panel administrativo existente conserva su función. Los nombres de las plantillas antiguas se mantienen como alias de compatibilidad y no crean nuevas opciones de navegación.

## Correo real

El remitente elegido es **`santiagoocoy2025@gmail.com`**. La configuración usa **`smtp.gmail.com:587` con STARTTLS**. Para activar el envío:

1. Activa la verificación en dos pasos en la cuenta de Google.
2. Crea una [contraseña de aplicación](https://myaccount.google.com/apppasswords) para GESICOM.
3. Guarda esa contraseña, sin los espacios de presentación, en `EMAIL_HOST_PASSWORD` mediante la configuración privada del entorno. No uses la contraseña normal ni la publiques en Git o en el chat.
4. Mantén `EMAIL_HOST_USER=santiagoocoy2025@gmail.com` y `DEFAULT_FROM_EMAIL=GESICOM <santiagoocoy2025@gmail.com>`.
5. Comprueba configuración y autenticación con los comandos de abajo.

También se admiten otros proveedores mediante estas variables:

- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS` o `EMAIL_USE_SSL`.
- `EMAIL_HOST_USER` y `DEFAULT_FROM_EMAIL`.
- `EMAIL_HOST_PASSWORD` autorizado por el proveedor, o `EMAIL_OAUTH2_ACCESS_TOKEN` válido para SMTP XOAUTH2.

Si eliges OAuth2, el token SMTP debe estar vigente y renovarse mediante el proveedor o un servicio externo. El proveedor del destinatario no requiere configuración adicional. Gmail requiere que la cuenta autenticada coincida con el remitente configurado.

```bash
python manage.py comprobar_correo --solo-configuracion
python manage.py comprobar_correo
```

El segundo comando autentica la conexión sin enviar un mensaje ni mostrar secretos. Si faltan credenciales, el sistema lo indica y no confirma un envío real. Para producción utiliza `compose.yml`, sin el perfil de Mailpit.

El trabajador `procesar_notificaciones` debe estar activo para enviar tanto los PIN como las novedades. El panel administrativo muestra pendientes, errores y señal del trabajador; la cola de seguridad detallada se consulta en el administrador de Django. Los mensajes de seguridad no se desactivan mediante las preferencias de novedades.

Gmail personal impone [límites de envío](https://support.google.com/mail/answer/22839). Al crecer los avisos, comprueba que la cuota cubra a los destinatarios; una cuenta personal no garantiza envíos masivos para más de 1.000 usuarios. La bandeja interna sigue disponible cuando el proveedor demora o rechaza correo.

## Organización

```text
SENNOVA/        configuración única, seguridad, salud y WSGI
Gesicom/        evidencias, perfiles, reportes y componentes visuales
cuentas/        cuentas, recuperación, cola cifrada de seguridad, sesiones y auditoría
instructor/     entrada, registro y salida de autenticación
ADMIN/         centro de operaciones, usuarios y permisos
notificaciones/ novedades, plazos, bandeja y cola de correo
config/         Gunicorn y ejemplo de proxy HTTPS
docker/         arranque del contenedor
database/       esquema lógico, preparación de pruebas y copias
docs/           operación, seguridad y resultados de verificación
scripts/        configuración, respaldo y prueba de carga
```

Cada aplicación mantiene sus rutas en `urls.py` y sus pruebas en `tests/`. `SENNOVA/urls.py` compone el proyecto y `core/` conserva alias a su configuración. La [guía de desarrollo y archivos](docs/DESARROLLO.md) indica dónde realizar cada cambio y cómo ejecutar una funcionalidad por separado. La separación de consultas y operaciones, y las relaciones de MySQL, se describen en [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) y [database/documentacion/modelo.md](database/documentacion/modelo.md). Los nombres históricos de las aplicaciones se mantienen para conservar las migraciones. Se retiraron estilos sin uso, pantallas prototipo, fixtures con cuentas fijas y scripts de limpieza destructiva.

## Desarrollo sin contenedor de aplicación

Requiere Python 3.12, MySQL 8.4, Redis y las bibliotecas de desarrollo del cliente MySQL para instalar `mysqlclient`.

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python scripts/configurar_local.py
python manage.py migrate --settings=SENNOVA.migration_settings
python manage.py collectstatic --noinput
python manage.py runserver
```

Configura `DB_*` y `REDIS_URL` para los servicios existentes. Prepara primero las cuentas dedicadas con `scripts/preparar_mysql.py --aplicar --con-pruebas` si MySQL está en el servicio Docker del proyecto; para otro servidor utiliza el procedimiento de [perfiles de MySQL](database/seguridad/README.md). `.env` se carga automáticamente; las variables del proceso tienen prioridad. SQLite queda disponible con `DB_ENGINE=sqlite` para desarrollo puntual. MySQL es el destino principal y la base utilizada en las verificaciones de capacidad y concurrencia.

## Verificación

```bash
# Preparar una cuenta exclusiva para test_<DB_NAME>, sin permisos en la base real.
python scripts/preparar_mysql.py --aplicar --con-pruebas

docker compose --profile tools run --rm test
docker compose exec app python manage.py comprobar_base_datos --estricto
docker compose exec app python manage.py check
docker compose exec app python manage.py makemigrations --check --dry-run
```

Para analizar el código: `pip install -r requirements-dev.txt` y `ruff check .`. Los resultados y el alcance de las pruebas están en [docs/VERIFICACION.md](docs/VERIFICACION.md). La prueba HTTP reproducible es `python scripts/prueba_carga_http.py`; crea y elimina exclusivamente sus registros temporales.

La cuenta web solo tiene `SELECT`, `INSERT`, `UPDATE` y `DELETE` en su esquema. Las migraciones utilizan `SENNOVA.migration_settings` y una cuenta independiente; las pruebas utilizan otra cuenta, limitada a `test_<DB_NAME>`. Compose mantiene esas credenciales fuera de los servicios web y trabajador. Las conexiones exigen TLS y deshabilitan cargas locales y sentencias encadenadas. Consulta [la preparación, actualización y verificación de los perfiles](database/seguridad/README.md) antes de actualizar una instalación existente.

## Operación y despliegue

Configura HTTPS, un `DJANGO_SECRET_KEY` privado, `DJANGO_DEBUG=False`, los dominios permitidos y el correo real antes de publicar. Gunicorn usa por defecto 4 procesos y 2 hilos; Redis comparte sesiones y límites de acceso entre procesos. WhiteNoise sirve los recursos estáticos. Los archivos privados se entregan mediante Django y no deben exponerse con un alias público del servidor web.

Lee [docs/OPERACION.md](docs/OPERACION.md), [docs/SEGURIDAD.md](docs/SEGURIDAD.md) y [database/README.md](database/README.md).

## Ramas y revisiones

El trabajo continúa en el fork `santiagoCoy2025/senova`. Cada bloque usa una rama nueva y un pull request a `develop`. Después de pasar las comprobaciones e integrar el PR, se elimina la rama de trabajo; `develop` y `main` se conservan. Las instrucciones están en [AGENTS.md](AGENTS.md).

GitHub Actions ejecuta las comprobaciones con Python 3.12, MySQL y Redis: código, migraciones, pruebas, configuración de producción, estáticos y auditoría de dependencias. Las acciones externas se fijan por SHA. Los valores de autenticación que aparecen en el workflow pertenecen exclusivamente a servicios desechables del trabajo de CI.

La referencia visual es el [Manual de Identidad Visual SENA 2024](https://www.sena.edu.co/es-co/Documents/MANUAL_IDENTIDAD_VISUAL_SENA_2024.pdf). Work Sans se distribuye localmente con su licencia SIL Open Font License y el logo conserva los trazados y el color del recurso oficial.
