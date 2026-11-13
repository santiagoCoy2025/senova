# Operación

## Recuperación de acceso

Los tres pasos funcionan también sin JavaScript. Los errores nativos conservan el correo, pero no reflejan el PIN ni las contraseñas. Una verificación vigente permite continuar al último paso al volver a la página del PIN; la pantalla final identifica la cuenta autorizada. Solicitar otro PIN invalida el anterior, como en el flujo original.

Con JavaScript hay progreso de pasos, tiempo restante y pegado de un PIN con espacios o guiones. Pegar no envía el formulario. Una petición sin confirmación termina la espera visual a los quince segundos y ofrece **Comprobar siguiente paso**; en el último paso ofrece comprobar el inicio de sesión con la nueva contraseña. No pulses de nuevo suponiendo que una operación falló: el servidor puede haberla terminado antes del corte de conexión. Si la sesión no se conserva, solicita un PIN nuevo. Reconectar o terminar un intervalo de espera no envía datos automáticamente.

Las rutas `/api/olvide_password/`, `/api/verificar_pin/` y `/api/restablecer_password/` conservan JSON para los clientes anteriores. Los formularios nativos solicitan HTML mediante la cabecera de navegación. Los errores de límite o indisponibilidad ofrecen volver al paso correspondiente y no muestran detalles internos. Los mensajes de correo siguen procesándose mediante la cola existente.

Esta actualización incluye `cuentas.0008_indices_recuperacion`: respalda primero y aplica las migraciones con `SENNOVA.migration_settings`, usando la cuenta de migraciones. Retira dos índices redundantes y añade el de usuario/uso/fecha; conserva hashes, solicitudes y relaciones. En bases grandes planifica la creación de índices según la ventana operativa de la instalación. Recopila estáticos y reinicia la aplicación web para cargar `recovery.js` y `recovery.css`. El trabajador mantiene su configuración y cola actuales.

## Notificaciones

El alta de una novedad o plazo crea avisos en lotes y prepara la cola de correo. La petición web no espera el envío de mensajes a todos los destinatarios.

```bash
python manage.py procesar_notificaciones --continuo --intervalo 30 --lote 50
```

El trabajador genera recordatorios y vencimientos, omite usuarios que ya entregaron el reporte y reclama mensajes con bloqueos de MySQL. Dos trabajadores no toman el mismo lote activo. Los errores de envío se reintentan con espera creciente hasta cinco veces. Después pueden reactivarse desde la página administrativa de Novedades.

El estado visible del procesador se guarda en Redis. La bandeja funciona aunque SMTP esté temporalmente indisponible. Las preferencias se vuelven a comprobar justo antes de enviar. El mismo trabajador procesa primero la cola de seguridad: PIN y avisos de cambios de credenciales. Mientras hay lotes listos, continúa sin esperar el intervalo de reposo.

Los PIN no se envían dentro de la petición web. La respuesta de recuperación es genérica incluso si SMTP falla. La cola de seguridad reintenta tres veces con espera creciente, respeta la caducidad de 10 minutos y borra el contenido cifrado al enviar, cancelar o agotar los intentos. Un PIN caducado necesita una solicitud nueva; los errores ordinarios de novedades siguen el procedimiento de reactivación anterior.

La cola ofrece entrega al menos una vez: un corte justo después de la aceptación del proveedor y antes de registrar el resultado puede producir una repetición. Los avisos internos por novedad/fase de plazo sí se deduplican con restricciones de la base de datos.

## Plazos y entregas

Las fechas se muestran en `America/Bogota`. El usuario puede asociar una evidencia a un plazo de su grupo y proyecto. Se conserva la fecha límite aplicable al registro y se identifica una entrega tardía. Entregar el reporte detiene los avisos pendientes de ese plazo; la aprobación se gestiona por separado.

Cambiar un plazo (fecha, indicaciones, destinatarios o estado) incrementa su revisión y su versión de avisos. Guardar sin cambios no reenvía avisos. Las pestañas con una revisión anterior deben recargar antes de guardar. Para una entrega distinta, crea otro plazo.

## Correo de producción

