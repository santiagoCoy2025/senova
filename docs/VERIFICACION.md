# Verificación de la revisión

Fecha: 11 de noviembre de 2026. Las mediciones corresponden al entorno local de revisión.

## Pruebas y dependencias

- 96 pruebas automatizadas contra MySQL, incluidas concurrencia, permisos, recuperación y salud en producción.
- `check`, `check --deploy`, revisión de migraciones y Ruff sin incidencias.
- Recopilación de archivos estáticos con manifiesto completada.
- Auditoría de los 15 paquetes de ejecución fijados: sin vulnerabilidades conocidas en la consulta realizada.
- Chart.js 4.4.8: sin avisos en la consulta al registro de npm.
- Imagen Docker construida y arrancada con usuario 10001: migraciones, estáticos, salud HTTP interna, redirección HTTPS, HSTS y acceso administrativo comprobados.

Estas comprobaciones no sustituyen una auditoría de penetración ni garantizan ausencia de vulnerabilidades futuras.

## Capacidad HTTP

- MySQL 8.4, Redis y Gunicorn con 4 procesos y 2 hilos.
- 1.200 cuentas y 12.000 evidencias temporales.
- 2.400 peticiones autenticadas, con 40 clientes concurrentes.
- Cero errores; duración 15,97 s; mediana 187,42 ms; percentil 95 de 758,2 ms.
- Rendimiento observado: 150,31 peticiones/s.

La prueba alterna el panel de usuario y la lista de evidencias. No representa 1.200 inicios de sesión simultáneos, envíos SMTP reales ni descargas masivas. Los datos temporales se eliminaron al terminar.

## Consultas y cola

Con 1.200 usuarios y 12.000 evidencias, las vistas administrativas, de evidencias y de reportes necesitaron 9, 8 y 10 consultas respectivamente. Publicar avisos para 1.200 usuarios utilizó 13 consultas, sin esperar envíos SMTP dentro de la petición web.

Se comprobaron dos publicaciones simultáneas de una misma novedad y dos trabajadores reclamando correo: no duplicaron avisos ni tomaron los mismos mensajes.

## Flujos verificados

- PIN de seis dígitos enviado a Mailpit, rechazo de PIN incorrecto, verificación y cambio de contraseña.
- La pantalla de nueva contraseña no está disponible antes de verificar el PIN.
- Inicio de sesión con la contraseña nueva.
- Publicación dirigida, creación de plazo, entrega asociada, revisión y aviso al propietario.
- Captura del aviso de vencimiento y preferencias de correo.
- Acceso denegado a archivos de otros usuarios y a descargas anónimas.
- Encabezados de seguridad, CSRF, límites, caducidad, reutilización y aislamiento de sesiones.
- Copia de MySQL y restauración en una base independiente con las seis cuentas de revisión.
- Renderizado de los roles y adaptación a escritorio/móvil.
- 129 vistas comprobadas en navegador, entre 320 y 1.440 píxeles, sin desbordamientos ni errores JavaScript.

Los mensajes de la revisión se capturaron localmente; no se enviaron a Internet. El acceso SMTP real queda sujeto a la credencial privada de Gmail.

## Actualización de Gmail y seguridad

Se comprobaron 30 pantallas adicionales en navegador, con los seis roles y escritorio/móvil: reautenticación, confirmación de contraseña, cierre de otras sesiones, recuperación en cola, remitente Gmail capturado en Mailpit, revocación después de recuperar y pantalla HTML de límite de intentos. No hubo errores JavaScript ni desbordamientos.

Las pruebas incluyen dos trabajadores enviando correos de seguridad sin repetir destinatarios, eliminación del contenido cifrado, reintentos, clave de cifrado anterior durante una rotación, vinculación del PIN a las credenciales y rechazo de sesiones previas a la nueva política. Gmail real requiere su contraseña de aplicación; la captura local no valida esa autenticación.

## Repetición

```bash
python manage.py test --settings=SENNOVA.test_settings --noinput
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py collectstatic --noinput
ruff check .
python scripts/prueba_carga_http.py
```

Las pruebas de concurrencia requieren MySQL y utilizan una base de pruebas independiente. Los archivos de resultados y las credenciales locales se guardan en `.local/`, fuera del repositorio.

## Centro de operaciones e interacciones — 12 de noviembre de 2026

- 117 pruebas automatizadas con MySQL, incluidas las 96 de la revisión anterior. Se añadieron regresiones de aislamiento de búsqueda, autorización tras retirar roles, limitación por cuenta, caída del contador, transacciones masivas, cuentas protegidas, revocación al desactivar y datos históricos sin propietario o autor.
- 40 comprobaciones de navegador: seis roles en escritorio y móvil, y administración a 320, 768 y 1.440 píxeles. Sin errores JavaScript, CSP ni desbordamientos.
- Cierre de la búsqueda con Escape incluso con texto escrito y devolución de foco al botón.
- Gráfico real de 7/30/90 días, actualización sin recarga y navegación con Atrás; búsqueda con teclado, selección de resultados y cierre; filtros, paginación y observaciones tras sustituir filas; selección, cancelación, activación, desactivación y cambio de roles con confirmación.
- Filtros y formularios de administración comprobados con JavaScript desactivado. La tabla de datos del gráfico se genera en el servidor.
- Ruff, comprobación de migraciones, configuración de producción y recopilación de estáticos completados. No se requiere una migración nueva.
- Las nueve consultas de `database/consultas/diagnostico.sql` se ejecutaron contra MySQL; solo consultan metadatos y contadores.

