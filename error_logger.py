import json
import traceback
from datetime import datetime, date
from pathlib import Path
from configuration import settings


LOG_DIR = Path(settings.log_dir)
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / settings.log_file


def log_error_boletin(
    fecha_boletin: date,
    url_boletin: str,
    etapa: str,
    exc: Exception,
    extra: dict | None = None
) -> None:
    """
    Guarda error a archivo SIN tronar el proceso.
    Incluye timestamp, fecha, URL, etapa, excepción y traceback.
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "timestamp": ts,
        "fecha_boletin": str(fecha_boletin),
        "url_boletin": url_boletin,
        "etapa": etapa,
        "exception_type": type(exc).__name__,
        "exception_message": str(exc),
        "traceback": traceback.format_exc()
    }

    if extra:
        payload["extra"] = extra

    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")