import re
import unicodedata
from datetime import datetime, date


class BoletinEdomexParser:
    def __init__(self):
        self.meses = {
            "ENERO": 1,
            "FEBRERO": 2,
            "MARZO": 3,
            "ABRIL": 4,
            "MAYO": 5,
            "JUNIO": 6,
            "JULIO": 7,
            "AGOSTO": 8,
            "SEPTIEMBRE": 9,
            "SETIEMBRE": 9,
            "OCTUBRE": 10,
            "NOVIEMBRE": 11,
            "DICIEMBRE": 12,
        }

        self.tipos_juicio = [
            "CONTROVERSIA DE ARRENDAMIENTO",
            "ARRENDAMIENTO",
            "EJECUTIVO MERCANTIL",
            "EJECU MERCAN",
            "ORDINARIO CIVIL",
            "ORDINA CIVIL",
            "DESAHUCIO",
        ]

        self.map_tipo_juicio = {
            "CONTROVERSIA DE ARRENDAMIENTO": "ARRENDAMIENTO",
            "ARRENDAMIENTO": "ARRENDAMIENTO",
            "ORDINA CIVIL": "ORDINARIO CIVIL",
            "ORDINARIO CIVIL": "ORDINARIO CIVIL",
            "EJECU MERCAN": "EJECUTIVO MERCANTIL",
            "EJECUTIVO MERCANTIL": "EJECUTIVO MERCANTIL",
            "DESAHUCIO": "DESAHUCIO",
        }

        self.map_estatus = {
            "ACUERDO": "ACUERDO",
            "ACUERDOS": "ACUERDO",
            "INICIAL": "INICIAL",
            "SENTENCIA INTERLOCUT": "SENTENCIA INTERLOCUTORIA",
            "SENTENCIA INTERLOCUTORIA": "SENTENCIA INTERLOCUTORIA",
            "SENTENCIA": "SENTENCIA",
            "SENTENCIA DEFINITIVA": "SENTENCIA DEFINITIVA",
        }

        self._build_regex()

    def _build_regex(self):
        self.re_juzgado = re.compile(
            r"^(JUZGADO\s+.+)$",
            re.IGNORECASE | re.MULTILINE
        )

        self.re_sala = re.compile(
            r"^(PRIMERA SECRETARIA|SEGUNDA SECRETARIA|TERCERA SECRETARIA|CUARTA SECRETARIA|QUINTA SECRETARIA|SECRETARIA)$",
            re.IGNORECASE | re.MULTILINE
        )

        self.re_fecha = re.compile(
            r"ACUERDOS\s+DEL\s+D[IÍ]A\s+\w+,\s*(\d{1,2})\s+DE\s+([A-ZÁÉÍÓÚ]+)\s+DE\s+(\d{4})",
            re.IGNORECASE
        )

        self.re_bloque = re.compile(
            r"(?m)^\s*\d+\._\s*.*?(?=(?:^\s*\d+\._)|\Z)",
            re.DOTALL
        )

        self.re_expediente = re.compile(
            r"^([0-9]{1,6}/[0-9]{4})\s+(.*)$",
            re.IGNORECASE | re.DOTALL
        )

        self.re_estatus = re.compile(
            r"\(([^)]+)\)\s*$",
            re.IGNORECASE
        )

        self.re_vs = re.compile(
            r"\bVS\.?\b",
            re.IGNORECASE
        )

        self.re_pagina = re.compile(
            r"\n=+\nPágina\s+(\d+)\n=+\n",
            re.IGNORECASE
        )

        self.re_numero_boletin = re.compile(
            r"\bNo\.\s*(\d+)\b",
            re.IGNORECASE
        )

    def limpiar_espacios(self, texto: str) -> str:
        return re.sub(r"\s+", " ", texto or "").strip()

    def limpiar_campos_multilinea(self, texto: str | None) -> str | None:
        if not texto:
            return None

        lineas = texto.replace("\r", "\n").split("\n")
        lineas_limpias = [re.sub(r"[ \t]+", " ", ln).strip() for ln in lineas]
        lineas_limpias = [ln for ln in lineas_limpias if ln != ""]
        return "\n".join(lineas_limpias).strip()

    def quitar_acentos(self, texto: str | None) -> str:
        if texto is None:
            return ""
        nfkd = unicodedata.normalize("NFKD", texto)
        return "".join(c for c in nfkd if not unicodedata.combining(c))

    def normalizar_texto(self, texto: str) -> str:
        texto = texto.replace("\r", "\n")
        texto = texto.replace("\xa0", " ")
        texto = re.sub(r"[ \t]+", " ", texto)
        texto = re.sub(r"\n+", "\n", texto)
        return texto.strip()

    def normalizar_nombre(self, texto: str | None) -> str | None:
        if not texto:
            return None
        return self.limpiar_espacios(self.quitar_acentos(texto.upper()))

    def extraer_numero_boletin(self, texto: str) -> int | None:
        match = self.re_numero_boletin.search(texto)
        if not match:
            return None
        return int(match.group(1))

    def extraer_juzgado(self, texto: str) -> str | None:
        match = self.re_juzgado.search(texto)
        return self.limpiar_espacios(match.group(1)) if match else None

    def extraer_sala(self, texto: str) -> str | None:
        match = self.re_sala.search(texto)
        return self.limpiar_espacios(match.group(1).upper()) if match else None

    def extraer_fecha_publicacion(self, texto: str) -> date | None:
        match = self.re_fecha.search(texto)
        if not match:
            return None

        dia = int(match.group(1))
        mes_txt = self.quitar_acentos(match.group(2).upper())
        anio = int(match.group(3))

        mes = self.meses.get(mes_txt)
        if not mes:
            return None

        return date(anio, mes, dia)

    def extraer_paginas(self, texto: str) -> list[tuple[int, str]]:
        """
        Divide el texto completo por los separadores:
        ================================================================================
        Página X
        ================================================================================
        """
        texto = self.normalizar_texto(texto)

        matches = list(self.re_pagina.finditer("\n" + texto))
        if not matches:
            return [(1, texto)]

        paginas = []
        full_text = "\n" + texto

        for i, match in enumerate(matches):
            numero_pagina = int(match.group(1))
            inicio = match.end()
            fin = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
            contenido = full_text[inicio:fin].strip()
            paginas.append((numero_pagina, contenido))

        return paginas

    def extraer_bloques(self, texto: str) -> list[tuple[int, str]]:
        return [
            (m.start(), m.group(0).strip())
            for m in self.re_bloque.finditer(texto)
        ]
    def extraer_sala_antes_de_posicion(
        self,
        texto: str,
        posicion: int,
        sala_actual: str | None = None
    ) -> str | None:
        """
        Busca la última secretaría antes del expediente actual.
        Si no encuentra, conserva la sala anterior.
        """
        texto_anterior = texto[:posicion]
        matches = list(self.re_sala.finditer(texto_anterior))

        if not matches:
            return sala_actual

        ultima = matches[-1]
        return self.limpiar_espacios(ultima.group(1).upper())
    
    def normalizar_estatus(self, estatus: str | None) -> str | None:
        if not estatus:
            return None
        e = self.normalizar_nombre(estatus)
        return self.map_estatus.get(e, e)

    def detectar_estatus(self, texto: str) -> tuple[str | None, str]:
        match = re.search(
            r"\((ACUERDO|ACUERDOS|INICIAL|SENTENCIA DEFINITIVA|SENTENCIA INTERLOCUT|SENTENCIA INTERLOCUTORIA|SENTENCIA)\)",
            texto,
            flags=re.IGNORECASE
        )

        if not match:
            return None, texto.strip()

        estatus = self.normalizar_estatus(match.group(1))
        limpio = texto[:match.start()].strip()

        return estatus, limpio

    def detectar_tipo_juicio(self, resto: str) -> tuple[str | None, str]:
        resto_up = self.normalizar_nombre(resto) or ""

        for patron in sorted(self.tipos_juicio, key=len, reverse=True):
            patron_up = self.normalizar_nombre(patron)
            idx = resto_up.find(patron_up)
            if idx != -1:
                tipo_real = self.map_tipo_juicio.get(patron_up, patron_up)
                restante = resto[idx + len(patron_up):].strip()
                return tipo_real, restante

        return None, resto.strip()

    def separar_demandados(self, demandado: str | None) -> list[str]:
        if not demandado:
            return []

        especiales = self.separar_demandados_especiales(demandado)
        if especiales:
            return especiales

        plano = demandado.replace("\n", " ")
        plano = self.limpiar_espacios(plano)
        plano = self.limpiar_parentesis_no_estatus(plano) or ""
        # Cortar cualquier estatus que se haya colado
        plano = re.split(
            r"\((?:ACUERDO|ACUERDOS|INICIAL|SENTENCIA DEFINITIVA|SENTENCIA INTERLOCUT|SENTENCIA INTERLOCUTORIA|SENTENCIA)\)",
            plano,
            maxsplit=1,
            flags=re.IGNORECASE
        )[0]

        # Primer corte por coma
        partes = [
            p.strip()
            for p in plano.split(",")
            if p.strip()
        ]

        resultado = []

        for p in partes:
            limpio = self.limpiar_demandado_individual(p)

            if not limpio:
                continue

            # Segundo corte: casos "PERSONA Y PERSONA"
            subpartes = self.separar_por_conjuncion_personas(limpio)

            for sp in subpartes:
                sp_limpio = self.limpiar_demandado_individual(sp)
                if sp_limpio:
                    resultado.append(sp_limpio)

        return resultado

    def nivel_confianza_registro(
        self,
        id_expediente: str | None,
        tipo_juicio: str | None,
        actor: str | None,
        demandado: str | None,
        estatus: str | None
    ) -> str:
        score = 0
        if id_expediente:
            score += 1
        if tipo_juicio:
            score += 1
        if actor:
            score += 1
        if demandado:
            score += 1
        if estatus:
            score += 1

        if score >= 5:
            return "ALTA"
        if score >= 3:
            return "MEDIA"
        return "BAJA"

    def parsear_bloque(
        self,
        bloque: str,
        fecha_publicacion: date | None,
        juzgado: str | None,
        sala: str | None,
        numero_boletin: int | None = None,
        numero_pagina: int | None = None
    ) -> list[dict]:
        bloque = self.normalizar_texto(bloque)
        bloque = re.sub(r"^\d+\._\s*", "", bloque)

        m_exp = self.re_expediente.match(bloque)
        if not m_exp:
            return []

        id_expediente = m_exp.group(1).strip()
        resto = m_exp.group(2).strip()

        estatus, resto = self.detectar_estatus(resto)
        tipo_juicio, resto = self.detectar_tipo_juicio(resto)

        if tipo_juicio not in {"DESAHUCIO", "ARRENDAMIENTO", "ORDINARIO CIVIL", "EJECUTIVO MERCANTIL"}:
            return []

        partes = re.split(self.re_vs, resto, maxsplit=1)
        if len(partes) == 2:
            actor = self.limpiar_campos_multilinea(partes[0].strip(" .,-"))
            demandado_completo = self.limpiar_campos_multilinea(partes[1].strip(" .,-"))
        else:
            actor = self.limpiar_campos_multilinea(resto.strip(" .,-"))
            demandado_completo = None

        demandados = self.separar_demandados(demandado_completo)

        if not demandados:
            demandados = [None]

        total_demandados = str(len(demandados)) if demandados and demandados[0] is not None else None

        registros = []

        for demandado in demandados:
            registros.append({
                "id_expediente": id_expediente,
                "sala": sala,
                "actor_demandante": actor,
                "demandado": demandado,
                "tipo_juicio": tipo_juicio,
                "fecha_publicacion": fecha_publicacion,
                "conteo_demandados": total_demandados,
                "estatus": estatus,
                "juzgado": juzgado,
                "numero_boletin": numero_boletin,
                "numero_pagina": numero_pagina,
                "created_at": datetime.now(),
                "nivel_confianza": self.nivel_confianza_registro(
                    id_expediente=id_expediente,
                    tipo_juicio=tipo_juicio,
                    actor=actor,
                    demandado=demandado,
                    estatus=estatus,
                ),
                "nombre_original": actor,
                "nombre_normalizado": self.normalizar_nombre(actor),
            })

        return registros

    def deduplicar(self, registros: list[dict]) -> list[dict]:
        resultado = []
        vistos = set()

        for r in registros:
            key = (
                r.get("id_expediente"),
                r.get("actor_demandante"),
                r.get("demandado"),
                r.get("tipo_juicio"),
                r.get("estatus"),
                r.get("numero_pagina"),
            )
            if key in vistos:
                continue
            vistos.add(key)
            resultado.append(r)

        return resultado

    def parse(self, texto: str, fecha: str) -> list[dict]:
        texto = self.normalizar_texto(texto)

        numero_boletin = self.extraer_numero_boletin(texto)
        paginas = self.extraer_paginas(texto)

        registros = []

        juzgado_actual = None
        sala_actual = None
        fecha_actual = None

        for numero_pagina, contenido_pagina in paginas:
            juzgado_pagina = self.extraer_juzgado(contenido_pagina)

            if juzgado_pagina:
                juzgado_actual = juzgado_pagina

            bloques = self.extraer_bloques(contenido_pagina)

            for posicion_bloque, bloque in bloques:
                sala_bloque = self.extraer_sala_antes_de_posicion(
                    contenido_pagina,
                    posicion_bloque,
                    sala_actual
                )

                fecha_bloque = fecha

                if sala_bloque:
                    sala_actual = sala_bloque

                if fecha_bloque:
                    fecha_actual = fecha_bloque

                regs = self.parsear_bloque(
                    bloque=bloque,
                    fecha_publicacion=fecha_actual,
                    juzgado=juzgado_actual,
                    sala=sala_actual,
                    numero_boletin=numero_boletin,
                    numero_pagina=numero_pagina
                )

                if regs:
                    registros.extend(regs)

        return self.deduplicar(registros)
    
    def limpiar_demandado_individual(self, texto: str | None) -> str | None:
        if not texto:
            return None

        t = self.limpiar_espacios(texto.replace("\n", " "))

        # quitar Y/O suelto al final
        t = re.sub(r"\s+Y/O\s*$", "", t, flags=re.IGNORECASE)

        # quitar frases genéricas
        patrones_corte = [
            r"\s+Y/O\s+CUALQUIER\s+OTRO\s+HABITANTE.*$",
            r"\s+Y/O\s+CUALQUIER\s+OTRO\s+OCUPANTE.*$",
            r"\s+Y/O\s+CUALQUIER\s+OTRO\s+POSEEDOR.*$",
            r"\s+CUALQUIER\s+OTRO\s+HABITANTE.*$",
            r"\s+CUALQUIER\s+OTRO\s+OCUPANTE.*$",
            r"\s+CUALQUIER\s+OTRO\s+POSEEDOR.*$",
            r"\s+OCUPANTE\s+O\s+POSEEDOR.*$",
        ]

        for patron in patrones_corte:
            t = re.sub(patron, "", t, flags=re.IGNORECASE)

        # limpieza final
        t = t.strip(" .,-")

        return t or None    


    def separar_demandados_especiales(self, demandado: str) -> list[str] | None:
        """
        Casos especiales de morales/instituciones.
        Ejemplo:
        QUIEN SE HACE LLAMAR TAMBIÉN CITIBANAMEX Y EL INSTITUTO...
        """
        if not demandado:
            return None

        texto = self.limpiar_espacios(demandado.replace("\n", " "))
        texto_norm = self.normalizar_nombre(texto) or ""

        if "QUIEN SE HACE LLAMAR TAMBIEN" in texto_norm:
            # Quita lo anterior hasta "TAMBIÉN"
            texto_limpio = re.sub(
                r".*?QUIEN\s+SE\s+HACE\s+LLAMAR\s+TAMBI[EÉ]N\s+",
                "",
                texto,
                flags=re.IGNORECASE
            )

            # Divide por " Y EL " o " Y LA "
            partes = re.split(
                r"\s+Y\s+(?=EL\s+|LA\s+|LOS\s+|LAS\s+)",
                texto_limpio,
                flags=re.IGNORECASE
            )

            resultado = []
            for p in partes:
                p = self.limpiar_demandado_individual(p)
                if p:
                    resultado.append(p)

            return resultado if resultado else None

        return None
    
    def separar_por_conjuncion_personas(self, texto: str) -> list[str]:
        """
        Separa casos como:
        ALICIA SALCEDO MORA Y FLAVIO SANCHEZ LOPEZ

        o:
        CLAUDIA BATALLA MORELL E INSTITUTO DE LA FUNCIÓN REGISTRAL...

        en registros separados.
        """
        if not texto:
            return []

        t = self.limpiar_espacios(texto.replace("\n", " "))

        t_norm = self.normalizar_nombre(t) or ""

        frases_no_separar = [
            "Y/O",
            "Y OTRO",
            "Y OTROS",
            "Y CUALQUIER",
            "Y QUIEN",
            "Y/O CUALQUIER",
        ]

        if any(frase in t_norm for frase in frases_no_separar):
            return [t]

        # Separar por " Y " o " E " únicamente si después parece iniciar otro demandado
        partes = re.split(
            r"\s+(?:Y|E)\s+(?=(?:[A-ZÁÉÍÓÚÑ]{2,}|EL\s+|LA\s+|LOS\s+|LAS\s+|INSTITUTO\s+|BANCO\s+|SOCIEDAD\s+|SECRETAR[IÍ]A\s+))",
            t,
            maxsplit=1,
            flags=re.IGNORECASE
        )

        if len(partes) != 2:
            return [t]

        izquierda = partes[0].strip(" .,-")
        derecha = partes[1].strip(" .,-")

        if not izquierda or not derecha:
            return [t]

        # Evitar cortar nombres muy cortos o frases raras
        if len(izquierda.split()) >= 3 and len(derecha.split()) >= 2:
            return [izquierda, derecha]

        return [t]
    def limpiar_parentesis_no_estatus(self, texto: str | None) -> str | None:
        if not texto:
            return None

        # Quita paréntesis informativos que NO deben ser demandados
        texto = re.sub(
            r"\((?:ESTADO PROCESAL|EST\.?\s*PROCESAL|TRÁMITE|TRAMITE)\)",
            "",
            texto,
            flags=re.IGNORECASE
        )

        return self.limpiar_espacios(texto)