La revisión utilizó dos cuentas, 33 evidencias y un plazo temporales. Se eliminaron al terminar; permanecen las seis cuentas y los datos de revisión previos. La contraseña solicitada para el administrador solo se aplicó a la base local y al archivo privado de credenciales. No forma parte del código, del workflow ni de la configuración SMTP.

El workflow conserva el contenedor Python y las conexiones internas a MySQL/Redis ya corregidas. La imagen de aplicación y la medición HTTP de capacidad descritas arriba corresponden a la revisión anterior; este bloque se comprobó con Gunicorn, MySQL y Redis, además de la validación automática del PR.

## Correcciones, historial y administrador nativo — 12 de noviembre de 2026

- 147 pruebas con MySQL, incluidas propiedad de registros, rechazo de versiones desactualizadas, conservación del plazo original, historial privado, preferencias de avisos, limpieza de archivos tras un fallo y pruebas concurrentes de corrección/aprobación.
- Se comprobó la protección de privilegios en el administrador nativo, la revocación de sesiones y PIN al desactivar, los avisos a ambas direcciones al cambiar correo, el cambio de contraseña propio sin perder la nueva sesión y la preservación de un hash actualizado durante una edición de perfil.
- 37 comprobaciones de navegador: ciclo de rechazo/corrección/aprobación con archivo, dos pestañas en conflicto, observaciones después de filtrar, privacidad, actualización desde Django admin, alta con redirección y corrección mediante teclado sin JavaScript. Seis roles en escritorio/móvil y detalle/formulario a 320, 768 y 1.440 píxeles, sin errores JavaScript, CSP ni desbordamientos.
- La migración 0013 se aplicó al MySQL de revisión e incorporó el registro existente al historial. La prueba de datos históricos confirma que no altera fechas, estado ni adjuntos anteriores.
- Diez consultas SQL de diagnóstico ejecutadas correctamente. Ruff, comprobación de migraciones, producción y estáticos completados.

La comprobación externa de `smtp.gmail.com:587` devolvió `ENETUNREACH` (red inaccesible) antes de autenticar. No se enviaron mensajes reales y la credencial no quedó validada frente a Google. El comando ahora distingue ese fallo de un rechazo de contraseña. La configuración privada sigue fuera del historial Git; las pruebas de correo utilizan transporte local.

Los datos de navegador fueron temporales: dos cuentas, un plazo y dos evidencias, con sus movimientos y adjunto. Se retiraron al finalizar. Se conservan las seis cuentas y los datos de revisión previos; el registro de evidencia anterior cuenta ahora con su movimiento histórico.

## Estabilidad de las pruebas de límites

La ejecución posterior a integrar el PR de evidencias cruzó una frontera de diez minutos durante la prueba de usuario/correo: el contador entró en otra ventana y la expectativa anterior dejó de corresponder con esa petición. La prueba ahora fija únicamente el reloj del middleware, manteniendo real el de la caché. Un caso adicional comprueba el bloqueo al final de una ventana, `Retry-After: 1` y el acceso en la siguiente. La batería completa consta de 148 pruebas; el comportamiento del servidor no se modifica con esta corrección.

## Agenda, cumplimiento y comunicaciones — 12 de noviembre de 2026

- 186 pruebas con MySQL (38 adicionales): seguimiento por destinatario, conservación del límite original, agrupación sin duplicados, filtros y CSV seguro, bandeja individual y masiva, CSRF, permisos, contraseña actual y límites de intentos. El reloj de la prueba nueva de límites también se fija solo en el middleware.
- Dos administradores recordando simultáneamente no duplican avisos; dos editores del mismo plazo producen un guardado y un conflicto. Se comprueban el guardado sin cambios, el archivo de plazos vencidos y la misma política desde Django admin. El campo de fecha nativo ya no mezcla un campo de fecha dividida con un control de fecha único.
- El trabajador descarta correo pendiente después de una entrega, cambio de versión, retiro de grupos, desactivación o cambio de preferencias. Las regresiones verifican que una fila eliminada no reaparece y que una cancelación concurrente no se vuelve a poner en cola tras un fallo SMTP. El latido se mantiene durante lotes largos.
- 55 comprobaciones en Chromium con los seis roles en escritorio y móvil: agenda, bandeja, seguimiento, filtros dinámicos y navegación Atrás, exportación filtrada, recordatorio adicional, lectura tras sustituir filas, dos pestañas en conflicto, administrador nativo y archivo con apertura de aviso antiguo. Agenda, evidencias asociadas y selección de notificaciones comprobadas sin JavaScript.
- Otras ocho comprobaciones de la agenda a 320, 390, 600, 768 y 1.440 píxeles confirman que la tabla personal se adapta a tarjetas y deja visibles las acciones. Sin errores JavaScript, CSP ni desbordamientos en la revisión de los paneles.
- Con 1.200 destinatarios y 12.000 evidencias, el seguimiento paginado utilizó 10 consultas y unos 135 ms en la ejecución completa local. La selección de grupos usa subconsultas sin duplicar personas y el conteo excluye las subconsultas de revisión que solo necesita la página visible. Usuarios, evidencias y reportes conservaron 9, 8 y 10 consultas, respectivamente. Estas cifras describen este entorno y conjunto de datos, no una garantía de latencia de producción.
- Migraciones `Gesicom.0014` y `notificaciones.0002` aplicadas al MySQL local tras una copia privada. Ruff, ausencia de migraciones pendientes, comprobación de producción y recopilación de estáticos correctos. Doce consultas SQL de diagnóstico completadas.

