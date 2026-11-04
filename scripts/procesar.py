"""Descarga, convierte, sube a R2 y agrega a vuelos.json uno o varios ortomosaicos.

Lee de variables de entorno: LINK, FECHA (opcional), NOMBRE (opcional), RES (opcional),
R2_BUCKET, R2_PUBLIC_URL, R2_ACCOUNT_ID (+ credenciales AWS_* para la CLI de aws).

- Link a una carpeta de Google Drive: procesa todos los .tif de la carpeta. La fecha y el nombre
  salen del nombre de cada archivo, por ejemplo "2026-10-21 Losa piso 1.tif". Las fechas que ya
  están en el visor se saltan.
- Link a un archivo: usa FECHA/NOMBRE si vienen; si no, los saca del nombre del archivo.
"""
import os, re, subprocess, sys, time, urllib.parse
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import actualizar_vuelos  # noqa: E402

TRABAJO = Path("trabajo")
EXT = (".tif", ".tiff")
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


def publicar(archivo, fecha, nombre):
    salida = TRABAJO / f"{fecha}.tif"
    subprocess.run(["bash", "scripts/convertir.sh", str(archivo), str(salida), RES], check=True)
    for intento in (1, 2, 3):  # R2 a veces rechaza una subida por partes; se reintenta
        r = subprocess.run(["aws", "s3", "cp", str(salida), f"s3://{env('R2_BUCKET')}/{fecha}.tif",
                            "--endpoint-url", f"https://{env('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
                            "--content-type", "image/tiff", "--only-show-errors"])
        if r.returncode == 0:
            break
        if intento == 3:
            raise RuntimeError("no se pudo subir a R2 después de 3 intentos")
        print(f"Reintentando subida ({intento})…", flush=True); time.sleep(10)
    actualizar_vuelos.agregar(fecha, nombre, f"{env('R2_PUBLIC_URL')}/{fecha}.tif")
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
        comun = nombres.pop() if len(nombres) == 1 and len(archivos) > 1 else None
        if comun:
            actualizar_vuelos.poner_titulo_si_falta(comun)
        for a in sorted(archivos, key=lambda a: desde_nombre(Path(a.path).name)[0] or a.path):
            nombre_archivo = Path(a.path).name
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
        if not es_geotiff(destino):
            sys.exit("::error::Lo descargado no es un GeoTIFF. Revisa que el link esté compartido como "
                     "'Cualquier persona con el enlace' y que el archivo sea .tif (ECW se convierte antes con convertir.bat).")
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
