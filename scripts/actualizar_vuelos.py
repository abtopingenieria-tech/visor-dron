"""Agrega o reemplaza vuelos en vuelos.json y quita los vuelos de ejemplo.
Uso por consola: python3 scripts/actualizar_vuelos.py FECHA NOMBRE URL"""
import json, re, sys

ARCHIVO = "vuelos.json"


def leer():
    with open(ARCHIVO, encoding="utf-8") as f:
        return json.load(f)


def fechas_reales():
    return {v["fecha"] for v in leer().get("vuelos", []) if not v["url"].startswith("ejemplo/")}


def guardar(cfg):
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")


def poner_titulo_si_falta(titulo, por_defecto="Visor de Avance Dron"):
    """Usa `titulo` como título del visor solo si sigue el título genérico."""
    cfg = leer()
    if titulo and cfg.get("titulo", por_defecto) == por_defecto:
        cfg["titulo"] = titulo
        guardar(cfg)


def agregar(fecha, nombre, url):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
        raise ValueError(f"Fecha inválida: {fecha!r}. Usa el formato AAAA-MM-DD, por ejemplo 2026-10-21.")
    cfg = leer()
    vuelos = [v for v in cfg.get("vuelos", []) if not v["url"].startswith("ejemplo/") and v["fecha"] != fecha]
    vuelos.append({"fecha": fecha, "nombre": (nombre or "").strip(), "url": url})
    cfg["vuelos"] = sorted(vuelos, key=lambda v: v["fecha"])
    guardar(cfg)
    return len(cfg["vuelos"])


if __name__ == "__main__":
    try:
        n = agregar(sys.argv[1], sys.argv[2], sys.argv[3])
    except ValueError as e:
        sys.exit(str(e))
    print(f"vuelos.json: {n} vuelo(s)")