El remitente es `santiagoocoy2025@gmail.com` por `smtp.gmail.com:587`, con STARTTLS y una contraseña de aplicación de Google. Se requiere verificación en dos pasos. El perfil local de Mailpit captura correos; no valida la autenticación de Gmail ni envía mensajes reales. Para producción, usa `compose.yml` sin el perfil de desarrollo y añade la credencial privada.

Si se utiliza OAuth2, la renovación del token corresponde al servicio de identidad del despliegue. Comprueba la conexión con `python manage.py comprobar_correo`; no imprime secretos ni envía mensajes.

Las cuentas personales de Gmail tienen cuotas de envío. Dimensiona el volumen de avisos antes de usarlo con todos los usuarios; la cola no aumenta los límites del proveedor. Las direcciones `example.invalid` de las cuentas de revisión solo sirven con la captura local.

## Sesiones y cambios de cuenta

`/mi-cuenta/seguridad/` muestra las sesiones del usuario y permite cerrarlas mediante POST, CSRF y contraseña actual. La eliminación alcanza la caché y MySQL. El inicio de sesión registra la sesión antes de la primera navegación. `SESSION_IDLE_TIMEOUT` controla la caducidad por inactividad, con 1.800 segundos por defecto; la actividad visible se actualiza como máximo una vez por minuto para limitar escrituras.

Al cambiar la contraseña desde el perfil se conserva la sesión actual y se cierran las demás. Una recuperación cierra todas las sesiones autenticadas y solicita ingresar de nuevo. Los cambios sensibles invalidan las solicitudes de recuperación y generan avisos al correo anterior y al actual.

Ejecuta `python manage.py clearsessions` periódicamente para retirar sesiones caducadas de MySQL; sus registros asociados se eliminan en cascada.

La primera instalación de esta política exige iniciar sesión de nuevo: las sesiones anteriores que todavía no estaban registradas no se aceptan, aunque quedaran en caché. Esto permite que el cierre de otras sesiones abarque todos los accesos admitidos por la nueva versión.

Las consultas automáticas de la campana no prolongan la sesión. Cuando el servidor responde que el acceso terminó, la interfaz vuelve a la pantalla de ingreso.

## Actualizar esta versión

Instala las dependencias, ejecuta `python manage.py migrate --noinput --settings=SENNOVA.migration_settings` y `python manage.py collectstatic --noinput`, y reinicia aplicación y trabajador. Antes de instalar esta separación de cuentas, sigue la [guía de permisos de MySQL](../database/seguridad/README.md): respalda, genera las credenciales que falten, verifica TLS en los procesos y prepara los perfiles dedicados. No se eliminan cuentas ni evidencias.

## Capacidad

`WEB_WORKERS` y `WEB_THREADS` acotan la concurrencia y las conexiones. Los listados se paginan y las estadísticas se agrupan en SQL. El número de cuentas almacenadas no se convierte en el número de procesos o conexiones abiertos.

La capacidad real depende del hardware, consultas, conexiones SMTP y tamaño de archivos. Consulta las mediciones en `VERIFICACION.md` antes de ajustar el número de trabajadores o el límite de conexiones de MySQL.

## Salud y copias

`/health/` devuelve un estado mínimo tras comprobar base de datos y caché. No muestra credenciales ni detalles internos. Docker utiliza esta ruta para supervisar la aplicación.

Realiza copias de MySQL y del volumen de medios. Verifica una restauración independiente antes de reemplazar datos de una instalación existente.

## Validación de GitHub Actions

El workflow vigente es `.github/workflows/validacion.yml`. El trabajo corre dentro de `python:3.12-bookworm`; los servicios MySQL y Redis se resuelven como `mysql` y `redis`. No necesita publicar sus puertos en el servidor de GitHub ni buscar contenedores con `docker ps`.

Esta configuración evita que la instalación de las bibliotecas de MySQL interactúe con un servidor MySQL preinstalado del runner. La preparación de `test_senova` usa el cliente dentro del contenedor de trabajo. No se ocultan fallos de paquetes con `dpkg --configure -a || true`: si una dependencia no se instala, la validación debe detenerse.

Las claves que empiezan por `ci-` solo pertenecen a servicios efímeros de pruebas. Los secretos de la instalación y la contraseña de revisión no se incluyen en el workflow. Cada PR a `develop` verifica Ruff, migraciones, pruebas MySQL, configuración de producción, estáticos y dependencias antes de integrarse.