Las tres cuentas, tres plazos, dos evidencias y la publicación usados en navegador se retiraron con sus avisos. Se conservaron las seis cuentas, la evidencia con su movimiento histórico, los dos plazos y los ocho avisos previos. Los correos de pruebas utilizan captura local; Gmail continúa pendiente de validación de acceso y autenticación SMTP en el entorno de despliegue.

## Reportes accesibles y permisos de grupos — 12 de noviembre de 2026

- 216 pruebas con MySQL (30 adicionales): períodos históricos, meses inválidos o invertidos, filtros comunes, aislamiento por rol/propietario, proyectos históricos y sin clasificar, límites de calendario, CSV Unicode y protección de fórmulas. Las columnas previas del CSV se conservan y se añaden los datos de seguimiento.
- El CSV trimestral y el gráfico utilizan la misma serie, hasta el mes final elegido. Las pruebas confirman una agregación acotada tanto para uno como para doce trimestres. Con 12.000 evidencias, la descarga completa utilizó cinco consultas y unos 450 ms en este entorno. Reportes conservó diez consultas; la lista de evidencias utilizó nueve, incluida la consulta de clasificaciones históricas autorizadas.
- Las pruebas de permisos cubren contraseña y revisión obligatorias, actualización parcial sin perder otros permisos, rechazo completo de campos desconocidos, permisos homónimos de otro modelo, CSRF, límites por cuenta, autorización retirada, grupos protegidos y auditoría sin duplicar movimientos al guardar sin cambios.
- Dos editores concurrentes del mismo grupo producen un guardado y un conflicto. La edición nativa comparte esa revisión, confirma la contraseña y conserva los grupos del sistema ante renombrado, eliminación y selección mixta. Un editor de Django no puede elevar sus privilegios modificando un grupo que contenga cuentas de personal.
- 41 comprobaciones en Chromium: seis roles en reportes/evidencias a 390 y 1.440 píxeles; reportes/permisos de administración a 320, 768 y 1.440 píxeles; actualización de gráficos sin duplicar instancias; Atrás; proyectos históricos; descarga filtrada; error de rango; impresión; contraseña; conflictos entre pestañas; edición nativa y bloqueo de grupos protegidos. Reportes y filtros comprobados sin JavaScript.
- Diez comprobaciones adicionales verifican filtros al pulsar segmentos, una ventana histórica de doce trimestres en cinco anchos, restauración del valor predeterminado de trimestres, datos disponibles si no carga Chart.js y guardado de permisos sin JavaScript. El PDF de prueba contiene las cuatro tablas de datos. Se corrigió una regla anterior que las ocultaba al imprimir.
- Ruff, configuración de producción, estáticos y trece consultas SQL de diagnóstico completados. No hay nuevas migraciones ni tablas duplicadas.

Los datos visuales son temporales: tres cuentas, un grupo y 38 evidencias. Se retiran con sus sesiones y avisos al finalizar la revisión; las cuentas y registros previos se conservan. Las capturas utilizan nombres de ejemplo. Esta comprobación no activa Gmail real: la validación de acceso y autenticación SMTP sigue pendiente en el despliegue.

## Adjuntos, reintentos y conservación de entregas — 12 de noviembre de 2026

- 249 pruebas con MySQL (33 adicionales): formatos y contenido, imágenes dañadas o de resolución excesiva, estructura de Office, archivos vacíos, límites, acceso privado del personal autorizado, rutas compartidas y adjuntos ausentes. La vista de texto conserva las tildes y limita la lectura; la descarga mantiene el archivo completo.
- Las pruebas de alta cubren firma vinculada a la cuenta, caducidad, reintento después de entregar o archivar el plazo, pérdida del archivo en el navegador, datos distintos en el reintento y eliminación o reasignación de la evidencia original. Dos peticiones concurrentes del mismo UUID producen una evidencia, un archivo, un recibo y un movimiento. Un fallo revierte la escritura y permite volver a intentarlo.
- La retirada de archivos se comprueba después del commit, con referencias compartidas, rollback y eliminación de cuentas. El límite de un archivo por petición se verifica también en el servidor.
- La administración conserva plazos y fechas de evidencias existentes; una entrega nueva registra el límite original y exige un plazo activo, asignado y pendiente para su destinatario/proyecto. Se verifica que las correcciones preservan clasificaciones históricas, incluidos registros sin proyecto y plazos reclasificados después.
- 60 comprobaciones en Chromium: seis roles en formulario/listado a 390 y 1.440 píxeles; detalle y corrección a 320, 768 y 1.440; selección con imagen, quitar selección, arrastrar, errores de formato/contenido, foco y enlaces del resumen, envío asociado a plazo, reintentos sin archivo, texto largo y Windows-1252, adjunto ausente, PDF privado, permiso nativo de consulta y proyecto histórico. El alta identificada y el texto completo se comprobaron sin JavaScript. Nombres largos y selector de archivos se revisaron entre 320 y 1.440 píxeles. Sin desbordamientos, errores JavaScript ni infracciones CSP.
- Copia privada de MySQL comprobada y migración `Gesicom.0015_solicitudes_adjuntos` aplicada. El índice por nombre de archivo y los recibos no modifican registros anteriores. Ruff, migraciones, configuración de producción, estáticos, sintaxis JavaScript y catorce consultas SQL de diagnóstico completados.

