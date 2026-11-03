#!/usr/bin/env bash
# Convierte un ortomosaico GeoTIFF a COG liviano (JPEG + máscara de transparencia).
# Uso: scripts/convertir.sh entrada.tif salida.tif [resolucion_en_metros]
set -euo pipefail
entrada="$1"; salida="$2"; res="${3:-}"

info=$(gdalinfo -json "$entrada")
bandas=$(python3 -c 'import json,sys; print(len(json.load(sys.stdin)["bands"]))' <<<"$info")
tiene_crs=$(python3 -c 'import json,sys; d=json.load(sys.stdin); print("si" if d.get("coordinateSystem",{}).get("wkt") else "no")' <<<"$info")
tipo=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["bands"][0]["type"])' <<<"$info")

if [ "$tiene_crs" != "si" ]; then
  echo "::error::El archivo no está georreferenciado (no tiene sistema de coordenadas). Exporta el ortomosaico como GeoTIFF."
  exit 1
fi
if [ "$bandas" -lt 3 ]; then
  echo "::error::El archivo tiene $bandas banda(s); se esperaba un ortomosaico RGB (3 o 4 bandas)."
  exit 1
fi

args=(-b 1 -b 2 -b 3)
# La cuarta banda es la transparencia: pasa a ser la máscara del COG
if [ "$bandas" -ge 4 ]; then args+=(-mask 4); fi
# Ortomosaicos de 16 bits: se escalan a 8 bits para poder comprimir en JPEG
if [ "$tipo" != "Byte" ]; then args+=(-ot Byte -scale); fi
if [ -n "$res" ]; then args+=(-tr "$res" "$res" -r average); fi

echo "Bandas: $bandas · tipo: $tipo · resolución: ${res:-original}"
gdal_translate "$entrada" "$salida" "${args[@]}" -of COG \
  -co COMPRESS=JPEG -co QUALITY=85 -co NUM_THREADS=ALL_CPUS -co BIGTIFF=IF_SAFER
ls -lh "$entrada" "$salida"
