#!/usr/bin/env bash
# Convierte un ortomosaico GeoTIFF a COG liviano (JPEG + máscara de transparencia).
# El borde vacío (negro o blanco puro, conectado al contorno de la imagen) se marca como
# transparente con `nearblack`, así en el visor se ve el mapa de fondo en vez de un recuadro.
# Uso: scripts/convertir.sh entrada.tif salida.tif [resolucion_en_metros]
# Con FORZAR=1 reconvierte aunque el archivo ya venga optimizado.
set -euo pipefail
entrada="$1"; salida="$2"; res="${3:-}"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT

info=$(gdalinfo -json "$entrada")
leer() { python3 -c "import json,sys; d=json.load(sys.stdin); $1" <<<"$info"; }
bandas=$(leer 'print(len(d["bands"]))')
tiene_crs=$(leer 'print("si" if d.get("coordinateSystem",{}).get("wkt") else "no")')
tipo=$(leer 'print(d["bands"][0]["type"])')
estructura=$(leer 'm=d.get("metadata",{}).get("IMAGE_STRUCTURE",{}); print(m.get("LAYOUT",""), m.get("COMPRESSION",""))')
mascara=$(leer 'print("si" if "PER_DATASET" in d["bands"][0].get("mask",{}).get("flags",[]) else "no")')

if [ "$tiene_crs" != "si" ]; then
  echo "::error::El archivo no está georreferenciado (no tiene sistema de coordenadas). Exporta el ortomosaico como GeoTIFF."
  exit 1
fi
if [ "$bandas" -lt 3 ]; then
  echo "::error::El archivo tiene $bandas banda(s); se esperaba un ortomosaico RGB (3 o 4 bandas)."
  exit 1
fi

# Si ya viene listo (COG JPEG con su máscara de borde) y sin cambio de resolución, se usa tal cual
if [ -z "${FORZAR:-}" ] && [ -z "$res" ] && [[ "$estructura" == COG*JPEG* ]] && [ "$mascara" = "si" ]; then
  echo "El archivo ya está optimizado ($estructura, con máscara); se sube sin reconvertir."
  cp "$entrada" "$salida"; ls -lh "$salida"; exit 0
fi

echo "Bandas: $bandas · tipo: $tipo · resolución: ${res:-original}"
# 1) Solo RGB (la banda 4, si existe, se reemplaza por la máscara de borde); 16 bits -> 8 bits
rgb=(-b 1 -b 2 -b 3)
if [ "$tipo" != "Byte" ]; then rgb+=(-ot Byte -scale); fi
gdal_translate -q -of VRT "${rgb[@]}" "$entrada" "$tmp/rgb.vrt"

# 2) Borde negro o blanco conectado al contorno -> máscara transparente (tolerancia 20 por la compresión)
nearblack -q -of GTiff -setmask -near 20 -color 0,0,0 -color 255,255,255 \
  -co TILED=YES -co COMPRESS=DEFLATE -co BIGTIFF=IF_SAFER -o "$tmp/borde.tif" "$tmp/rgb.vrt"

# 3) COG con JPEG; la máscara se copia sola
extra=()
if [ -n "$res" ]; then extra+=(-tr "$res" "$res" -r average); fi
gdal_translate "$tmp/borde.tif" "$salida" "${extra[@]}" -of COG \
  -co COMPRESS=JPEG -co QUALITY=85 -co NUM_THREADS=ALL_CPUS -co BIGTIFF=IF_SAFER
ls -lh "$entrada" "$salida"