Se retiraron tres cuentas, un grupo, un plazo y nueve evidencias temporales, con sus sesiones, recibos, avisos y archivos. Se conservaron las seis cuentas, la evidencia con su movimiento histórico, los dos plazos y los ocho avisos de revisión previos. El trabajador local utiliza captura de correo; esta revisión no envía mensajes reales ni valida autenticación de Gmail.

## Campana actualizada y consultas de bandeja — 12 de noviembre de 2026

- 257 pruebas con MySQL (ocho adicionales): compatibilidad del resumen básico, aislamiento del destinatario, límite de cuatro avisos, orden estable, respuesta de solo lectura, CSRF al abrir, títulos escapados y conteo accesible superior a 99. La consulta detallada tampoco prolonga una sesión inactiva y devuelve JSON 401 al caducar.
- El resumen utiliza una consulta de notificaciones sin detalle y dos con los cuatro avisos. Las pruebas verifican que la bandeja y su cabecera realizan un único conteo de pendientes en la petición. Otra petición vuelve a consultar; no se comparten resultados entre cuentas.
- 41 comprobaciones en Chromium: publicación dirigida visible sin recargar, títulos insertados como texto, foco conservado, apertura con POST/CSRF, exclusión de avisos ajenos, ausencia de peticiones solapadas, error temporal, respeto de `Retry-After`, consulta sin respuesta y reintento, pausa con pestaña oculta o sin conexión, recuperación, lista vacía y vuelta al ingreso al cerrar la sesión. Los tiempos y fallos de red se simularon en el navegador; no se provocaron cortes en los servicios.
- Seis roles en reportes y bandeja a 390 y 1.440 píxeles, además de la campana abierta entre 320 y 1.440 píxeles. Lista inicial y apertura comprobadas sin JavaScript. Sin errores JavaScript, infracciones CSP ni desbordamientos.
- Ruff, ausencia de migraciones nuevas, configuración de producción y recopilación de estáticos correctos. No se añadieron tablas ni paneles.

Se retiraron las tres cuentas, el grupo, la publicación y sus avisos de prueba con las sesiones; se conservaron las seis cuentas y los registros anteriores. Los datos de las capturas son ficticios y el correo continúa en captura local.

## Filtros ligeros y protección de ediciones — 12 de noviembre de 2026

- 266 pruebas con MySQL (nueve adicionales): los nueve paneles aceptan página completa y fragmento, mantienen el aislamiento, filtros, permisos, versiones, CSRF y caché privada. Las consultas de la cabecera no se ejecutan al devolver un fragmento; los parámetros de URL no permiten elegir otra plantilla.
- Se reprodujeron y corrigieron la pérdida de una observación durante una actualización, la incoherencia entre URL y resultados al cancelar Atrás y el error 500 del directorio con `rol=²`. Roles inexistentes, cadenas numéricas excesivas, estados desconocidos y búsquedas demasiado largas muestran errores y ningún resultado, también en la ruta histórica del directorio.
- 66 comprobaciones en Chromium: igualdad de los resultados completos y parciales de los nueve paneles, aislamiento, edición mientras hay una consulta, confirmación y cancelación de Atrás/Adelante, historial sin duplicados, salida de la sección, guardado de observaciones y roles, filtros inválidos, gráficos, paginación y funcionamiento sin JavaScript. Seis roles en evidencias/bandeja a 390 y 1.440 píxeles y avisos de error/edición entre 320 y 1.440.
- Las pruebas de red simulan respuestas fuera de orden, error temporal, respuesta incompleta y una consulta que excede quince segundos. Se comprueba que la tabla y los filtros aplicados se conservan, que se puede reintentar una navegación fallida sin perder Adelante y que una sesión revocada vuelve al ingreso. No hubo errores JavaScript, infracciones CSP ni desbordamientos en las comprobaciones completadas.
- Con los datos ficticios locales, el HTML sin comprimir disminuyó entre el 27,7 % y el 82,1 %, según el panel. Evidencias pasó de 9 a 7 consultas y reportes de 10 a 8; la bandeja evitó una consulta y los otros paneles dos. Estas medidas comparan las dos representaciones de los mismos resultados; no son una garantía de latencia o capacidad de producción.
- Ruff, configuración de producción, sintaxis JavaScript, estáticos y comprobación de migraciones correctos. No hay tablas ni migraciones nuevas. Los filtros mantienen el renderizado completo cuando no se solicita un fragmento.

Se retiraron tres cuentas, trece evidencias, un grupo, un plazo y una publicación, con sus movimientos, avisos y sesiones. Se conservaron las seis cuentas, la evidencia con su movimiento histórico, los dos plazos y los ocho avisos anteriores. El correo local permanece en captura, sin validación de Gmail real.

