"""Descarga, convierte, sube a R2 y agrega a vuelos.json uno o varios ortomosaicos.

Lee de variables de entorno: LINK, FECHA (opcional), NOMBRE (opcional), RES (opcional),
R2_BUCKET, R2_PUBLIC_URL, R2_ACCOUNT_ID (+ credenciales AWS_* para la CLI de aws).

- Link a una carpeta de Google Drive: procesa todos los .tif de la carpeta. La fecha y el nombre
  salen del nombre de cada archivo, por ejemplo "2026-10-21 Losa piso 1.tif". Las fechas que ya
  están en el visor se saltan.
- Link a un archivo: usa FECHA/NOMBRE si vienen; si no, los saca del nombre del archivo.
"""
import os, re, subprocess, sys, urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import actualizar_vuelos  # noqa: E402

TRABAJO = Path("trabajo")
EXT = (".tif", ".tiff")
RE_FECHA = re.compile(r"(20\d{2})[-_. ]?(0[1-9]|1[0-2])[-_. ]?(0[1-9]|[12]\d|3[01])")

env = os.environ.get
LINK, FECHA, NOMBRE, RES = env("LINK", "").strip(), env("FECHA", "").strip(), env("NOMBRE", "").strip(), env("RES", "").strip()
resumen = []


def anotar(linea):
    print(linea, flush=True)
    resumen.append(linea)


def desde_nombre(nombre_archivo):
    """'2026-10-21 Losa piso 1.tif' -> ('2026-10-21', 'Losa piso 1')"""
    base = Path(nombre_archivo).stem
    m = RE_FECHA.search(base)
    if not m:
        return None, base
    fecha = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    partes = [x.replace("_", " ").strip(" -.") for x in (base[:m.start()], base[m.end():])]
    return fecha, re.sub(r"\s+", " ", " ".join(x for x in partes if x)).strip()


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
    subprocess.run(["aws", "s3", "cp", str(salida), f"s3://{env('R2_BUCKET')}/{fecha}.tif",
                    "--endpoint-url", f"https://{env('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
                    "--content-type", "image/tiff", "--only-show-errors"], check=True)
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
        for a in sorted(archivos, key=lambda a: a.path):
            nombre_archivo = Path(a.path).name
            if not nombre_archivo.lower().endswith(EXT):
                anotar(f"- ⏭️ {nombre_archivo}: no es .tif (los .ecw se convierten antes con convertir.bat)")
                continue
            fecha, nombre = desde_nombre(nombre_archivo)
            if not fecha:
                anotar(f"- ⚠️ {nombre_archivo}: el nombre no tiene fecha (renómbralo como 2026-10-21 Nombre.tif)")
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
            sys.exit("::error::Falta la fecha: escríbela en el formulario o ponla en el nombre del archivo (2026-10-21 Nombre.tif).")
        publicar(destino, fecha, nombre)

    with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a", encoding="utf-8") as f:
        f.write("### Resultado\n\n" + "\n".join(resumen) + "\n\nEl sitio se actualiza en 1 o 2 minutos.\n")
    if errores:
        sys.exit(f"::error::{errores} archivo(s) no se pudieron agregar; revisa el resumen.")


if __name__ == "__main__":
    main()
