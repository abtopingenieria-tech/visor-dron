"""Descarga, convierte, sube a R2 y agrega a vuelos.json uno o varios ortomosaicos.

Lee de variables de entorno: LINK, FECHA (opcional), NOMBRE (opcional), RES (opcional),
R2_BUCKET, R2_PUBLIC_URL, R2_ACCOUNT_ID (+ credenciales AWS_* para la CLI de aws).

- Link a una carpeta de Google Drive: procesa todos los .tif de la carpeta. La fecha y el nombre
  salen del nombre de cada archivo, por ejemplo "2026-10-21 Losa piso 1.tif". Las fechas que ya
  están en el visor se saltan.
- Link a un archivo: usa FECHA/NOMBRE si vienen; si no, los saca del nombre del archivo.
- Archivos .dxf (sueltos o en la carpeta): se publican como plano de diseño para superponer.
  El DXF no trae sistema de coordenadas: se usa EPSG si viene, o el mismo de los ortomosaicos.
"""
import gzip, json, os, re, shutil, subprocess, sys, time, unicodedata, urllib.parse
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import actualizar_vuelos  # noqa: E402

TRABAJO = Path("trabajo")
EXT = (".tif", ".tiff")
EXT_PLANO = (".dxf",)
# Formatos de fecha aceptados en el nombre del archivo, en orden de prioridad:
#   2026-10-21 / 20261021 (año-mes-día)  ·  21-10-2026 / 21-10-26 (formato chileno día-mes-año)
SEP = r"[-_. /]"
RE_FECHAS = [
    (re.compile(rf"(?<!\d)(20\d{{2}}){SEP}?(\d{{2}}){SEP}?(\d{{2}})(?!\d)"), ("a", "m", "d")),
    (re.compile(rf"(?<!\d)(\d{{1,2}}){SEP}(\d{{1,2}}){SEP}(20\d{{2}})(?!\d)"), ("d", "m", "a")),
    (re.compile(rf"(?<!\d)(\d{{1,2}}){SEP}(\d{{1,2}}){SEP}(\d{{2}})(?!\d)"), ("d", "m", "a2")),
]
CONECTORES = {"al", "del", "de", "el", "la", "vuelo", "fecha"}

env = os.environ.get
LINK, FECHA, NOMBRE, RES = env("LINK", "").strip(), env("FECHA", "").strip(), env("NOMBRE", "").strip(), env("RES", "").strip()
EPSG = env("EPSG", "").strip().upper().removeprefix("EPSG:")
resumen = []


def anotar(linea):
    print(linea, flush=True)
    resumen.append(linea)


def desde_nombre(nombre_archivo):
    """'2026-10-21 Losa piso 1.tif' -> ('2026-10-21', 'Losa piso 1')
    'Ortofoto CFRD del 17-06-26.tif' -> ('2026-06-17', 'Ortofoto CFRD')"""
    base = Path(nombre_archivo).stem
    for patron, orden in RE_FECHAS:
        for m in patron.finditer(base):
            partes = dict(zip(orden, m.groups()))
            anio = int(partes["a"]) if "a" in partes else 2000 + int(partes["a2"])
            try:
                fecha = date(anio, int(partes["m"]), int(partes["d"])).isoformat()
            except ValueError:
                continue
            resto = [x.replace("_", " ").strip(" -.") for x in (base[:m.start()], base[m.end():])]
            palabras = " ".join(x for x in resto if x).split()
            while palabras and palabras[-1].lower() in CONECTORES:  # "... Escondida al" -> "... Escondida"
                palabras.pop()
            return fecha, " ".join(palabras)
    return None, base


def descargar_directo(url, destino):
    if "dropbox.com" in url:
        url = url.replace("dl=0", "dl=1")
        if "dl=1" not in url:
            url += ("&" if "?" in url else "?") + "dl=1"
    elif "box.com/s/" in url:
        url = url.replace("/s/", "/shared/static/")
    subprocess.run(["curl", "-fL", "--retry", "3", "-o", str(destino), url], check=True)


def es_geotiff(ruta):
    return subprocess.run(["gdalinfo", str(ruta)], capture_output=True).returncode == 0