## Calendario personal y archivo iCalendar — 13 de noviembre de 2026

- 289 pruebas con MySQL (23 adicionales): lista sin mes, límites de Colombia, navegación de años admitidos, filtros inválidos, estados de entrega y plazo original. La lista, cuadrícula y archivo aplican el mismo alcance personal; las pruebas incluyen superusuario, cambios de pertenencia, archivo, grupos coincidentes y parámetros de otras cuentas.
- Exportación de 242 eventos de varias páginas con una sola consulta de eventos. Otra regresión comprueba que 510 plazos producen una cuadrícula limitada a 500 con aviso y un archivo con los 510 resultados. Se verificaron identificadores estables, revisión, fechas UTC, cabeceras privadas, GET/HEAD, rechazo de POST, host no confiable, Unicode y saltos de línea que intentan añadir componentes o destinatarios.
- 68 comprobaciones de Chromium y presentación: cambio lista/calendario sin recargar, filtros, anterior/siguiente/actual, Atrás/Adelante, apertura con indicaciones completas y plazo precargado al entregar, consulta de evidencias, descarga real del navegador, mes inválido y recuperación. Seis roles en las dos vistas a 390 y 1.440 píxeles, con calendario y estados entre 320 y 1.440; formularios, navegación y descarga también sin JavaScript. Sin errores JavaScript, infracciones CSP ni desbordamientos en las comprobaciones realizadas.
- Con los datos ficticios locales, la página completa de calendario realizó siete consultas y la descarga tres; solo una consulta de la descarga obtuvo los eventos. Estas medidas no garantizan latencia ni capacidad de producción. Las pruebas previas con 1.200 usuarios y 12.000 evidencias se volvieron a ejecutar dentro de la batería completa.
- Ruff, comprobación de formato de las seis plantillas modificadas, configuración de producción, estáticos y ausencia de migraciones nuevas correctos. Tras los últimos ajustes de legibilidad se repitieron las 23 pruebas específicas y la revisión adaptable. No hay dependencias ni tablas nuevas.

Los archivos se validaron y descargaron localmente; no se importaron en cuentas externas de Google u Outlook. Son copias sin sincronización, invitaciones ni alarmas. Se retiraron las tres cuentas, los dos grupos, los dieciocho plazos y las dos evidencias temporales, con sus movimientos, avisos y sesiones. Permanecen seis cuentas, una evidencia con su movimiento, dos plazos y ocho avisos. Las capturas contienen datos ficticios; el correo continúa capturado localmente, sin validación de Gmail real.

## Organización del proyecto e historial administrativo — 13 de noviembre de 2026

- Se agruparon 29 módulos de pruebas en seis carpetas `tests/`. El inventario antes/después confirma que se conservan las 289 pruebas anteriores. La separación de rutas por aplicación conserva las 161 rutas originales, con sus nombres y vistas; se comparó también el alias `core.urls`. Las dos rutas añadidas corresponden únicamente al historial administrativo y su CSV. La paginación común se centralizó en `ui/`, conservando el acceso de plantilla histórico.
- 306 pruebas con MySQL (17 nuevas): acceso por rol y superusuario, retiro de permisos, eventos con actor eliminado, orden estable, filtros de texto y fechas completas de Colombia, parámetros inválidos, respuestas HTTP, registros históricos malformados, HTML escapado y CSV con neutralización de fórmulas. La descarga de 120 registros usa una consulta de eventos, incluye todas las páginas y no exporta los campos de correo o hash de contraseña. GET/HEAD no añade ni modifica eventos.
- 87 comprobaciones de Chromium y presentación: acceso desde `/`, enlace del centro de operaciones, búsqueda, tipos, fechas, intervalos inválidos, detalles con teclado, paginación, Atrás/Adelante y descarga del archivo completo o filtrado. Seis roles en evidencias, reportes, calendario y seguridad a 390 y 1.440 píxeles, más autorización del historial por rol. Filtros, detalles y CSV también sin JavaScript; pantalla con detalles entre 320 y 1.440. Sin errores JavaScript, infracciones CSP ni desbordamientos en las comprobaciones realizadas.
- La actualización canónica se ejecutó desde `/tmp`: comprobaciones correctas, ninguna migración pendiente y estáticos recopilados. Se comprobó el acceso Python histórico, la ausencia de operaciones al importarlo, `--help` desde otra carpeta y la detención tras el primer fallo simulado. El acceso PowerShell se revisó por código; no se ejecutó en Windows.
- Con cuarenta eventos ficticios, la página realizó siete consultas y el CSV cuatro; solo una consulta del CSV obtuvo los eventos. Son medidas locales, sin garantía de latencia o capacidad de producción. Las regresiones de 1.200 usuarios y 12.000 evidencias se ejecutaron de nuevo en la batería completa.
- Catorce consultas SQL de diagnóstico de solo lectura ejecutadas correctamente. Ruff, formato de seis plantillas, sintaxis JavaScript, producción, estáticos y comprobación de migraciones correctos. Tras centralizar la paginación se repitieron la batería completa y la revisión de navegador. Sin nuevas dependencias ni cambios de esquema.

