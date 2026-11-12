"""Fases 2 y 3: limpiar los CSV íntegros y resumir la calidad de los datos."""
import hashlib
import json
import logging
import pandas as pd
from pathlib import Path


# La raíz se obtiene desde este archivo, no desde la carpeta actual de consola.
carpeta_raiz = Path(__file__).resolve().parent.parent
carpeta_datos = carpeta_raiz.parent / "raw_batch_202611"
carpeta_salida = carpeta_raiz / "output_samples"


# Usamos el mismo log que el script 1
logging.basicConfig(
    filename=carpeta_raiz / "logs" / "ejecucion_pipeline.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


def calcular_sha256(ruta_archivo):
    # Se valida el CSV antes de leerlo, con el mismo criterio de la fase 1.
    hash_sha256 = hashlib.sha256()
    with open(ruta_archivo, "rb") as f:
        while True:
            bloque = f.read(65536)
            if not bloque:
                break
            hash_sha256.update(bloque)
    return hash_sha256.hexdigest()


def cargar_csvs_buenos():
    # Solo combinamos archivos del manifiesto que conservan la huella esperada.
    ruta_manifiesto = carpeta_datos / "manifest_checksums.sha256"
    archivos_ok = 0
    archivos_mal = 0
    lista_dataframes = []


    with open(ruta_manifiesto, "r", encoding="utf-8") as f:
        lineas = f.readlines()


    for linea in lineas:
        linea = linea.strip()
        if not linea: continue
        
        hash_esperado, nombre_archivo = linea.split(maxsplit=1)
        nombre_archivo = nombre_archivo.strip("* ")
        ruta_csv = carpeta_datos / nombre_archivo


        if ruta_csv.exists() and calcular_sha256(ruta_csv) == hash_esperado:
            df = pd.read_csv(ruta_csv)
            lista_dataframes.append(df)
            archivos_ok += 1
            logging.info(f"Cargado {nombre_archivo} con {len(df)} filas")
        else:
            archivos_mal += 1
            logging.warning(f"Ignorado {nombre_archivo} por fallo de hash")
            
    df_completo = pd.concat(lista_dataframes, ignore_index=True)
    return df_completo, archivos_ok, archivos_mal


def main():
    df, num_ok, num_mal = cargar_csvs_buenos()
    total_filas = len(df)
    
    # Arreglar formatos
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["importe_eur"] = pd.to_numeric(df["importe_eur"], errors="coerce")
    df["unidades"] = pd.to_numeric(df["unidades"], errors="coerce")


    # El IQR es la distancia entre los percentiles 25 y 75. Se amplía 1,5 veces
    # para definir un rango habitual y detectar importes que quedan muy alejados.
    importes = df["importe_eur"].dropna()
    q1 = importes.quantile(0.25)
    q3 = importes.quantile(0.75)
    iqr = q3 - q1
    limite_abajo = q1 - 1.5 * iqr
    limite_arriba = q3 + 1.5 * iqr


    # La máscara indica qué filas son válidas. Partimos de que todas pasan y
    # cada regla descarta las que incumplen sus condiciones.
    filas_buenas = pd.Series(True, index=df.index)


    # Filtrar 1: Sin ID
    filas_buenas = filas_buenas & df["id_transaccion"].notna()
    
    # Filtrar 2: Fechas malas o futuras (suponiendo año 2026)
    filas_buenas = filas_buenas & df["timestamp"].notna()
    filas_buenas = filas_buenas & (df["timestamp"].dt.year == 2026)
    filas_buenas = filas_buenas & (df["timestamp"] <= pd.Timestamp.now())
    
    # Filtrar 3: Importes menores a cero
    filas_buenas = filas_buenas & df["importe_eur"].notna()
    filas_buenas = filas_buenas & (df["importe_eur"] > 0)
    
    # Filtrar 4: Unidades negativas o decimales
    filas_buenas = filas_buenas & df["unidades"].notna()
    filas_buenas = filas_buenas & (df["unidades"] >= 1)
    filas_buenas = filas_buenas & (df["unidades"] % 1 == 0)
    
    # Apartamos los importes que quedan fuera de los límites IQR calculados.
    filas_buenas = filas_buenas & (df["importe_eur"] >= limite_abajo)
    filas_buenas = filas_buenas & (df["importe_eur"] <= limite_arriba)


    # Aplicamos la máscara y copiamos el resultado para poder modificarlo.
    df_limpio = df[filas_buenas].copy()
    
    # Contamos cuántas hemos tirado a la basura
    filas_basura = total_filas - len(df_limpio)
    logging.warning(f"Filas eliminadas por limpieza: {filas_basura}")


    # Los campos descriptivos pueden faltar sin invalidar la venta; indicamos
    # explícitamente que el dato no estaba disponible.
    df_limpio["tienda"] = df_limpio["tienda"].fillna("No especificado")
    df_limpio["categoria"] = df_limpio["categoria"].fillna("No especificado")
    df_limpio["metodo_pago"] = df_limpio["metodo_pago"].fillna("No especificado")
    
    # Poner las fechas bonitas para guardar
    df_limpio["timestamp"] = df_limpio["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")


    # Calcular estadísticas
    metricas = {
        "resumen": {
            "total_verificados": total_filas,
            "borrados_por_errores": int(filas_basura),
            "total_limpios": len(df_limpio)
        },
        "integridad": {
            "archivos_bien": num_ok,
            "archivos_mal": num_mal,
            "porcentaje_integridad": round(num_ok / (num_ok + num_mal) * 100, 2)
        },
        "estadisticas_precios": {
            "media": round(df_limpio["importe_eur"].mean(), 2),
            "mediana": round(df_limpio["importe_eur"].median(), 2),
            "maximo": round(df_limpio["importe_eur"].max(), 2),
            "minimo": round(df_limpio["importe_eur"].min(), 2)
        },
        "limites_iqr": {
            "tope_inferior": round(limite_abajo, 2),
            "tope_superior": round(limite_arriba, 2)
        }
    }


    # Guardamos las métricas en JSON para consultarlas o incluirlas en el informe.
    ruta_json = carpeta_salida / "metricas_perfilado.json"
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(metricas, f, indent=4)
        
    logging.info(f"Proceso completado. Quedan {len(df_limpio)} filas validas.")


if __name__ == "__main__":
    main()

