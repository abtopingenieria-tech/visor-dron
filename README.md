# Visor de Avance Dron

Sitio web estático que muestra ortomosaicos de dron de distintas fechas sobre un mapa y permite compararlos
(deslizador, lado a lado o transparencia). Cualquier persona con el link puede verlo; no necesita cuenta.

- `index.html`: el visor. No hay que tocarlo.
- `vuelos.json`: la lista de vuelos. Es lo único que se edita para agregar una fecha.

## Vuelos de ejemplo

La carpeta `ejemplo/` trae 3 ortomosaicos simulados para ver el visor funcionando. Cuando cargues tus vuelos, bórralos de `vuelos.json` (y si quieres, borra la carpeta).

## Agregar un vuelo nuevo

### 1. Exportar el ortomosaico como GeoTIFF optimizado (COG)

Los navegadores no leen ECW. Convierte cada ortomosaico en QGIS:

1. Abre el `.ecw` o `.tif` en QGIS.
2. Clic derecho en la capa → **Exportar → Guardar como…**
3. Formato: **GeoTIFF**. SRC: el del proyecto (UTM WGS84 o SIRGAS UTM sirven tal cual).
4. En **Opciones de creación**, elige el perfil o escribe: `COMPRESS=JPEG`, `QUALITY=85`, y marca **Crear como COG**
   (o en formato elige directamente **Cloud Optimized GeoTIFF** si aparece).
5. Si el ortomosaico no trae transparencia, define **NoData = 0** (o agrega banda alfa) para que el borde no se vea negro.
6. Nombra el archivo con la fecha del vuelo, por ejemplo `2026-10-21.tif`.

Con GDAL por consola: `gdal_translate entrada.ecw 2026-10-21.tif -of COG -co COMPRESS=JPEG -co QUALITY=85 -a_nodata 0`

**Ojo:** `index.html` solo funciona publicado en un sitio web (GitHub Pages u otro). Si lo abres directo desde el computador o desde la vista previa de la app, se queda en "Cargando vuelos…".

### 2. Subirlo a Cloudflare R2

1. En el panel de Cloudflare → **R2** → tu bucket → **Upload** y sube el `.tif`.
2. Copia su URL pública (`https://pub-xxxx.r2.dev/2026-10-21.tif`).

Configuración única del bucket (solo la primera vez):
- **Settings → Public access**: activar el dominio `r2.dev` (o un dominio propio).
- **Settings → CORS policy**:
  ```json
  [{ "AllowedOrigins": ["*"], "AllowedMethods": ["GET", "HEAD"], "AllowedHeaders": ["Range"], "ExposeHeaders": ["Content-Range", "Content-Length", "Accept-Ranges"] }]
  ```

### 3. Agregarlo a `vuelos.json`

Añade una línea con la fecha (AAAA-MM-DD), un nombre y la URL. El visor ordena por fecha y por defecto compara los dos últimos vuelos.

## Compartir

Envía el link del sitio. El botón **Copiar link** incluye las fechas y el modo elegidos, así quien lo abre ve la misma comparación.

## Sistemas de coordenadas aceptados

UTM WGS84 (EPSG:326xx y 327xx), SIRGAS 2000 UTM sur (EPSG:31977 a 31985) y Web Mercator (EPSG:3857).
Si tu ortomosaico usa otro, reprojéctalo a uno de estos al exportar.