## Interacciones del espacio de trabajo

- `Ctrl K`, `Cmd K` o `/` abre la búsqueda; flechas y Enter eligen un resultado y Escape cierra.
- Los filtros de usuarios y evidencias conservan su estado en la URL y permiten volver con el navegador. Los formularios GET continúan funcionando sin JavaScript.
- El centro de operaciones permite períodos de 7, 30 o 90 días. El gráfico cuenta la fecha de envío de las evidencias y ofrece una tabla de datos accesible, también sin JavaScript.
- La selección de cuentas se limita a la página visible. El cambio de roles solo afecta los desplegables modificados; puede conservar varios roles existentes. Las cuentas protegidas no se pueden modificar por un administrador sin privilegios de superusuario.

## Corrección y revisión de evidencias

1. El propietario abre el detalle de una evidencia pendiente o rechazada y selecciona **Corregir evidencia**.
2. Actualiza nombre, tipo, archivo o enlace y explica qué corrigió. El plazo y la primera entrega se conservan.
3. Al guardar vuelve a revisión. El último revisor autorizado recibe un aviso en su bandeja y, si lo permite, en la cola de correo.
4. El equipo consulta el contenido y el historial antes de aprobar o rechazar. Una pestaña desactualizada debe recargar la versión vigente.

La primera entrega sigue determinando el cumplimiento del plazo; las correcciones posteriores muestran su fecha propia en el historial. Una corrección no crea una entrega nueva ni cambia retroactivamente el límite aplicado.

El registro inicial redirige al detalle para que actualizar el navegador no reenvíe el formulario. Las correcciones funcionan sin JavaScript y reutilizan el mismo formulario. El administrador nativo participa en el control de versiones y en el historial.

La migración `Gesicom.0013` añade los campos de versión y el historial. Crea un movimiento de estado histórico para las evidencias existentes en lotes de 500; conserva sus datos y adjuntos. Realiza una copia de seguridad antes de actualizar una instalación con datos y aplica las migraciones con `SENNOVA.migration_settings`, siguiendo el procedimiento habitual de despliegue.

## Diagnóstico de SMTP

`python manage.py comprobar_correo` comprueba conexión y autenticación sin enviar mensajes. `--solo-configuracion` valida los parámetros sin conectarse. El comando distingue rechazo de credenciales, error de resolución, espera agotada, certificado TLS no confiable y falta de acceso de red. Ninguno de esos mensajes muestra la contraseña ni la respuesta privada del proveedor.

Una validación de configuración no demuestra que el servidor acepte la cuenta. Si el entorno no tiene acceso a `smtp.gmail.com:587`, habilita esa salida en el despliegue antes de comprobar la autenticación. Gmail requiere una contraseña de aplicación de Google o un token OAuth2 vigente; la contraseña normal de acceso no sustituye esa autorización.


## Agenda y seguimiento de entregas

Los paneles personales destacan los plazos vencidos sin entrega y las evidencias propias rechazadas. Coordinación y dinamización disponen de una cola de revisión ordenada por primera entrega. “Mis plazos” permite buscar y filtrar por proyecto y estado; “Ver evidencias” conserva el plazo y el propietario al aplicar otros filtros.

En **Plazos de reportes → Seguimiento**, administración consulta los destinatarios activos actuales, entregas a tiempo, tardías y pendientes. Se cuentan personas, aunque una persona tenga varias evidencias. La revisión mostrada corresponde a la evidencia más reciente. El CSV exporta todos los resultados filtrados, sin limitarse a la página; neutraliza fórmulas de hoja de cálculo y no se almacena en caché.

**Preparar recordatorios** exige contraseña actual, CSRF y la revisión vigente. Crea un aviso adicional por persona pendiente y versión del plazo, respetando sus preferencias de correo. Repetir la acción no duplica avisos y no adelanta ni sustituye los recordatorios automáticos. Los filtros de la tabla no limitan esta acción: siempre cubre a quienes faltan en todo el plazo. Las peticiones sensibles tienen límites por cuenta e IP.