def subir(local, clave, tipo, *extra):
    for intento in (1, 2, 3):  # R2 a veces rechaza una subida por partes; se reintenta
        r = subprocess.run(["aws", "s3", "cp", str(local), f"s3://{env('R2_BUCKET')}/{clave}",
                            "--endpoint-url", f"https://{env('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
                            "--content-type", tipo, "--only-show-errors", *extra])
        if r.returncode == 0:
            return f"{env('R2_PUBLIC_URL')}/{clave}"
        if intento == 3:
            raise RuntimeError("no se pudo subir a R2 después de 3 intentos")
        print(f"Reintentando subida ({intento})…", flush=True); time.sleep(10)


def epsg_de_vuelos():
    """El DXF no guarda sistema de coordenadas: se toma el del primer ortomosaico publicado."""
    for v in actualizar_vuelos.leer().get("vuelos", []):
        if v["url"].startswith("http"):
            r = subprocess.run(["gdalsrsinfo", "-o", "epsg", "/vsicurl/" + v["url"]], capture_output=True, text=True)
            m = re.search(r"EPSG:(\d+)", r.stdout)
            if m:
                return m.group(1)
    return None


def publicar_plano(archivo, nombre):
    epsg = EPSG or epsg_de_vuelos()
    if not epsg:
        raise RuntimeError("no sé en qué coordenadas está el DXF: escribe el EPSG en el formulario (por ejemplo 32719)")
    clave = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode().lower()).strip("-") or "plano"
    salida = TRABAJO / f"{clave}.geojson"
    r = subprocess.run(["ogr2ogr", "-f", "GeoJSON", str(salida), str(archivo), "-skipfailures",
                        "-s_srs", f"EPSG:{epsg}", "-t_srs", "EPSG:4326", "-dim", "XY",
                        "-sql", "SELECT Layer, Text FROM entities", "-nln", "plano",
                        "-lco", "COORDINATE_PRECISION=7", "-lco", "RFC7946=YES"], capture_output=True, text=True)
    if r.returncode != 0 or not salida.exists():
        raise RuntimeError("no se pudo leer el DXF: " + (r.stderr.strip().splitlines() or ["error desconocido"])[-1])
    datos = json.loads(salida.read_text(encoding="utf-8"))
    for ft in datos.get("features", []):  # solo los textos sueltos llevan etiqueta (no los nombres de achurado)
        props = ft.get("properties") or {}
        if (ft.get("geometry") or {}).get("type") != "Point" or not props.get("Text"):
            props.pop("Text", None)
    datos["features"] = [ft for ft in datos.get("features", []) if ft.get("geometry")]
    salida.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    n = len(datos["features"])
    if not n:
        raise RuntimeError("el DXF no tiene líneas ni textos en el espacio modelo")
    comprimido = TRABAJO / f"{clave}.geojson.gz"
    with open(salida, "rb") as a, gzip.open(comprimido, "wb", 9) as b:
        shutil.copyfileobj(a, b)
    # Se sube comprimido; el navegador lo descomprime solo gracias a Content-Encoding
    url = subir(comprimido, f"planos/{clave}.geojson", "application/geo+json", "--content-encoding", "gzip")
    actualizar_vuelos.agregar_plano(nombre, f"{url}?v={int(time.time())}")
    for p in (archivo, salida, comprimido):
        Path(p).unlink(missing_ok=True)
    anotar(f"- 📐 Plano {nombre} ({n} elementos, EPSG:{epsg})")


def nombre_plano(nombre_archivo):
    return NOMBRE or Path(nombre_archivo).stem.replace("_", " ").strip()


def publicar(archivo, fecha, nombre):
    salida = TRABAJO / f"{fecha}.tif"
    subprocess.run(["bash", "scripts/convertir.sh", str(archivo), str(salida), RES], check=True)
    actualizar_vuelos.agregar(fecha, nombre, subir(salida, f"{fecha}.tif", "image/tiff"))
    for p in (archivo, salida):
        Path(p).unlink(missing_ok=True)
    anotar(f"- ✅ {fecha} {('· ' + nombre) if nombre else ''}")


