"""Fase 1: comprobar que los CSV no hayan cambiado desde su preparación."""
import hashlib
import logging
from pathlib import Path


# La raíz se obtiene desde este archivo para que funcione desde cualquier cwd.
carpeta_raiz = Path(__file__).resolve().parent.parent
# Ubicación predeterminada del lote, junto a la carpeta del proyecto.
carpeta_datos = carpeta_raiz.parent / "raw_batch_202611"


# Crear carpetas si no existen
carpeta_logs = carpeta_raiz / "logs"
carpeta_salida = carpeta_raiz / "output_samples"
carpeta_logs.mkdir(parents=True, exist_ok=True)
carpeta_salida.mkdir(parents=True, exist_ok=True)


# Configurar el log
logging.basicConfig(
    filename=carpeta_logs / "ejecucion_pipeline.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


def calcular_sha256(ruta_archivo):
    # Leer por bloques evita cargar un CSV grande entero en memoria.
    hash_sha256 = hashlib.sha256()
    with open(ruta_archivo, "rb") as f:
        while True:
            bloque = f.read(65536)
            if not bloque:
                break
            hash_sha256.update(bloque)
    return hash_sha256.hexdigest()


def main():
    ruta_manifiesto = carpeta_datos / "manifest_checksums.sha256"
    
    if not ruta_manifiesto.exists():
        logging.error(f"No encuentro el archivo {ruta_manifiesto}")
        return


    archivos_aprobados = []
    archivos_rechazados = []


    # Cada línea relaciona una huella esperada con el nombre de un CSV.
    with open(ruta_manifiesto, "r", encoding="utf-8") as f:
        lineas = f.readlines()


    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue
            
        hash_esperado, nombre_archivo = linea.split(maxsplit=1)
        nombre_archivo = nombre_archivo.strip("* ")
        
        ruta_archivo_csv = carpeta_datos / nombre_archivo
        
        if not ruta_archivo_csv.exists():
            logging.error(f"Archivo no encontrado: {nombre_archivo}")
            archivos_rechazados.append((nombre_archivo, hash_esperado, "FALTA_ARCHIVO"))
            continue


        # Si cambia algún byte, SHA-256 produce una huella diferente.
        hash_real = calcular_sha256(ruta_archivo_csv)
        
        if hash_real == hash_esperado:
            logging.info(f"OK: {nombre_archivo}")
            archivos_aprobados.append(nombre_archivo)
        else:
            logging.error(f"FALLO HASH: {nombre_archivo}")
            archivos_rechazados.append((nombre_archivo, hash_esperado, hash_real))


    # Registramos los archivos rechazados para poder revisarlos después.
    ruta_cuarentena = carpeta_salida / "quarantine_manifest.txt"
    with open(ruta_cuarentena, "w", encoding="utf-8") as f:
        f.write("REPORTE DE CUARENTENA\n\n")
        if archivos_rechazados:
            for archivo, esperado, real in archivos_rechazados:
                f.write(f"Archivo rechazado: {archivo}\n")
                f.write(f"Hash esperado: {esperado}\n")
                f.write(f"Hash real: {real}\n\n")
        else:
            f.write("Todo correcto, ningun archivo rechazado.\n")


    logging.info(f"Fin Fase 1. Aprobados: {len(archivos_aprobados)}, Rechazados: {len(archivos_rechazados)}")


if __name__ == "__main__":
    main()