**Archivar** conserva las evidencias, retira el plazo de las agendas y cancela su cola pendiente. También funciona para plazos vencidos. Una edición desde Django admin utiliza el mismo servicio de versiones, grupos y avisos.

El trabajador vuelve a comprobar cuenta, preferencias, destinatarios, disponibilidad y versión del plazo antes de cada envío. Si alguien ya entregó, cancela sus recordatorios pendientes. `cancelado` identifica estos descartes normales y no se reintenta como un fallo SMTP. Los correos ya aceptados por el transporte no se pueden retirar. Una modificación concurrente durante el intercambio SMTP puede llegar después de la comprobación; queda registrado el resultado real de la aceptación. El latido del trabajador se renueva durante lotes largos.

## Organización de la bandeja

La búsqueda por título o mensaje, los filtros de tipo y lectura y la paginación comparten la misma consulta autorizada. Cada usuario puede cambiar el estado individual, seleccionar avisos de la página (máximo 100 por petición) o marcar todos los resultados filtrados. Una selección con identificadores ajenos se rechaza completa. Al consultar un aviso se comprueba el acceso actual a su destino; si fue archivado, eliminado o dejó de estar asignado, la bandeja explica el motivo.

Al actualizar, aplica `Gesicom.0014` (índice de plazo/usuario/primera entrega) y `notificaciones.0002` (revisión, actualización y estados de seguimiento/cancelación), recoge estáticos y reinicia web y trabajador. No se cambian fechas ni límites de evidencias previas. La columna `version` de avisos y `revision` de edición tienen finalidades distintas; las escrituras deben pasar por `notificaciones.plazos` para mantenerlas coherentes.

## Reportes y exportaciones

La lista de evidencias, los reportes y sus CSV comparten `Gesicom.filtros`. Se puede buscar por nombre, tipo u observaciones y combinar proyecto, estado, meses, propietario y plazo. Los proyectos históricos y los registros sin proyecto permanecen consultables. Un filtro inválido muestra errores y no devuelve registros; las descargas con filtros inválidos responden HTTP 400, sin generar un CSV de toda la base.

La serie trimestral termina en el trimestre del mes final elegido. Sin fecha final, utiliza el trimestre actual. Pantalla y CSV trimestral utilizan la misma agregación SQL y de 1 a 12 trimestres. Las aprobadas reflejan el estado actual de las evidencias registradas en cada trimestre; no se cuentan como si fueran la fecha de aprobación. El total general corresponde a todos los registros filtrados y se indica cuando la ventana trimestral solo muestra una parte.

Los gráficos permiten filtrar por proyecto o estado. Los enlaces de las tablas ofrecen la misma acción con teclado o sin JavaScript. Los filtros conservan el historial del navegador. Cada gráfico incluye una tabla de datos; la impresión utiliza estas tablas. Si Chart.js no está disponible, los datos siguen siendo consultables.

El CSV de evidencias conserva primero las seis columnas históricas y añade estado, usuario, primera entrega, plazo, límite original y entrega tardía. Se ordena según la consulta y recorre los registros en lotes de 500, sin acumular las instancias ni el documento CSV completo en Django. El controlador de MySQL puede mantener sus propios búferes de filas. Se usa UTF-8 con marca BOM para las tildes en hojas de cálculo, neutralización de fórmulas y `Cache-Control: no-store`. El CSV trimestral usa el mismo período que el gráfico. El seguimiento de plazos reutiliza la misma respuesta CSV.

## Permisos de grupos

El panel conserva los seis permisos históricos, con etiquetas que describen su función real. “Sin asignar” retira la concesión del grupo; no deniega permisos que una persona obtenga de otros grupos o de asignaciones individuales. El acceso a Django admin también requiere una cuenta de personal autorizada. Los permisos nativos no sustituyen los roles que gobiernan los paneles de GESICOM.

Guardar requiere contraseña actual y una revisión calculada sobre el grupo y sus permisos completos. La actualización bloquea el grupo, vuelve a comprobar la autorización y valida todo el formulario antes de escribir. Una pestaña antigua se rechaza; guardar sin cambios no genera otro movimiento de auditoría. Los permisos ajenos al catálogo se conservan al usar el panel de GESICOM. Se aceptan los nombres de campo históricos y el valor anterior de retirada para mantener compatibilidad.

