# configuration.py
import os
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_ENV = BASE_DIR / "config.env"

env_from_var = os.getenv("ENV_PATH")
ENV_PATH = Path(env_from_var).expanduser() if env_from_var else DEFAULT_ENV

if not ENV_PATH.exists():
    raise FileNotFoundError(f"No existe el archivo .env en: {ENV_PATH}")

load_dotenv(dotenv_path=ENV_PATH, override=True)

def get_env(key: str, default: str | None = None, *, required: bool = False) -> str | None:
    val = os.getenv(key, default)
    if required and (val is None or val == ""):
        raise ValueError(f"Falta variable requerida: {key}")
    return val

def get_int(key: str, default: int | None = None, *, required: bool = False) -> int | None:
    val = get_env(key, None, required=required)
    if val is None or val == "":
        return default
    try:
        return int(val)
    except ValueError as e:
        raise ValueError(f"Variable {key} debe ser entero. Valor actual: {val}") from e

def get_list(key: str, default: str = "") -> list[str]:
    raw = get_env(key, default) or ""
    return [x.strip() for x in raw.split(",") if x.strip()]

@dataclass(frozen=True)
class Settings:
    # DB
    db_backend: str
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    # Extras genéricos (ejemplos)
    app_env: str
    log_level: str
    url_boletin:str
    url_boletin_filtro:str
    fecha_ini:str
    fecha_fin:str
    is_debbug:str
    log_dir:str
    log_file:str
    pdf_url: str
    pdf_fecha_ini: str
    pdf_fecha_fin: str
    pdf_juzgados: list[str]
    pdf_dir: str
    pdf_timeout: int

def load_settings() -> Settings:
    return Settings(
        db_backend=(get_env("DB_BACKEND", "postgres") or "postgres").lower(),
        db_host=get_env("DB_HOST", "localhost") or "localhost",
        db_port=get_int("DB_PORT", 5432) or 5432,
        db_name=get_env("DB_NAME", required=True) or "",
        db_user=get_env("DB_USER", required=True) or "",
        db_password=get_env("DB_PASSWORD", required=True) or "",
        #Ejemplo de obtencion de llaves
        url_boletin=get_env("URL_BOLETIN", "") or "",
        app_env=get_env("APP_ENV", "dev") or "dev",
        log_level=get_env("LOG_LEVEL", "INFO") or "INFO",
        url_boletin_filtro=get_env("URL_BOLETIN_FILTRO", "") or "",
        fecha_ini=get_env("FILTRADO_INI","") or "",
        fecha_fin=get_env("FILTRADO_FIN","") or "",
        is_debbug=get_env("ISDEBBUG", "false") or "false",
        log_dir=get_env("LOG_DIR","") or "logs",
        log_file=get_env("LOG_FILE","") or "errores_boletin.log",
        pdf_url=get_env("PDF_URL", required=True) or "",
        pdf_fecha_ini=get_env("FECHA_INI", required=True) or "",
        pdf_fecha_fin=get_env("FECHA_FIN", required=True) or "",
        pdf_juzgados=get_list("PDF_JUZGADOS"),
        pdf_dir=get_env("PDF_DIR", "pdfs") or "pdfs",
        pdf_timeout=get_int("PDF_TIMEOUT", 30) or 30,
    )

settings = load_settings()
