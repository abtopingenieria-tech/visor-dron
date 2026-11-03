@echo off
REM Convierte ortomosaicos (.tif o .ecw) a GeoTIFF optimizado para el visor (COG con JPEG).
REM Uso: abre "OSGeo4W Shell" (viene con QGIS), entra a la carpeta de tus ortomosaicos y escribe:
REM   convertir.bat
REM Crea una carpeta "web" con los archivos listos para subir a Cloudflare R2.
REM Para bajar la resolución (archivos aún más livianos), cambia RES a por ejemplo 0.05 (5 cm/px).

set RES=
set CALIDAD=85
if not exist web mkdir web

for %%F in (*.tif *.ecw) do (
  echo Convirtiendo %%F ...
  if "%RES%"=="" (
    gdal_translate "%%F" "web\%%~nF.tif" -b 1 -b 2 -b 3 -mask 4 -of COG -co COMPRESS=JPEG -co QUALITY=%CALIDAD% -co NUM_THREADS=ALL_CPUS
  ) else (
    gdal_translate "%%F" "web\%%~nF.tif" -b 1 -b 2 -b 3 -mask 4 -tr %RES% %RES% -r average -of COG -co COMPRESS=JPEG -co QUALITY=%CALIDAD% -co NUM_THREADS=ALL_CPUS
  )
)
echo Listo. Revisa la carpeta "web".