Solo un superadministrador puede modificar el grupo `administrador` o un grupo con cuentas de personal/superusuario. Django admin utiliza la misma política, contraseña y revisión para añadir o editar grupos. Los seis grupos del sistema no se pueden renombrar ni eliminar desde esa administración, incluso en lotes mixtos. Los intentos de confirmación se limitan por identidad e IP. La auditoría registra actor y ruta, sin contraseña ni contenido de la petición.

Este bloque no necesita migraciones ni nuevas tablas de permisos. Después de actualizar, recoge los estáticos y reinicia web y trabajador para cargar los módulos compartidos.

## Adjuntos y formularios de entrega

El selector comprueba extensión, tamaño y archivos vacíos, permite quitar la selección y muestra una imagen antes de enviarla. El servidor vuelve a comprobar el contenido; una extensión correcta no basta. Los documentos de Office modernos deben estar sin contraseña. Si el formulario devuelve errores, conserva los campos de texto y explica que es necesario seleccionar otra vez el archivo. El resumen de errores recibe el foco y enlaza con los campos afectados.

Cada formulario nuevo incluye una identificación privada de 24 horas. Si el navegador repite el envío, se abre la evidencia original sin crear otra ni sustituir sus datos. Esto también funciona con JavaScript desactivado. Para otra evidencia, abre un formulario nuevo. Si el formulario ha caducado, usa el enlace que aparece en el error y copia los datos a uno nuevo. No se deben borrar sus recibos de MySQL al eliminar una evidencia: impiden que un reintento la vuelva a crear.

El detalle muestra nombre, formato y tamaño del adjunto. Los textos tienen una vista limitada de 64 KB del archivo de origen; la descarga conserva todos los bytes. Sin JavaScript se ofrece un enlace al texto completo. Si falta un archivo, el detalle y el historial siguen disponibles y el propietario puede sustituirlo o retirarlo mediante una corrección. Una vista de descarga todavía puede devolver 404 si el archivo desaparece después de abrir el detalle.

Antes de actualizar, respalda MySQL y los medios. Aplica `Gesicom.0015_solicitudes_adjuntos`, recopila estáticos y reinicia web y trabajador. La migración añade un índice por nombre de archivo y recibos internos, sin modificar fechas, proyectos, adjuntos ni historial previos; no crea recibos para entregas históricas. El personal de Django necesita permiso explícito de consulta o cambio de evidencias para abrir sus archivos. Las evidencias existentes mantienen su plazo como solo lectura en esa administración.

## Campana de notificaciones

La campana muestra el contador y hasta cuatro avisos recientes. Al abrirse actualiza también los títulos y su estado de lectura; mientras permanece abierta, continúa actualizándose sin recargar el panel. Conserva el foco del aviso seleccionado si sigue en la lista. Si desaparece, el foco vuelve al control de la campana. El distintivo muestra hasta `99+`; su etiqueta accesible conserva el total real.

La consulta periódica se programa cada 45 segundos después de terminar la anterior. Se suspende al ocultar la pestaña o perder conexión, se cancela si no responde en diez segundos y no se solapa con otra. Los fallos amplían la espera hasta cinco minutos, respetando una espera mayor de `Retry-After`. Si falla una actualización, la lista anterior sigue disponible y se ofrece reintentar o consultar la bandeja. Volver a la pestaña o recuperar conexión solicita un resumen actualizado.

Estas consultas no prolongan la sesión por inactividad. Cuando el servidor devuelve acceso caducado, el navegador vuelve al ingreso. Abrir un aviso continúa usando POST con CSRF y la autorización actual de su destino. Sin JavaScript, la lista inicial y esos formularios siguen funcionando.

El resumen básico conserva su respuesta anterior con `pendientes`; `?detalle=1` añade cuatro avisos de la cuenta, con título, fecha, lectura y ruta de apertura. No devuelve el mensaje completo ni destinatarios. Su lectura utiliza una consulta de notificaciones para el contador y una segunda solo cuando se piden los avisos; el control de sesión realiza sus propias comprobaciones. No hay caché de respuestas ni estado compartido entre usuarios. Este bloque no cambia tablas: recopila estáticos y reinicia la aplicación web.

