from __future__ import annotations
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Iterator
from configuration import settings
from redirection import crear_sesion


def iterar_fechas(fecha_ini: str, fecha_fin: str) -> Iterator[date]:
    inicio = datetime.strptime(fecha_ini, "%Y-%m-%d").date()
    fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()

    if inicio > fin:
        raise ValueError("PDF_FECHA_INI no puede ser mayor que PDF_FECHA_FIN")

    actual = inicio
    while actual <= fin:
        yield actual
        actual += timedelta(days=1)


def construir_url(fecha: date, juzgado: str) -> str:
    fecha_str = fecha.strftime("%Y%m%d")
    return settings.pdf_url.format(
        fecha=fecha_str,
        juzgado=juzgado
    )


def nombre_archivo(fecha: date, juzgado: str) -> str:
    return f"boletin_{fecha.strftime('%Y%m%d')}_{juzgado}.pdf"


def es_pdf_valido(response) -> bool:
    if response.status_code != 200:
        return False

    content_type = (response.headers.get("Content-Type") or "").lower()
    if "pdf" in content_type:
        return True

    return response.content[:4] == b"%PDF"


def descargar_pdf(session, url: str, ruta_salida: Path, timeout: int = 30) -> bool:
    try:
        response = session.get(url, timeout=timeout, stream=True)
    except Exception as e:
        print(f"Error consultando {url}: {e}")
        return False

    if not es_pdf_valido(response):
        print(f"No existe o no es PDF: {url} | status={response.status_code}")
        return False

    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    with open(ruta_salida, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    print(f"Descargado: {ruta_salida}")
    return True