Cada ejecución de navegador utilizó dos cuentas y cuarenta eventos ficticios, retirados con sus registros temporales de acceso y sesiones. Permanecen las seis cuentas, una evidencia con su movimiento, dos plazos y ocho avisos. Las capturas muestran datos ficticios. La aplicación y el trabajador mantienen la captura local de correo; este bloque no valida el acceso real a Gmail.

## Bandeja interactiva y reloj de Colombia — 13 de noviembre de 2026

- Se reprodujo en una base aislada que un tipo de filtro inexistente se ignoraba al marcar resultados y permitía cambiar avisos ajenos a esa consulta pretendida. La regresión ahora pasa: los filtros de bandeja se validan también antes de la actualización filtrada, sin ampliar el alcance de la cuenta ni de la operación.
- 322 pruebas con MySQL (16 adicionales): filtros inválidos, días completos de Colombia, años admitidos, alcance desconocido, selección de otros propietarios, operaciones atómicas, CSRF, protocolo JSON explícito, retorno nativo, primera fecha de lectura y ausencia de mensajes diferidos al responder JSON. Una regresión verifica 250 avisos actualizados con un solo `UPDATE`. El reloj inicial se prueba alrededor de medianoche, con otra zona activa en el servidor.
- 120 comprobaciones de Chromium: 34 de bandeja, cinco de fallos y concurrencia de lectura, 23 del reloj y 58 regresiones de navegación y protección de ediciones. Se comprobaron los seis roles en móvil/escritorio, formularios sin JavaScript, filtros diarios, selección y todas las páginas, actualización inmediata de la campana y conservación de preferencias editadas. Un envío repetido durante una petición se bloquea; una respuesta tardía conserva el filtro nuevo y una búsqueda en pausa o en curso mantiene texto y foco.
- Los fallos de red se simulan en el navegador: una respuesta de POST retenida después de guardar caduca a los quince segundos, sin reenvío automático; consultar recupera el estado confirmado. Un fallo al recargar resultados se reintenta con GET, conservando el POST único. Una sesión cerrada vuelve al ingreso. Se repitieron además las regresiones de observaciones pendientes, Atrás/Adelante, respuestas fuera de orden, fragmentos incompletos y consultas sin respuesta. Sin errores JavaScript ni infracciones CSP en las comprobaciones completadas.
- El reloj conserva hora y fecha de Bogotá desde navegadores configurados en Tokio, Los Ángeles y Madrid. Se verificaron el cambio de día, la pausa al ocultar la pestaña, la recuperación, el funcionamiento sin conexión, el reloj único tras filtrar y la referencia inicial sin JavaScript. Avanzar los segundos no produjo peticiones de red. El pie se comprobó entre 320 y 1.440 píxeles, en el flujo del documento, sin superponerse al contenido. Se acotó el ancho de los gráficos para evitar desbordamientos al cambiar el tamaño de la ventana.
- Con los datos ficticios, la bandeja completa realizó ocho consultas y el fragmento siete; una operación filtrada sin coincidencias realizó cuatro consultas, incluido un único `UPDATE`. Son medidas locales, sin garantía de latencia o capacidad de producción. Las pruebas anteriores con 1.200 usuarios y 12.000 evidencias se volvieron a ejecutar en la batería completa.
- Ruff, cuatro plantillas, sintaxis de los cuatro controladores JavaScript modificados o añadidos, producción, estáticos y comprobación de migraciones correctos. No se añadieron tablas, migraciones ni dependencias. El reloj actualiza el navegador y no añade consultas periódicas a MySQL.

Se retiraron las cuentas, avisos, grupo, evidencias, plazo y publicación ficticios de las dos cohortes, junto con sus movimientos, registros temporales de acceso y sesiones. Se conservaron seis cuentas, una evidencia con su movimiento, dos plazos y ocho avisos. Las capturas contienen datos ficticios; el correo permanece en captura local y este bloque no valida Gmail real.

## Permisos mínimos de MySQL y consultas administrativas — 13 de noviembre de 2026

