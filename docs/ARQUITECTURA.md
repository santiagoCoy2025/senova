# Organización del proyecto

| Carpeta | Responsabilidad |
| --- | --- |
| `SENNOVA/` | Configuración activa, rutas y middleware HTTP |
| `config/` | Configuración de Gunicorn |
| `Gesicom/` | Evidencias, reportes, páginas y recursos visuales compartidos |
| `Gesicom/forms.py` | Validaciones compartidas de creación y corrección, con compatibilidad para el enlace histórico |
| `Gesicom/services.py` | Transacciones de evidencia, control de versiones, historial y ciclo de sustitución de adjuntos |
| `Gesicom/solicitudes.py` | Firma y comprobación de identificadores de formulario vinculados a la cuenta |
| `Gesicom/adjuntos.py` | Formatos admitidos, comprobaciones de contenido y lectura limitada de texto |
| `Gesicom/archivos.py` | Acceso autorizado a adjuntos y metadatos de disponibilidad |
| `Gesicom/interfaz.py` | Renderizado completo o del contenido del panel con las mismas vistas y permisos |
| `Gesicom/templates/ui/paginacion.html` | Paginación común para evidencias, administración y notificaciones |
| `Gesicom/templates/ui/reloj_colombia.html` | Reloj compartido en el pie de las páginas autenticadas, con referencia inicial del servidor |
| `ADMIN/forms.py` | Validación del directorio contra el catálogo de roles mostrado |
| `Gesicom/filtros.py` | Validación y normalización de filtros compartidos, con errores visibles y descarga cerrada ante parámetros inválidos |
| `Gesicom/reportes.py` | Series históricas, resúmenes autorizados y filas exportables |
| `Gesicom/exportaciones.py` | Respuesta CSV común con Unicode, neutralización de fórmulas y transmisión del documento |
| `Gesicom/selectors.py` | Consultas reutilizadas por vistas, reportes y búsqueda; visibilidad por rol |
| `Gesicom/busqueda.py` | Búsqueda autenticada, limitada por cuenta y con resultados acotados |
| `ADMIN/` | Administración de la comunidad |
| `ADMIN/selectors.py` | Agregaciones y consultas del centro de operaciones |
| `ADMIN/permisos.py` | Catálogo de permisos, protección de grupos, revisión y transacciones compartidas con Django admin |
| `ADMIN/admin.py` | Formularios nativos de grupo con confirmación, revisión y conservación de los roles del sistema |
| `ADMIN/services.py` | Cambios de estado y roles, protección de cuentas y auditoría |
| `ADMIN/auditoria.py` | Consultas filtradas, etiquetas y filas CSV del historial administrativo |
| `cuentas/` | Formularios comunes, recuperación, correo de seguridad y sesiones |
| `instructor/` | Entrada, registro y salida de la aplicación; se conservan las rutas existentes |
| `notificaciones/` | Novedades, plazos, preferencias, bandeja y cola de entrega |
| `notificaciones/resumen.py` | Conteo y cuatro avisos recientes compartidos durante una petición, sin caché entre cuentas |
| `notificaciones/calendario.py` | Límites mensuales de Colombia y distribución acotada de plazos en 42 días |
| `notificaciones/icalendar.py` | Descarga privada iCalendar, escape de texto y plegado UTF-8 sin dependencias adicionales |
| `database/` | Documentación del esquema, diagnóstico SQL y preparación de la base de pruebas |
| `scripts/` | Operación, copias de seguridad y medición de carga |
| `docs/` | Operación, seguridad, arquitectura y verificaciones |

Cada aplicación mantiene sus propias rutas en `urls.py`. `SENNOVA/urls.py` compone estos archivos y conserva los nombres públicos anteriores, junto con los accesos de compatibilidad de `core/`. Las pruebas se agrupan en seis carpetas `tests/`, por aplicación y por funcionalidad; la configuración `SENNOVA.test_settings` conserva su ruta. La [guía de desarrollo](DESARROLLO.md) incluye el mapa de archivos y los comandos por módulo.

Las migraciones permanecen dentro de sus aplicaciones, como espera Django. Los módulos de compatibilidad y las plantillas históricas que remiten a las vistas actuales no generan menús adicionales. Solo se retiran funciones sin llamadas ni rutas activas.

El centro de operaciones agrega los registros en MySQL y limita las listas recientes; los directorios y las evidencias del detalle de usuario tienen paginación. La búsqueda reutiliza la visibilidad de evidencias y solo consulta la bandeja del usuario conectado. Los resultados no se almacenan en una caché compartida: la autorización se aplica en cada petición.

