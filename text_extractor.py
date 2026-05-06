from pathlib import Path
from pypdf import PdfReader

def leer_texto_pdf(ruta_pdf: str) -> tuple[str, int]:
    """
    Lee todo el texto del PDF incluyendo separadores por página
    y devuelve (texto, total_paginas).
    Además elimina el archivo.
    """
    ruta = Path(ruta_pdf)

    try:
        reader = PdfReader(str(ruta))
        partes = []
        total_paginas = len(reader.pages)

        for i, pagina in enumerate(reader.pages, start=1):
            texto = pagina.extract_text() or ""
            partes.append(
                f"\n{'=' * 80}\nPágina {i}\n{'=' * 80}\n{texto}"
            )

        texto_final = "\n".join(partes)

        return texto_final, total_paginas

    finally:
        try:
            if ruta.exists():
                ruta.unlink()
        except Exception as e:
            print(f"No se pudo eliminar el PDF {ruta_pdf}: {e}")