- Se comprobó que la cuenta de ejecución anterior podía modificar tablas y que la conexión local anterior no utilizaba TLS. En el entorno de revisión se separaron cuentas de ejecución, migraciones y pruebas, con contraseñas distintas. La cuenta web conserva únicamente `SELECT`, `INSERT`, `UPDATE` y `DELETE` en el esquema real; las otras dos tienen DDL acotado a su esquema. Se retiró el permiso histórico de la cuenta web sobre la base de pruebas. Los tres perfiles exigen SSL y no tienen roles.
- Se completaron 28 comprobaciones reales en esquemas y cuentas temporales: CRUD permitido, DDL y concesión de privilegios rechazados para ejecución, migraciones limitadas, pruebas sin acceso a la base real, consultas entre esquemas rechazadas, parámetros tratados como datos, sentencias encadenadas rechazadas y conexiones sin TLS rechazadas. Se probaron nombres de bases parecidos para verificar que los guiones bajos no amplíen el alcance. El servidor comprobado tenía `partial_revokes` desactivado; el generador contempla también su activación y se prueba esa selección por código, sin cambiar la configuración global del servidor de revisión.
- Se comprobó TLS cifrado con el cliente MySQL instalado y el rechazo de una CA ajena. El cliente MariaDB 3.4.9 acepta un certificado de CA válida al conectarse por IP sin verificar su nombre; por ello `VERIFY_IDENTITY` exige ahora un nombre DNS, además de una CA existente. Con DNS se verificó el rechazo de un nombre ajeno al certificado. La instalación local utiliza `REQUIRED`: cifra sin afirmar validación de identidad.
- 346 pruebas de Django con MySQL, 24 adicionales: perfiles sin privilegios globales, nombres y claves inválidos, cuentas compartidas, preflight de dedicación, escapes de credenciales y comodines, opciones TLS, IP abreviadas, concesiones desconocidas, roles, permisos globales, cargas locales, modo estricto, claves foráneas, motores, error de conexión y autorización del diagnóstico. Se prueba también que el historial y los miembros recientes no carguen hashes de contraseñas ni correo innecesario. La exportación de 256 eventos usa una consulta y mantiene la identidad pública de sus autores.
- La página de diagnóstico utiliza únicamente metadatos, requiere administrador o superusuario, deshabilita caché y rechaza POST. Tiene un solo acceso desde Permisos, actualización explícita y presentación de solo lectura. Se completaron 64 comprobaciones de Chromium con los seis roles, los paneles principales, administración nativa, cuatro anchuras de pantalla, el reloj único y la consulta sin JavaScript. Sin errores JavaScript ni desbordamientos en las comprobaciones completadas.
- Configuración de Compose validada con las credenciales de migraciones y pruebas fuera de web y trabajador; tarea de migración previa obligatoria y perfil de pruebas independiente. Se retiró la migración automática del arranque web y el antiguo SQL que concedía DDL a la cuenta web. Las cuentas se preparan mediante la herramienta del operador, no desde una vista de Django. No se añadieron tablas ni migraciones.
- Respaldo comprimido privado restaurado correctamente en una base independiente, con seis cuentas, una evidencia, su movimiento, dos plazos y ocho avisos. Un fallo de respaldo simulado no dejó SQL ni archivos incompletos. La comparación de los datos antes y después de aplicar y repetir los perfiles conservó esos registros. Las cuentas y bases temporales de aislamiento y restauración se retiraron; las sesiones y auditoría de los accesos de revisión pueden crecer.
- Versiones consultadas en PyPI: Gunicorn actualizado de 27.0.0 a 27.0.1 y Ruff de 0.17.4 a 0.17.5; servidor local reiniciado y disponible. Django 5.2.19 se mantiene en la última versión de su línea LTS comprobada y mysqlclient 2.3.1 ya está actualizado. `pip check`, Ruff, producción, migraciones, estáticos y auditoría de dependencias correctos; no se detectaron vulnerabilidades conocidas en los requisitos de ejecución consultados.

Las regresiones de escala se ejecutaron de nuevo: directorio y evidencias conservan nueve consultas, reportes diez y CSV de 12.000 evidencias cinco. Son verificaciones locales, sin garantía de latencia de producción. Las capturas muestran las cuentas ficticias de revisión y el correo sigue capturado en Mailpit.

## Recuperación progresiva e índices de solicitudes — 13 de noviembre de 2026

- Se reprodujo que un formulario nativo de recuperación devolvía JSON sin avanzar a la página siguiente. Ahora los tres pasos funcionan también sin JavaScript. La negociación conserva JSON para los clientes históricos y para `Accept: application/json`; una navegación que prefiera HTML obtiene formularios con errores y redirecciones. No cambian las rutas existentes ni los controles de CSRF, caducidad, cinco intentos y prueba ligada a la sesión.
- 365 pruebas de Django con MySQL, 19 adicionales: negociación y comodines de `Accept`, flujo HTML completo, respuesta genérica para cuentas ausentes, escape del correo, ausencia de PIN y contraseñas reflejados, PIN ASCII, bloqueo de intentos, caducidad, nueva solicitud, protección entre sesiones, corrección de contraseñas inválidas, no-store, CSRF, límites y fallo de caché. Se comprueban también continuación tras volver a un PIN verificado y visibilidad de la cuenta solo para la sesión autorizada. Dos sesiones concurrentes, una HTML y otra JSON, producen una sola verificación válida.
- 65 comprobaciones de Chromium: tres pasos a 320, 390, 768 y 1.440 píxeles; recuperación y acceso completos con y sin JavaScript; errores con foco y campos de contraseña vacíos en la respuesta nativa. Se conservan el correo en sesión, un solo controlador y URLs sin datos del formulario. El PIN pegado admite separadores y ceros iniciales, sin envío automático. El contador pausa en segundo plano y no anuncia cada segundo; el servidor rechazó un PIN caducado aunque el contador todavía mostrara tiempo. Una comprobación adicional de interfaz aislada confirmó que vaciar una contraseña visible también restablece el medidor y la validación de confirmación, sin un POST real.
- Se retuvo el cuerpo de la respuesta después de confirmar en MySQL cada uno de los tres POST. La espera terminó a los quince segundos; un segundo envío programático quedó bloqueado y la acción de comprobación utilizó GET. Se pudo continuar tras verificar y comprobar el nuevo acceso tras cambiar la contraseña. Los campos secretos se vaciaron incluso con la contraseña visible. La pérdida completa de cookie o sesión puede requerir un PIN nuevo, según se explica en operación.
- Se probaron `Retry-After` en segundos y fecha HTTP, desconexión sin envío ni pérdida de correo, reconexión sin envío automático, respuestas HTML inesperadas, JSON nulo o incompleto, mensajes vacíos, servicio 503, texto HTML dentro de un error JSON y un destino de redirección ajeno al sitio. Ninguno se interpretó como una confirmación indebida. Cuando el controlador no cargó, funcionó el formulario nativo; restaurar su página POST desde el historial consultó el formulario GET sin repetir el envío.
- La edición de observaciones conservó guardado, actualización de versión y contenido después de separar `recovery.js` del controlador general. Los seis roles volvieron a comprobarse en evidencias y bandeja a 390 y 1.440 píxeles, con un reloj único y sin cargar el controlador de recuperación. Sin errores JavaScript, infracciones CSP ni desbordamientos en las comprobaciones completadas.
- Se verificaron dos índices redundantes en `cuentas_passwordresettoken`. La migración `cuentas.0008` retira el índice no único del hash y el índice simple de caducidad, conserva la unicidad y el compuesto de caducidad/uso, y añade usuario/uso/fecha descendente. Con 8.000 solicitudes históricas, `EXPLAIN FORMAT=JSON` eligió el índice nuevo y eliminó la ordenación adicional: en la batería completa, la estimación pasó de 7.947 filas a una. La comparación anterior utiliza `IGNORE INDEX` únicamente en la prueba; son estimaciones del optimizador, no una medición de lecturas físicas ni garantía de latencia.
- Se respaldó MySQL antes de aplicar la migración real mediante la cuenta de migraciones. Se verificaron los índices resultantes, la unicidad del hash, las solicitudes conservadas y los cuatro controles del diagnóstico SQL. Las regresiones de 1.200 usuarios y 12.000 evidencias mantienen nueve consultas en directorio/evidencias, diez en reportes y cinco en el CSV completo.

