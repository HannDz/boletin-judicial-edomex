from sqlalchemy import text
from datetime import date, datetime
from db import engine
from sqlalchemy.exc import IntegrityError, DataError, OperationalError, DBAPIError
import os


REGION_TO_TABLE = {
    "CUAUTITLAN": "epedientes_cuautitlan",
    "TLALNEPANTLA": "epedientes_tlalnepantla",
    "TOLUCA": "epedientes_toluca",
    "ECATEPEC": "expedientes_ecatepec",
}


def _append_db_error_txt(path: str, err: Exception, row: dict):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + "=" * 120 + "\n")
        f.write(f"TS: {datetime.now().isoformat(timespec='seconds')}\n")
        f.write(f"ERROR: {type(err).__name__}: {str(err)}\n")
        f.write(f"id_expediente: {row.get('id_expediente')}\n")
        f.write(f"sala: {row.get('sala')}\n")
        f.write(f"actor: {row.get('actor_demandante')}\n")
        f.write(f"demandado: {row.get('demandado')}\n")
        f.write(f"tipo: {row.get('tipo_juicio')}\n")
        f.write(f"fecha_publicacion: {row.get('fecha_publicacion')}\n")
        f.write(f"numero_boletin: {row.get('numero_boletin')}\n")
        f.write(f"numero_pagina: {row.get('numero_pagina')}\n")
        f.write(f"estatus: {row.get('estatus')}\n")
        f.write(f"conteo_demandados: {row.get('conteo_demandados')}\n")
        f.write(f"region: {row.get('region')}\n")
        f.write(f"tabla: {row.get('tabla')}\n")


def obtener_tabla_por_region(region: str) -> str:
    region = (region or "").strip().upper()

    tabla = REGION_TO_TABLE.get(region)
    if not tabla:
        raise ValueError(f"No existe tabla configurada para la región: {region}")

    return tabla


def construir_sql_insert_expedientes(tabla: str):
    return text(f"""
    INSERT INTO public.{tabla} (
        id_expediente,
        sala,
        actor_demandante,
        demandado,
        tipo_juicio,
        fecha_publicacion,
        numero_boletin,
        numero_pagina,
        estatus,
        conteo_demandados,
        tipo_persona,
        razon_social,
        primer_nombre,
        segundo_nombre,
        primer_apellido,
        segundo_apellido,
        nivel_confianza,
        nombre_original,
        nombre_normalizado
    )
    SELECT
        :id_expediente,
        :sala,
        :actor_demandante,
        :demandado,
        :tipo_juicio,
        :fecha_publicacion,
        :numero_boletin,
        :numero_pagina,
        :estatus,
        :conteo_demandados,
        p.tipo_persona,
        p.razon_social,
        p.primer_nombre,
        p.segundo_nombre,
        p.primer_apellido,
        p.segundo_apellido,
        p.nivel_confianza,
        p.nombre_original,
        p.nombre_normalizado
    FROM parse_demandante(:demandado) AS p;
    """)


CAMPOS_EXPEDIENTE = [
    "id_expediente",
    "sala",
    "actor_demandante",
    "demandado",
    "tipo_juicio",
    "fecha_publicacion",
    "numero_boletin",
    "numero_pagina",
    "estatus",
    "conteo_demandados",
]


def normalizar_registro(reg: dict) -> dict:
    return {k: reg.get(k) for k in CAMPOS_EXPEDIENTE}


def insertar_expedientes_bulk(
    registros: list[dict],
    region: str,
    batch_size: int = 1000,
    error_txt: str = "logs/db_insert_errors.txt"
) -> int:
    """
    Inserta en bulk sin romper el flujo:
    - selecciona tabla según región
    - intenta por batch
    - si falla batch -> fallback fila por fila con SAVEPOINT
    - registra errores a TXT y continúa
    - respeta parse_demandante(:demandado)
    """
    if not registros:
        return 0

    tabla = obtener_tabla_por_region(region)
    sql_insert = construir_sql_insert_expedientes(tabla)

    registros_norm = [normalizar_registro(r) for r in registros]
    total_insertadas = 0

    with engine.connect() as conn:
        for i in range(0, len(registros_norm), batch_size):
            if conn.in_transaction():
                conn.rollback()

            batch = registros_norm[i:i + batch_size]

            # 1) intento rápido por batch en su propia transacción
            try:
                with conn.begin():
                    result = conn.execute(sql_insert, batch)
                    total_insertadas += result.rowcount if result.rowcount is not None else len(batch)
                continue

            except (IntegrityError, DataError, OperationalError, DBAPIError) as e_batch:
                _append_db_error_txt(error_txt, e_batch, {
                    "id_expediente": f"[BATCH {i}-{i + len(batch) - 1}]",
                    "region": region,
                    "tabla": tabla,
                })

            # 2) fallback: fila por fila con SAVEPOINT para no romper el flujo
            for row in batch:
                try:
                    with conn.begin_nested():
                        conn.execute(sql_insert, row)
                    total_insertadas += 1

                except (IntegrityError, DataError, OperationalError, DBAPIError) as e_row:
                    row_error = dict(row)
                    row_error["region"] = region
                    row_error["tabla"] = tabla
                    _append_db_error_txt(error_txt, e_row, row_error)
                    continue

    return total_insertadas


def insertar_expediente(registro: dict, region: str) -> int:
    """
    Inserta un solo registro respetando parse_demandante(:demandado).
    """
    tabla = obtener_tabla_por_region(region)
    sql_insert = construir_sql_insert_expedientes(tabla)
    row = normalizar_registro(registro)

    with engine.begin() as conn:
        result = conn.execute(sql_insert, row)
        return result.rowcount if result.rowcount is not None else 1


def insertar_procesamiento_boletin(
    fecha_boletin: date,
    url_boletin: str,
    estado: str = "INICIADO",
    total_paginas: int | None = None,
    total_expedientes: int | None = None,
    descargado: bool | None = None,
    nombre_archivo: str | None = None,
) -> None:
    sql = text("""
        insert into procesamiento_boletin (
            fecha_boletin, url_boletin, estado,
            total_paginas, total_expedientes,
            descargado, nombre_archivo
        ) values (
            :fecha_boletin, :url_boletin, :estado,
            :total_paginas, :total_expedientes,
            :descargado, :nombre_archivo
        );
    """)

    with engine.begin() as conn:
        conn.execute(sql, {
            "fecha_boletin": fecha_boletin,
            "url_boletin": url_boletin,
            "estado": estado,
            "total_paginas": total_paginas,
            "total_expedientes": total_expedientes,
            "descargado": descargado,
            "nombre_archivo": nombre_archivo,
        })


def actualizar_total_paginas(id_procesamiento: int, total_paginas: int) -> None:
    sql = text("""
        update procesamiento_boletin
        set total_paginas = :total_paginas
        where id = :id;
    """)
    with engine.begin() as conn:
        conn.execute(sql, {"id": id_procesamiento, "total_paginas": total_paginas})


def existe_procesamiento(fecha_boletin: date, url_boletin: str) -> bool:
    sql = text("""
        select 1
        from procesamiento_boletin
        where fecha_boletin = :fecha
          and url_boletin = :url
        limit 1;
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"fecha": fecha_boletin, "url": url_boletin}).first() is not None