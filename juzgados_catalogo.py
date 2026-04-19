import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
JUZGADOS_JSON = BASE_DIR / "juzgados.json"

def cargar_catalogo_juzgados() -> dict:
    if not JUZGADOS_JSON.exists():
        raise FileNotFoundError(f"No existe el catálogo: {JUZGADOS_JSON}")

    with open(JUZGADOS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def obtener_info_juzgado(id_juzgado: str) -> dict:
    catalogo = cargar_catalogo_juzgados()
    return catalogo.get(str(id_juzgado), {
        "nombre": None,
        "region": None,
        "tipo": None
    })