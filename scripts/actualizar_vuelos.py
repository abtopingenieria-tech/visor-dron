"""Agrega o reemplaza un vuelo en vuelos.json y quita los vuelos de ejemplo.
Uso: python3 scripts/actualizar_vuelos.py FECHA NOMBRE URL"""
import json, re, sys

fecha, nombre, url = sys.argv[1], sys.argv[2].strip(), sys.argv[3]
if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
    sys.exit(f"Fecha inválida: {fecha!r}. Usa el formato AAAA-MM-DD, por ejemplo 2026-10-21.")

with open("vuelos.json", encoding="utf-8") as f:
    cfg = json.load(f)

vuelos = [v for v in cfg.get("vuelos", []) if not v["url"].startswith("ejemplo/") and v["fecha"] != fecha]
vuelos.append({"fecha": fecha, "nombre": nombre, "url": url})
cfg["vuelos"] = sorted(vuelos, key=lambda v: v["fecha"])

with open("vuelos.json", "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"vuelos.json: {len(cfg['vuelos'])} vuelo(s)")
