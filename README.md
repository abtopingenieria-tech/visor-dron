# Visor de Avance Dron

Sitio web que muestra ortomosaicos de dron de distintas fechas sobre un mapa y permite recorrerlos
con una línea de tiempo o compararlos (deslizador, lado a lado o transparencia).
Cualquier persona con el link puede verlo: https://abtopingenieria-tech.github.io/visor-dron/

- `index.html`: el visor.
- `vuelos.json`: la lista de vuelos (se actualiza sola al agregar un vuelo).
- `.github/workflows/agregar-vuelo.yml`: convierte y publica vuelos nuevos (uno o una carpeta completa).
- `ejemplo/`: 3 vuelos simulados; desaparecen del visor al agregar el primer vuelo real.

## Agregar vuelos (sin instalar nada)

**El nombre de cada archivo debe incluir su fecha**: sirve `Ortofoto Obra del 21-10-26.tif` (día-mes-año), `21-10-2026` o `2026-10-21`.
El resto del nombre se muestra en la línea de tiempo. Si todos los archivos se llaman igual salvo la fecha, ese texto pasa a ser el título del visor.

1. Sube los `.tif` a una carpeta de Google Drive y comparte **la carpeta** (o un solo archivo) como
   **"Cualquier persona con el enlace"**. Copia el link.
2. En GitHub entra a **Actions → Agregar vuelos → Run workflow**, pega el link en **link** y aprieta **Run workflow**.
   Los demás campos son opcionales: fecha y nombre solo sirven al subir un archivo suelto que no los tenga en su nombre;
   **resolución** (por ejemplo `0.05`) baja el detalle para achicar más.
3. Espera el ✓ verde (varios minutos por archivo grande) y recarga el visor. El resumen del run muestra qué se agregó.

Con una carpeta se procesan todos los `.tif` de una vez. Las fechas que ya están en el visor se saltan, así que puedes
dejar todos los vuelos en la misma carpeta e ir agregando nuevos. Si repites la fecha de un archivo suelto, reemplaza ese vuelo.

Qué hace: descarga cada archivo, lo convierte a COG con compresión JPEG (10 a 30 veces más liviano, igual en pantalla),
lo sube a Cloudflare R2 y lo agrega a `vuelos.json`.

**ECW:** no se puede convertir en la nube (es un formato con licencia). Conviértelo antes con `convertir.bat` (abajo).

## Configuración única: claves de Cloudflare R2

La acción necesita permiso para subir archivos al bucket `visor-dron`.

1. En Cloudflare → **R2 object storage** → **Manage API tokens** (o "API Tokens" en la página de R2) →
   **Create Account API token**.
   - Permisos: **Object Read & Write**.
   - Bucket: solo `visor-dron`.
2. Al crearlo, Cloudflare muestra **Access Key ID**, **Secret Access Key** y el **Account ID**
   (también aparece en la URL del panel: `dash.cloudflare.com/<ACCOUNT_ID>/r2`). Cópialos.
3. En GitHub → **Settings → Secrets and variables → Actions → New repository secret**, crea tres secretos:
   `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`.

Configuración del bucket (ya hecha): acceso público por `r2.dev` y política CORS:
```json
[{ "AllowedOrigins": ["*"], "AllowedMethods": ["GET", "HEAD"], "AllowedHeaders": ["Range"], "ExposeHeaders": ["Content-Range", "Content-Length", "Accept-Ranges"] }]
```

## Cuánto cabe

El plan gratis de R2 trae 10 GB. Un ortomosaico de 3 GB sin comprimir queda en unos 150 a 300 MB, o sea 30 a 60 vuelos.
Pasado eso, R2 cobra US$ 0,015 por GB al mes (100 GB ≈ US$ 1,5 al mes).

## Si tus ortomosaicos están en ECW: `convertir.bat`

El ECW no se puede abrir en la nube, así que se convierte en tu computador (Windows):

1. Instala QGIS una vez desde https://qgis.org/download/ (no hace falta abrirlo nunca; trae el lector de ECW).
2. Descarga [`convertir.bat`](convertir.bat) (botón ↓ "Download raw file") y cópialo a la carpeta donde están los `.ecw`.
3. Hazle **doble clic**. Convierte todos los `.ecw` y `.tif` de esa carpeta y deja los livianos en la subcarpeta `web`.
4. Renombra los archivos de `web` con su fecha (`2026-10-21 Losa piso 1.tif`), súbelos a tu carpeta de Drive y usa la
   acción **Agregar vuelos** (detecta que ya vienen optimizados y no los vuelve a comprimir).

## Sistemas de coordenadas

UTM WGS84 (EPSG:326xx y 327xx), SIRGAS 2000 UTM sur (EPSG:31977 a 31985) y Web Mercator (EPSG:3857).

## Nota

`index.html` solo funciona publicado en un sitio web. Abierto directo desde el computador se queda en "Cargando vuelos…".