Se retiraron las cuatro cuentas ficticias, su evidencia, movimientos, avisos, solicitudes y sesiones de prueba. Permanecen las seis cuentas originales, una evidencia con su movimiento, dos plazos y ocho avisos; sus datos se compararon con la referencia anterior, excluyendo la fecha de último acceso. Las capturas y correos de prueba contienen datos ficticios. La auditoría de accesos puede crecer y este bloque no valida entrega real de Gmail.

## Directorio administrativo y consultas por lotes — 13 de noviembre de 2026

- Se reprodujo que guardar una operación de cuentas perdía búsqueda, estado y página. Las redirecciones ahora conservan los filtros válidos y la página mediante una ruta interna fija, incluso ante contraseña incorrecta; se descartan destinos y parámetros ajenos. El acceso histórico al directorio se conserva.
- 385 pruebas de Django con MySQL, 20 adicionales: filtros compartidos, permisos por rol, superusuario, personal sin rol, permiso nativo insuficiente, revocación, CSV de todas las páginas, filtros inválidos, Unicode y fórmulas, fechas explícitas de Colombia, ausencia de secretos, auditoría de solicitud sin búsqueda, GET/HEAD/POST y representación parcial. La consulta de la página obtiene cuentas y grupos en dos consultas y no carga hashes de contraseña.
- Una prueba real con el servicio anterior produjo 103 consultas `SELECT` para comparar los roles de 100 cuentas sin cambios; la precarga conjunta reduce ese caso a cuatro. Se mantienen bloqueo transaccional, cuentas protegidas, validación completa, auditoría de cambios y límite de 100 cuentas. No es una medida del coste de 100 cambios efectivos ni una garantía de latencia.
- El CSV de 1.200 cuentas se obtuvo con siete consultas: un máximo inicial y tres lotes de cuentas/grupos. Los `SELECT` de cuentas usan `LIMIT 500`, sin `OFFSET` ni hashes. Una nueva cuenta con identificador superior al corte no aparece en los lotes restantes. El archivo admite cambios concurrentes en los datos existentes y no representa una instantánea transaccional global. Las regresiones previas de 1.200 usuarios y 12.000 evidencias también pasaron en la batería completa.
- 46 comprobaciones de Chromium: descarga real de los 56 resultados de tres páginas, coincidencia de búsqueda/estado/rol, actualización parcial del enlace, UTF-8, orden estable, edición pendiente conservada al descargar, guardado de roles, desactivación desde la segunda página y rechazo de contraseña incorrecta con contexto conservado. Descarga y guardado con teclado también sin JavaScript. Seis roles en evidencias y bandeja a 390 y 1.440 píxeles, permisos de descarga y directorio entre 320 y 1.440. Sin errores JavaScript, infracciones CSP ni desbordamientos en las comprobaciones completadas.
- Ruff, formato de la plantilla modificada, comprobación de migraciones, configuración de producción, cuatro controles del diagnóstico SQL, estáticos y auditoría de dependencias correctos. Tras el ajuste de nombres de campos se repitieron las 20 pruebas específicas. No hay migraciones, tablas ni dependencias nuevas.

Se retiraron las 57 cuentas ficticias y sus datos relacionados, junto con catorce sesiones de prueba. Permanecen seis cuentas, una evidencia con su movimiento, dos plazos y ocho avisos; se verificaron por hash, excluyendo la fecha de último acceso. Las capturas contienen datos ficticios. La auditoría de accesos puede crecer; el correo permanece en captura local y no se validó entrega real de Gmail en este bloque.
