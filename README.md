# Visor de Avance Dron

Sitio web que muestra ortomosaicos de dron de distintas fechas sobre un mapa y permite recorrerlos
con una línea de tiempo o compararlos (deslizador, lado a lado o transparencia).
Cualquier persona con el link puede verlo: https://abtopingenieria-tech.github.io/visor-dron/

- `index.html`: el visor.
- `vuelos.json`: la lista de vuelos (se actualiza sola al agregar un vuelo).
- `.github/workflows/agregar-vuelo.yml`: convierte y publica un vuelo nuevo.
- `ejemplo/`: 3 vuelos simulados; desaparecen del visor al agregar el primer vuelo real.

## Agregar un vuelo (sin instalar nada)

1. Sube el ortomosaico **GeoTIFF** original a Google Drive (o Dropbox/Box) y compártelo como
   **"Cualquier persona con el enlace"**. Copia el link.
2. En GitHub entra a **Actions → Agregar vuelo → Run workflow** y completa:
   - **link**: el link compartido.
   - **fecha**: fecha del vuelo, `AAAA-MM-DD`.
   - **nombre**: algo corto, por ejemplo `Losa piso 1`.
   - **resolución** (opcional): por ejemplo `0.05` para bajar a 5 cm/px y achicar más el archivo.
3. Aprieta **Run workflow**. En unos minutos (más si el archivo pesa varios GB) aparece un ✓ verde y el vuelo
   ya está en el visor. Si aparece una ✗ roja, entra al run y lee el mensaje en rojo.

Qué hace: descarga el archivo, lo convierte a COG con compresión JPEG (10 a 30 veces más liviano, igual en pantalla),
lo sube a Cloudflare R2 y lo agrega a `vuelos.json`. Si repites una fecha, reemplaza ese vuelo.

**ECW:** no se puede convertir en la nube (es un formato con licencia). Exporta el ortomosaico como GeoTIFF desde tu
software de fotogrametría, o usa `convertir.bat` (abajo).

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

## Alternativa local: `convertir.bat`

Si prefieres convertir en tu computador (por ejemplo para archivos ECW), con QGIS instalado:
copia `convertir.bat` a la carpeta de tus ortomosaicos, abre **OSGeo4W Shell**, entra a esa carpeta
(`cd /d "D:\Vuelos\Obra"`) y escribe `convertir.bat`. Los archivos quedan en `web\`; súbelos al bucket
y agrégalos a `vuelos.json` a mano.

## Sistemas de coordenadas

UTM WGS84 (EPSG:326xx y 327xx), SIRGAS 2000 UTM sur (EPSG:31977 a 31985) y Web Mercator (EPSG:3857).

## Nota

`index.html` solo funciona publicado en un sitio web. Abierto directo desde el computador se queda en "Cargando vuelos…".
