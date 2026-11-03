@echo off
setlocal enabledelayedexpansion
title Convertir ortomosaicos para el Visor de Avance Dron
REM ------------------------------------------------------------------
REM Convierte los .ecw y .tif de ESTA carpeta a GeoTIFF livianos (COG JPEG)
REM listos para subir. Uso: copia este archivo a la carpeta de tus
REM ortomosaicos y hazle DOBLE CLIC. Requiere QGIS instalado (no hay que abrirlo).
REM
REM Para achicar aun mas, cambia RES a la resolucion en metros, ej: set RES=0.05
set RES=
set CALIDAD=85
REM ------------------------------------------------------------------

REM Busca la instalacion de QGIS / OSGeo4W para usar su GDAL (incluye lector ECW)
set "ENTORNO="
for /d %%D in ("C:\Program Files\QGIS*") do if exist "%%D\bin\o4w_env.bat" set "ENTORNO=%%D\bin\o4w_env.bat"
if not defined ENTORNO if exist "C:\OSGeo4W\bin\o4w_env.bat" set "ENTORNO=C:\OSGeo4W\bin\o4w_env.bat"
if not defined ENTORNO (
  echo No encontre QGIS instalado. Descargalo gratis desde https://qgis.org/download/ e intenta de nuevo.
  pause
  exit /b 1
)
call "%ENTORNO%" >nul

cd /d "%~dp0"
if not exist web mkdir web
set /a TOTAL=0

for %%F in (*.ecw *.tif *.tiff) do (
  set /a TOTAL+=1
  echo.
  echo === %%F ===
  set "MASCARA="
  gdalinfo "%%F" | findstr /b /c:"Band 4" >nul && set "MASCARA=-mask 4"
  set "REDUCIR="
  if not "%RES%"=="" set "REDUCIR=-tr %RES% %RES% -r average"
  gdal_translate "%%F" "web\%%~nF.tif" -b 1 -b 2 -b 3 !MASCARA! !REDUCIR! -of COG -co COMPRESS=JPEG -co QUALITY=%CALIDAD% -co NUM_THREADS=ALL_CPUS -co BIGTIFF=IF_SAFER
  if errorlevel 1 (echo   ERROR al convertir %%F) else (echo   Listo: web\%%~nF.tif)
)

echo.
if %TOTAL%==0 (echo No encontre archivos .ecw ni .tif en esta carpeta.) else (echo Terminado. Los archivos livianos estan en la carpeta "web".)
pause