def main():
    import gdown
    TRABAJO.mkdir(exist_ok=True)
    errores = 0

    if "drive.google.com" in LINK and "/folders/" in LINK:
        archivos = gdown.download_folder(url=LINK, skip_download=True, quiet=True) or []
        anotar(f"Carpeta de Drive con {len(archivos)} archivo(s).")
        ya = actualizar_vuelos.fechas_reales()
        # Si todos los archivos se llaman igual salvo la fecha ("Ortofoto Obra X del 17-06-26"),
        # ese texto pasa a ser el título del visor y cada vuelo muestra solo su fecha
        nombres = {desde_nombre(Path(a.path).name)[1] for a in archivos
                   if Path(a.path).name.lower().endswith(EXT) and desde_nombre(Path(a.path).name)[0]}
        n_tif = sum(Path(a.path).name.lower().endswith(EXT) for a in archivos)
        comun = nombres.pop() if len(nombres) == 1 and n_tif > 1 else None
        if comun:
            actualizar_vuelos.poner_titulo_si_falta(comun)
        for a in sorted(archivos, key=lambda a: desde_nombre(Path(a.path).name)[0] or a.path):
            nombre_archivo = Path(a.path).name
            if nombre_archivo.lower().endswith(EXT_PLANO):
                try:
                    destino = TRABAJO / nombre_archivo
                    gdown.download(id=a.id, output=str(destino), quiet=True)
                    publicar_plano(destino, Path(nombre_archivo).stem.replace("_", " ").strip())
                except Exception as e:
                    anotar(f"- ❌ {nombre_archivo}: {e}")
                    errores += 1
                continue
            if not nombre_archivo.lower().endswith(EXT):
                anotar(f"- ⏭️ {nombre_archivo}: no es .tif (los .ecw se convierten antes con convertir.bat)")
                continue
            fecha, nombre = desde_nombre(nombre_archivo)
            if comun and nombre == comun:
                nombre = ""
            if not fecha:
                anotar(f"- ⚠️ {nombre_archivo}: no encontré una fecha válida en el nombre (usa 21-10-26, 21-10-2026 o 2026-10-21)")
                errores += 1
                continue
            if fecha in ya:
                anotar(f"- ⏭️ {fecha}: ya está en el visor, se salta")
                continue
            try:
                destino = TRABAJO / nombre_archivo
                gdown.download(id=a.id, output=str(destino), quiet=True)
                if not es_geotiff(destino):
                    raise RuntimeError("lo descargado no es un GeoTIFF")
                publicar(destino, fecha, nombre)
                ya.add(fecha)
            except Exception as e:  # sigue con los demás archivos
                anotar(f"- ❌ {nombre_archivo}: {e}")
                errores += 1
    else:
        if "drive.google.com" in LINK:
            ruta = gdown.download(url=LINK, output=str(TRABAJO) + "/", fuzzy=True, quiet=True)
            if not ruta:
                sys.exit("::error::No se pudo descargar desde Drive. Revisa que esté compartido como 'Cualquier persona con el enlace'.")
            destino = Path(ruta)
        else:
            destino = TRABAJO / (urllib.parse.unquote(Path(LINK.split("?")[0]).name) or "entrada.tif")
            descargar_directo(LINK, destino)
        if destino.suffix.lower() in EXT_PLANO:
            try:
                publicar_plano(destino, nombre_plano(destino.name))
            except Exception as e:
                sys.exit(f"::error::{e}")
        elif not es_geotiff(destino):
            sys.exit("::error::Lo descargado no es un GeoTIFF. Revisa que el link esté compartido como "
                     "'Cualquier persona con el enlace' y que el archivo sea .tif (ECW se convierte antes con convertir.bat).")
        else:
            f_archivo, n_archivo = desde_nombre(destino.name)
            fecha, nombre = FECHA or f_archivo, NOMBRE or n_archivo
            if not fecha:
                sys.exit("::error::Falta la fecha: escríbela en el formulario o ponla en el nombre del archivo (por ejemplo 21-10-26).")
            publicar(destino, fecha, nombre)

    with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a", encoding="utf-8") as f:
        f.write("### Resultado\n\n" + "\n".join(resumen) + "\n\nEl sitio se actualiza en 1 o 2 minutos.\n")
    if errores:
        sys.exit(f"::error::{errores} archivo(s) no se pudieron agregar; revisa el resumen.")


if __name__ == "__main__":
    main()