Los filtros usan las mismas vistas GET con o sin JavaScript. La mejora interactiva sustituye únicamente los resultados, mantiene los parámetros en la URL y permite volver con el navegador. Los cambios de cuentas siguen siendo formularios POST con CSRF, confirmación de identidad y validación del servidor. Las acciones sensibles no se ejecutan desde la búsqueda.

Los recursos se sirven desde el proyecto: Work Sans, el emblema SENA y Chart.js. `search.js` gestiona la búsqueda, `workspace.js` las acciones administrativas y `admin-dashboard.js` el centro de operaciones; los estilos compartidos de estas interacciones permanecen en `operations.css`.

`Gesicom/admin.py` utiliza las mismas reglas de versiones y registro de movimientos. El formulario de corrección reutiliza `formulario.html`; no añade un segundo panel de evidencias. Los estilos de ese flujo están en `evidencias.css`. La tabla de movimientos es de solo lectura en la administración.

`reports.js` destruye las instancias anteriores de Chart.js al actualizar resultados y reconstruye cuatro gráficos con el estado autorizado del servidor. Las tablas se generan en HTML y se usan sin JavaScript y al imprimir. No se mantienen consultas trimestrales distintas para pantalla y CSV.

El alta de evidencias utiliza `SolicitudEnvio` como recibo interno, sin panel ni permisos adicionales. Su UUID único y el bloqueo transaccional de MySQL permiten recuperar el primer registro aceptado cuando llegan reintentos del mismo formulario. El recibo, la evidencia y el movimiento se confirman juntos; un fallo retira también el archivo nuevo que haya quedado sin referencia. Al eliminar la evidencia se conserva el recibo sin destino para que un reintento no la vuelva a crear.

Los archivos compartidos se buscan por nombre indexado y se retiran después del commit solo si ninguna evidencia los referencia. La consulta de disponibilidad no modifica registros históricos. Las vistas de texto leen como máximo 64 KB del origen, más un byte para detectar truncamiento; la descarga conserva el archivo completo.

`notifications.js` concentra la actualización de la campana en todos los paneles autenticados; `sena.js` conserva las interacciones generales y la caducidad visible del PIN. La lista inicial se genera en `notificaciones/avisos_recientes.html`, con POST y CSRF, para funcionar también sin JavaScript. Las actualizaciones utilizan el mismo resumen autorizado y crean los elementos con `textContent`; no incorporan HTML de los títulos. La bandeja y el procesador de contexto comparten el conteo únicamente dentro de la misma petición.

`navigation.js` gestiona los filtros, la paginación, el historial y las ediciones pendientes de los paneles interactivos. `search.js` y `workspace.js` no duplican ese controlador. Las solicitudes GET con `X-Workspace-Fragment: 1` usan `ui/base_fragmento.html` y omiten la cabecera y sus consultas de avisos. Las mismas vistas generan el documento completo sin esa cabecera HTTP. `Vary` identifica ambas representaciones y la respuesta privada conserva `no-store`.

El estado del historial contiene solo un identificador del documento y un índice, sin datos de formularios. Una navegación cancelada o fallida vuelve a la entrada aplicada sin borrar Adelante. Las nuevas ediciones cancelan las actualizaciones en curso; los eventos de cambio generados al retirar un campo enfocado no se confunden con otra edición del usuario. Los fragmentos se comprueban antes de sustituir regiones y cada consulta tiene un tiempo máximo de espera.

La lista, el calendario y la descarga de **Mis plazos** comparten `FiltrosAgendaForm` y `agenda_filtrada`: validan búsqueda, proyecto, estado, identificador y mes antes de consultar. La pertenencia actual a los grupos y las entregas de la cuenta se resuelven con subconsultas `Exists`, sin una consulta por evento. La cuadrícula admite hasta 500 plazos por mes y avisa si hay más; la lista paginada y la descarga conservan todos los resultados autorizados. El calendario reutiliza el panel y el controlador de navegación existentes, sin tablas ni rutas de administración duplicadas.

`FiltrosBandejaForm` valida búsqueda, tipo, lectura, identificador y fechas antes de consultar o marcar resultados. `inbox.js` envía los formularios de lectura con CSRF y solicita una actualización al controlador de navegación compartido. `workspace:refresh` conserva la consulta aplicada y espera si hay una búsqueda o actualización en curso. `notifications:changed` solicita el contador vigente mediante el controlador existente de la campana. Las acciones nativas conservan su redirección cuando no se solicita el protocolo JSON.

`clock.js` y `clock.css` presentan un único reloj en el pie del documento completo. Los fragmentos no lo reconstruyen. El cliente reutiliza dos formateadores `Intl.DateTimeFormat` en `America/Bogota`, actualiza los segundos y pausa el temporizador al ocultar la página. El componente obtiene una sola referencia temporal del servidor para su estado inicial; el reloj no consulta la base de datos ni un servicio de hora.