## Filtros y conservación de ediciones

Los paneles con filtros actualizan el contenido del panel sin volver a generar la cabecera de navegación ni su resumen de avisos. Conservan las mismas rutas, filtros, permisos y formularios POST. Sin JavaScript, el botón sigue abriendo la página completa. El directorio valida búsqueda, estado y rol; una opción inválida muestra el error y ningún resultado.

Una observación o cambio de roles pendiente pide confirmación antes de cambiar la lista o abandonar esa sección. Mientras hay una edición pendiente, escribir en la búsqueda espera al botón de filtros, sin interrumpir cada pausa con una confirmación. Escribir en una fila durante una actualización detiene esa actualización y conserva la edición. Guardar la observación o confirmar el envío de roles permite continuar.

Cancelar Atrás o Adelante conserva tanto los datos visibles como la dirección y la entrada del historial. Aplicar exactamente los mismos filtros refresca los datos sin añadir otra entrada. La paginación con teclado lleva el foco a los nuevos resultados.

Si una consulta falla o no responde en quince segundos, se conservan los resultados y filtros aplicados y aparece **Reintentar actualización**. Un fallo durante Atrás también puede reintentarse sin perder la entrada de Adelante. Una respuesta incompleta no sustituye una parte de las regiones. Las ediciones pendientes solo permanecen en la página actual: no se guardan como borradores en el navegador ni se recuperan después de cerrar la pestaña.

No hay cambios de esquema en este bloque. Recopila los estáticos y reinicia la aplicación web para cargar el renderizado compartido y `navigation.js`.

## Calendario personal y descarga de plazos

**Mis plazos** conserva la lista inicial de todos los meses. El selector **Calendario** abre el mes actual, con navegación al anterior, siguiente y actual. Búsqueda, proyecto, estado y mes se comparten entre ambas vistas. Seleccionar un evento abre sus indicaciones completas y permite enviar el reporte o consultar sus evidencias. En pantallas pequeñas se muestran los días con entregas, con sus fechas y estados. Administración de plazos incluye un acceso a **Mi calendario**; mantiene el alcance personal de la cuenta.

El campo de mes es opcional en la lista y obligatorio en calendario. Se aceptan meses de `1000-01` a `9998-12`; el mes se incorpora a la URL para que Atrás y Adelante recuperen la misma consulta. Un filtro inválido muestra el error, oculta los resultados y deshabilita la descarga. Los límites mensuales y las horas visibles se interpretan en Colombia, incluyendo el último minuto de cada mes.

**Descargar plazos (.ics)** incluye todos los resultados de los filtros, aunque ocupen varias páginas. El archivo se puede importar manualmente en un calendario compatible, como Google Calendar u Outlook. Los eventos indican la hora límite, el proyecto, el estado de entrega y las instrucciones. Se exportan fechas UTC para conservar el instante; revisa la zona horaria elegida en el calendario de destino. No se envían invitaciones ni se programa una alarma externa.

Es una copia del momento de la descarga, sin sincronización. Una entrega posterior, un cambio de fecha o el archivo de un plazo no modifica las copias ya importadas. La aplicación de destino decide cómo trata una nueva importación; revisa los eventos existentes antes de repetirla. El identificador del evento es estable por plazo mientras se conserve `PUBLIC_BASE_URL`. Configura esa variable con la dirección pública correcta antes de distribuir archivos; nunca se toma el dominio de la cabecera `Host`. Una dirección inválida omite los enlaces al portal y utiliza un espacio de identificadores de reserva.

La cuadrícula limita a 500 los eventos visibles y lo indica al superar esa cantidad. Aplica filtros, usa la lista o descarga para consultar los demás. El archivo es personal y puede contener instrucciones del centro; compártelo solo con quien deba consultarlo. El endpoint `/notificaciones/plazos/calendario.ics` requiere iniciar sesión y no admite enlaces públicos de suscripción.

Este bloque no requiere migraciones. Recopila estáticos y reinicia la aplicación web para cargar las plantillas y `calendar.css`.

## Historial administrativo

