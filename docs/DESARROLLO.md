# Guía de archivos y desarrollo

La configuración activa está en `SENNOVA/`. Cada aplicación conserva sus modelos, migraciones, rutas, plantillas y pruebas. Los nombres históricos de las aplicaciones mantienen la identidad de las tablas y permisos.

```text
SENNOVA/
  settings.py, urls.py, wsgi.py   configuración y composición del proyecto
  tests/                        comprobaciones del proyecto
  test_settings.py              configuración exclusiva de pruebas
  migration_settings.py         cuenta exclusiva de migraciones
  database_security.py          diagnóstico de la conexión, solo lectura
ADMIN/, Gesicom/, cuentas/, instructor/, notificaciones/
  urls.py                       rutas de la aplicación
  models.py, migrations/        persistencia e historial del esquema
  forms.py                      validación de entradas
  views.py                      peticiones y respuestas
  selectors.py, services.py     consultas y operaciones, cuando corresponda
  templates/                    plantillas propias
  tests/test_*.py                pruebas por funcionalidad
Gesicom/static/
  css/, js/                     recursos compartidos y por funcionalidad
  fonts/, img/brand/, vendor/    fuentes, identidad y bibliotecas con sus licencias
Gesicom/templates/ui/           componentes compartidos, incluida la paginación
templates/                      errores HTTP y personalización de Django admin
scripts/                        configuración, actualización, respaldo y medición
database/
  consultas/                    diagnóstico SQL de solo lectura
  documentacion/                modelo y relaciones
  seguridad/                    perfiles de cuentas y guía de permisos de MySQL
docs/                           arquitectura, desarrollo, operación y verificación
```

## Dónde hacer cada cambio

| Cambio | Ubicación |
| --- | --- |
| Evidencias, páginas, perfil y reportes | `Gesicom/urls.py` y módulos de esa aplicación |
| Inicio de sesión, registro y salida | `instructor/urls.py` y sus vistas |
| Recuperación de contraseña y sesiones | `cuentas/urls.py` y sus módulos |
| Formularios de recuperación HTML/JSON | `cuentas/presentacion.py`, `cuentas/views.py` y parciales de `cuentas/templates/cuentas/` |
| Interacción y estados de recuperación | `Gesicom/static/js/recovery.js` y `css/recovery.css` |
| Comunidad, permisos y actividad | `ADMIN/urls.py` y sus módulos |
| Búsqueda global y accesos rápidos | `Gesicom/busqueda.py`, `BusquedaGlobalForm`, `static/js/search.js` y el diálogo en `base.html` |
| Consulta de usuarios y CSV por lotes | `ADMIN/directorio.py`, con `FiltrosUsuariosForm` y operaciones en `ADMIN/services.py` |
| Plazos, novedades, bandeja y calendario | `notificaciones/urls.py` y sus módulos |
| Validación de filtros | Formularios de la aplicación, compartidos con la descarga |
| Auditoría administrativa | `ADMIN/auditoria.py`: consulta y presentación sin mutaciones |
| Correcciones y entregas | `Gesicom/services.py`, con formularios y selectores |
| Horarios mensuales e iCalendar | `notificaciones/calendario.py` y `notificaciones/icalendar.py` |
| Lectura interactiva de avisos | `Gesicom/static/js/inbox.js`, con filtros y servicios de `notificaciones/` |
| Hora de Colombia en el pie | `Gesicom/templates/ui/reloj_colombia.html`, `static/js/clock.js` y `static/css/clock.css` dentro de `Gesicom/` |
| Cambios del esquema | `migrations/` de la aplicación propietaria del modelo |

`SENNOVA/urls.py` incluye las rutas de las aplicaciones. La separación conserva direcciones, nombres y vistas existentes; las rutas públicas históricas mantienen su espacio de nombres. `core/` y las plantillas antiguas que extienden las actuales permanecen como accesos de compatibilidad.

## Pruebas

Instala `requirements-dev.txt` en el entorno virtual. Las pruebas de MySQL usan la base independiente preparada como explica [database/README.md](../database/README.md).

```bash
python manage.py test --settings=SENNOVA.test_settings --noinput
python manage.py test cuentas.tests --settings=SENNOVA.test_settings --noinput
python manage.py test ADMIN.tests.test_auditoria --settings=SENNOVA.test_settings --noinput
python manage.py test ADMIN.tests.test_directorio --settings=SENNOVA.test_settings --noinput
python manage.py test notificaciones.tests.test_calendario --settings=SENNOVA.test_settings --noinput
ruff check .
python manage.py makemigrations --check --dry-run
```

Los módulos `test_*.py` viven dentro de `tests/`; los antiguos `tests.py` se distribuyen por funcionalidad. `SENNOVA/test_settings.py` permanece en su ruta porque es configuración y la utiliza CI. Añade las pruebas junto a la función correspondiente, con datos ficticios y comprobaciones de permisos, transacciones y resultados relevantes.

## Herramientas operativas

```bash
python scripts/configurar_local.py
python scripts/actualizar_instalacion.py
sh scripts/backup_mysql.sh
```

La actualización ejecuta `check`, `migrate --noinput --settings=SENNOVA.migration_settings` y `collectstatic --noinput`, y se detiene ante el primer fallo. Requiere las credenciales privadas de migraciones. Resuelve la raíz desde el archivo, por lo que puede invocarse desde otro directorio. `sync_database.py` y `sync.ps1` remiten a esa implementación; importar el módulo no aplica migraciones.

El esquema se mantiene con migraciones de Django. La [documentación de MySQL](../database/README.md) describe diagnóstico y copias. Los resultados de pruebas, datos locales, credenciales, respaldos y archivos de usuarios se guardan fuera del código versionado.
