# Visor de Avance Dron

Sitio web estático que muestra ortomosaicos de dron de distintas fechas sobre un mapa y permite compararlos
(deslizador, lado a lado o transparencia). Cualquier persona con el link puede verlo; no necesita cuenta.

- `index.html`: el visor. No hay que tocarlo.
- `vuelos.json`: la lista de vuelos. Es lo único que se edita para agregar una fecha.

## Vuelos de ejemplo

La carpeta `ejemplo/` trae 3 ortomosaicos simulados para ver el visor funcionando. Cuando cargues tus vuelos, bórralos de `vuelos.json` (y si quieres, borra la carpeta).

## Agregar un vuelo nuevo

### 1. Convertir el ortomosaico a GeoTIFF optimizado (COG)

Los TIFF que exporta el software de fotogrametría suelen venir sin comprimir y pesan varios GB.
Convertidos a COG con compresión JPEG quedan entre 10 y 30 veces más livianos, sin diferencia visible en pantalla.
Los navegadores tampoco leen ECW, así que los ECW también pasan por este paso.

**Forma fácil (Windows, con QGIS instalado):**
1. Copia `convertir.bat` a la carpeta donde están tus `.tif` o `.ecw`.
2. Abre **OSGeo4W Shell** (menú inicio, viene con QGIS) y entra a esa carpeta con `cd "C:\ruta\a\la\carpeta"`.
3. Escribe `convertir.bat`. Los archivos listos quedan en la subcarpeta `web`.
4. Nombra cada archivo con la fecha del vuelo, por ejemplo `2026-10-21.tif`.

Para archivos aún más livianos, edita `convertir.bat` y pon `set RES=0.05` (5 cm/px). Para ver el avance de una obra suele bastar.

**Comando suelto:**
`gdal_translate entrada.tif salida.tif -b 1 -b 2 -b 3 -mask 4 -of COG -co COMPRESS=JPEG -co QUALITY=85`
(la banda 4 es la transparencia; si tu archivo solo tiene 3 bandas, quita `-mask 4`).

**Cuánto cabe:** el plan gratis de R2 trae 10 GB. Un ortomosaico de 3 GB sin comprimir queda en 150 a 300 MB, o sea unos 30 a 60 vuelos. Pasado eso, R2 cobra US$ 0,015 por GB al mes (100 GB ≈ US$ 1,5 al mes).

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

## Nota

`index.html` solo funciona publicado en un sitio web (GitHub Pages). Si lo abres directo desde el computador se queda en "Cargando vuelos…".