En **Centro de operaciones → Actividad reciente → Ver historial** se consulta la auditoría existente. Requiere el rol de administrador o superusuario; ser personal de Django por sí solo no concede este acceso. La pantalla permite buscar por nombre, cuenta, acción o ruta, y filtrar fechas completas de Colombia. Muestra 25 registros por página, ordenados por fecha y por identificador cuando las fechas coinciden.

El filtro distingue solicitudes con código HTTP, respuestas 400–599 y registros internos. El código describe la respuesta de la petición, sin asegurar por sí solo que se guardó un cambio: una redirección también puede acompañar un mensaje de validación. Despliega **Ver detalles** para consultar la acción registrada, ruta e IP. Un evento sin actor puede proceder de una solicitud anónima, mantenimiento o una cuenta eliminada. La IP puede representar una red compartida o una VPN.

**Descargar CSV filtrado** incluye todas las páginas de la consulta, con Unicode, fechas y desplazamiento horario de Colombia. Los campos se limitan a la actividad visible; no exporta los campos de correo, contraseña, PIN ni claves de sesión. Mantén ese archivo dentro del uso administrativo autorizado. Un filtro inválido oculta resultados y descarga; el endpoint de CSV responde con HTTP 400 para corregirlos. Leer, filtrar y exportar no cambia ni elimina eventos.

La página y descarga funcionan también sin JavaScript. La navegación con filtros y fechas utiliza el controlador compartido; no hay un segundo menú de administración. El bloque no cambia tablas ni requiere migraciones: recopila estáticos y reinicia la aplicación web.

## Herramientas y organización del código

`python scripts/actualizar_instalacion.py` ejecuta comprobaciones, migraciones y recopilación de estáticos, deteniéndose al primer error. Resuelve el directorio del proyecto desde el archivo, incluso al invocarlo desde otra carpeta. `sync_database.py` y `sync.ps1` mantienen los accesos anteriores y remiten a esa implementación. `--help` muestra el uso sin ejecutar la actualización.

Las rutas están junto a cada aplicación y las pruebas en `tests/`; los comandos de CI siguen usando `SENNOVA.test_settings`. Consulta [DESARROLLO.md](DESARROLLO.md) para ubicar archivos o ejecutar solo una funcionalidad. Las migraciones permanecen con sus aplicaciones; el esquema de MySQL no tiene una segunda definición SQL.

## Bandeja, fechas y cambios de lectura

La bandeja permite filtrar la fecha de creación de los avisos por días completos de Colombia. Las fechas, búsqueda, tipo, estado e identificador se validan tanto al consultar como al marcar resultados. Un filtro inválido muestra el error, oculta los resultados y deshabilita la operación sobre ellos; una petición filtrada inválida no modifica avisos. Los accesos históricos sin alcance explícito conservan la operación sobre toda la bandeja personal; un alcance desconocido se rechaza.

Con JavaScript, marcar leído o sin leer actualiza los resultados y la campana sin recargar el documento. La selección se limita a la página; **Marcar resultados como leídos** abarca todas las páginas de los filtros. La operación conserva los filtros aplicados, la página y las preferencias que se estén editando. Mientras se procesa una acción se bloquean sus controles para evitar un segundo envío; una búsqueda iniciada entretanto conserva su texto y termina antes de refrescar los resultados vigentes.

Si no se confirma una respuesta en quince segundos se informa de la incertidumbre y se ofrece **Actualizar bandeja**. Ese botón consulta los datos actuales, sin repetir la operación de lectura. Si el cambio se confirmó pero falla la consulta posterior, **Reintentar actualización** vuelve a consultar. Repetir explícitamente una marca de leído ya aplicada no sustituye su primera fecha de lectura. Sin JavaScript, los mismos formularios siguen funcionando con su redirección y CSRF.

El protocolo de lectura interactivo utiliza la cabecera exacta `X-Inbox-Action: 1` en las rutas POST existentes. Devuelve `mensaje` y `actualizados` al confirmar, o un `error` con HTTP 400/404 ante filtros o selección inválidos. La cabecera no evita la autenticación ni CSRF. Abrir el destino de un aviso mantiene su flujo de navegación anterior.

## Reloj de Colombia

