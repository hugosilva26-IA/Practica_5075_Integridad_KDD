# Informe de calidad de datos – Práctica 5075

## 1. Qué se ha hecho

En esta práctica he preparado un pequeño proceso para revisar unos datos de ventas antes de analizarlos. Primero compruebo que los CSV no hayan cambiado; después limpio los registros y guardo un resumen de los resultados. La idea es entender qué datos se pueden usar y dejar constancia de los que se han descartado.

## 2. Comprobación de los archivos

Para comprobar los CSV he usado SHA-256. El manifiesto incluye una huella para cada archivo, y el script calcula otra a partir del contenido actual. Si las dos huellas coinciden, el archivo pasa la comprobación.

En esta ejecución, los archivos de las tiendas Norte y Este han pasado. El archivo de la tienda Sur no coincide con la huella del manifiesto, así que el pipeline lo ha excluido.

- Archivos aprobados: **2**.
- Archivos rechazados: **1**.
- Integridad del lote: **66.67 %**.

Esta comprobación sirve para detectar si un archivo ha cambiado, pero no dice si los datos tienen sentido. Por eso, después se revisan también los registros.

## 3. Limpieza de los registros

Los dos archivos aprobados aportan **100 registros**. El script ha apartado **13** y el resultado final contiene **87**.

Para decidir qué registros conservar, el script comprueba que cada venta tenga un identificador, una fecha válida del año 2026, un importe numérico mayor que cero y unidades enteras de al menos una. También marca los importes que quedan fuera de los límites calculados con IQR.

Los campos `tienda`, `categoria` y `metodo_pago` son descriptivos. Si alguno está vacío, se completa con «No especificado» en vez de descartar toda la venta.

## 4. Resultados del perfilado

Los valores de esta sección están tomados de `output_samples/metricas_perfilado.json`.

| Indicador | Resultado |
|---|---:|
| Registros de entrada | 100 |
| Registros apartados | 13 |
| Registros finales | 87 |
| Archivos íntegros | 2 |
| Archivos rechazados | 1 |
| Integridad criptográfica | 66.67 % |

### Importe de las ventas (`importe_eur`)

| Medida | Valor (€) |
|---|---:|
| Media | 70.99 |
| Mediana | 73.44 |
| Mínimo | 12.50 |
| Máximo | 124.47 |

Para detectar importes atípicos se ha usado el rango intercuartílico (IQR). Dicho de forma sencilla, el método calcula un intervalo a partir de cómo se distribuyen los importes. En el JSON, los límites aparecen como **−0.18 €** y **141.12 €**.

## 5. Relación con KDD y calidad de datos

Lo realizado encaja con las primeras tareas de KDD: seleccionar los archivos que pasan la comprobación, limpiar los datos y dejarlos preparados para analizarlos. En esta práctica no se ha entrenado ningún modelo; el trabajo se centra en preparar y describir los datos de entrada.

También se han aplicado comprobaciones relacionadas con la calidad de los datos, como revisar que haya identificadores y fechas válidas y que los importes y las unidades cumplan las reglas definidas. Estas reglas ayudan a encontrar problemas, aunque no garantizan que todos los datos sean correctos en un sentido más amplio.

## 6. Conclusión

El proceso ha detectado un CSV cuya huella no coincide con la del manifiesto y lo ha dejado fuera. De los otros dos archivos se han conservado 87 de los 100 registros después de aplicar las reglas de limpieza. El JSON recoge las métricas de esta ejecución, y el log permite consultar los mensajes del proceso.

## 7. Cómo repetir la ejecución

Desde la carpeta del proyecto, con Python y las dependencias `pandas` y `numpy` instaladas, se pueden ejecutar los dos scripts indicando la carpeta donde están los CSV y el manifiesto:

```bash
python scripts/01_verificar_integridad.py --input /ruta/raw_batch_202611
python scripts/02_pipeline_saneamiento.py --input /ruta/raw_batch_202611
```

Los scripts no modifican los CSV originales. El log se guarda en `logs/ejecucion_pipeline.log`; los resultados de cuarentena y perfilado, en `output_samples/`.
