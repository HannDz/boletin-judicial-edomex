import os
import json
import traceback
from datetime import datetime, date
from pathlib import Path
from error_logger import log_error_boletin
from configuration import settings
from redirection import crear_sesion
from pdf_downloader import iterar_fechas, construir_url, nombre_archivo, descargar_pdf
from juzgados_catalogo import obtener_info_juzgado
from text_extractor import leer_texto_pdf
from extractor_js import *
from repository import *
# -----------------------------
# Configuración de carpetas
# -----------------------------
os.makedirs("tmp", exist_ok=True)

# -----------------------------
# Sesión
# -----------------------------
session = crear_sesion()
session.headers.update({"User-Agent": "Mozilla/5.0"})

carpeta = Path(settings.pdf_dir)

total_ok = 0
total_no = 0
total_existentes = 0
total_error = 0
textos: list[str] = []
# -----------------------------
# Loop principal: 1 try/except POR PDF
# -----------------------------
for juzgado in settings.pdf_juzgados:
    try:
        info = obtener_info_juzgado(juzgado)
        region = info["region"]
        print(f"\nProcesando juzgado: {juzgado} - {info.get('nombre')}")

    except Exception as e_juzgado:
        log_error_boletin(
            fecha_boletin=date.today(),
            url_boletin="",
            etapa="Obtener info juzgado",
            exc=e_juzgado,
            extra={"juzgado": juzgado}
        )
        total_error += 1
        continue

    for fecha in iterar_fechas(settings.pdf_fecha_ini, settings.pdf_fecha_fin):
        url = ""
        try:
            url = construir_url(fecha, juzgado)
        except Exception as e_pdfsrc:
            log_error_boletin(fecha, url, "Extraer PDF source", e_pdfsrc, 
                              extra={
                    "juzgado": juzgado,
                    "nombre_juzgado": info.get("nombre"),
                    "region": info.get("region"),
                    "tipo": info.get("tipo")
                })
            continue
        
        try:
            if existe_procesamiento_por_region(region, fecha, url):
                print(f"Ya existe {url}")
                continue

            archivo = carpeta / juzgado / nombre_archivo(fecha, juzgado)

            if archivo.exists():
                print(f"Ya existe: {archivo}")
                total_existentes += 1
                continue
        except Exception as e_pdfsrc:
            log_error_boletin(fecha, url, "Validación de archivo PDF", e_pdfsrc,
                              extra={
                    "juzgado": juzgado,
                    "nombre_juzgado": info.get("nombre"),
                    "region": info.get("region"),
                    "tipo": info.get("tipo")
                })
            continue
        try:
            ok = descargar_pdf(
                session=session,
                url=url,
                ruta_salida=archivo,
                timeout=settings.pdf_timeout
            )
            if ok:
                texto, total_paginas = leer_texto_pdf(str(archivo))
                parser = BoletinEdomexParser()
                registros = parser.parse(texto, fecha)
                textos.append(texto)
                total_ok += 1
                # for text in textos:
                #     print(text)
                try:
                    cantidad = insertar_expedientes_bulk(
                        registros=registros,
                        region=region
                    )

                    if cantidad > 0:
                        insertar_procesamiento_boletin(
                            region=region,
                            fecha_boletin=fecha,
                            url_boletin=url,
                            estado="TERMINADO",
                            total_paginas=total_paginas,
                            total_expedientes=len(registros),
                            descargado=False
                        )
                except Exception as e_db:
                    log_error_boletin(fecha, url, "Inserción BD", e_db, {"total_expedientes": len(registros)})
                    continue
            else:
                total_no += 1
                print("No se pudo descargar el PDF")

        except Exception as e_pdf:
            log_error_boletin(
                fecha_boletin=fecha,
                url_boletin=url,
                etapa="Descarga PDF",
                exc=e_pdf,
                extra={
                    "juzgado": juzgado,
                    "nombre_juzgado": info.get("nombre"),
                    "region": info.get("region"),
                    "tipo": info.get("tipo")
                }
            )
            total_error += 1
            continue

print("\nResumen")
print(f"Descargados: {total_ok}")
print(f"No encontrados: {total_no}")
print(f"Ya existentes: {total_existentes}")
print(f"Con error: {total_error}")