El pie de las páginas autenticadas muestra hora de 24 horas, segundos, fecha y zona de Bogotá. Permanece en el flujo del documento, separado de formularios y tablas, y se adapta a pantallas pequeñas. No se incluye en la impresión de reportes ni anuncia los segundos repetidamente a lectores de pantalla.

Con JavaScript utiliza la hora del dispositivo en `America/Bogota`, incluso si el navegador tiene otra zona horaria. Se actualiza localmente, funciona sin conexión y pausa su temporizador cuando la pestaña está oculta; al volver recupera la hora vigente. Sin JavaScript presenta la referencia del servidor al cargar la página. Las fechas límite y la caducidad de credenciales continúan calculándose en el servidor.

Este bloque no cambia tablas ni añade dependencias. Recopila estáticos y reinicia la aplicación web para cargar la bandeja, el controlador de actualización y el reloj.

## Directorio administrativo y CSV

En **Usuarios**, **Descargar CSV filtrado** incluye todos los resultados de la búsqueda, estado y rol aplicados, aunque ocupen varias páginas. No crea otro panel ni cambia la selección de cuentas. Una descarga conserva las ediciones pendientes de la página; esas ediciones solo se aplican al confirmar el guardado con la contraseña actual.

El archivo contiene identificador, usuario, nombre, correo, roles, estado y fecha de registro en Colombia. Se ordena por identificador ascendente; la pantalla conserva su orden de registro más reciente. Es información personal para uso administrativo autorizado. La auditoría registra la solicitud de exportación, no confirma que el navegador haya terminado de recibirla.

La descarga recorre consultas de hasta 500 cuentas y sus grupos, sin `OFFSET` ni cargar todo el directorio en Django. Al comenzar fija el identificador máximo y excluye altas posteriores con identificadores mayores. Una modificación o eliminación concurrente puede reflejarse en los lotes siguientes; el archivo no es una instantánea transaccional global. El controlador de MySQL puede mantener el búfer de cada consulta acotada.

Guardar roles o activar/desactivar cuentas conserva búsqueda, estado, rol y página, también ante un error de contraseña. Si la última página deja de existir al cambiar el estado, se muestra la última disponible. Los filtros inválidos ocultan resultados y descarga; el CSV responde HTTP 400. Los mismos formularios y enlaces funcionan sin JavaScript.

Este bloque no requiere migraciones ni dependencias nuevas. Recopila estáticos y reinicia la aplicación web para cargar los módulos y plantillas actualizados.

## Búsqueda global y conexión

El control de la cabecera y `Ctrl K`/`Cmd K` abren el buscador único. Las flechas recorren los resultados, Enter abre el elegido y Escape cierra y devuelve el foco. Los accesos rápidos se filtran localmente; a partir de dos caracteres se consultan los registros autorizados. La escritura espera una pausa breve y la composición de texto termina antes de consultar.

Cada consulta tiene una espera máxima de diez segundos, incluida la lectura de la respuesta. Cambiar el texto, cerrar el diálogo u ocultar la pestaña cancela la consulta pendiente. Una respuesta antigua no sustituye la nueva. Los errores ofrecen **Reintentar búsqueda** y mantienen los accesos rápidos de la consulta. Recuperar la conexión o volver a la pestaña permite reintentar, sin iniciar otra petición automáticamente.

Al superar el límite por cuenta, el diálogo respeta `Retry-After` en segundos o fecha HTTP y muestra el tiempo de espera inicial. No consulta otro término durante esa espera, incluso después de cerrar y reabrir el diálogo en la misma página. Al terminar se habilita el botón, sin enviar una consulta nueva. Recargar la página no elimina el límite aplicado en el servidor.

**Buscar en evidencias** conserva el texto en la consulta de ese módulo, con su propio alcance y filtros. Si JavaScript está desactivado, el navegador no admite el diálogo o el controlador no carga, la cabecera mantiene un formulario HTML de búsqueda de evidencias. Los registros de usuarios solo aparecen para administración y los avisos siempre pertenecen a la cuenta conectada.

Este bloque no cambia tablas ni dependencias. Recopila estáticos y reinicia la aplicación web para cargar `search.js` y las plantillas. `workspace.js` conserva las operaciones administrativas y sus confirmaciones.
