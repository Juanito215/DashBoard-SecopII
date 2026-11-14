"""
Patrón Builder para Consultas Analíticas y Filtrado Dinámico de SECOP II
Historias de Usuario: HU-08 (Departamento), HU-09 (Municipio en Cascada),
HU-10 (Año de Vigencia 2021-2026), HU-11 (Modalidad), HU-12 (Tipo de Contrato),
HU-13 (Rango de Cuantía Inicial en COP), HU-14 (Entidad Compradora por Nombre o NIT)
y HU-15 (Proveedor / Contratista Adjudicado por Razón Social o Documento)
Caso de Prueba de Aceptación: PA-ALFA-003
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations
import re
import time
from typing import Any
import pandas as pd
from src.utils.text_utils import normalizar_texto_busqueda


class ConsultaSecopBuilder:
    """
    Patrón Builder para ensamblar incrementalmente los filtros analíticos
    sobre el dataset en memoria y construir predicados para MongoDB ($match).
    
    Implementa una interfaz fluida (fluent interface) que permite encadenar
    múltiples criterios de filtrado sin bloquear el hilo principal.
    """

    def __init__(self, df: pd.DataFrame) -> None:
        """
        Inicializa el builder con el DataFrame base.

        Args:
            df (pd.DataFrame): DataFrame con los contratos cargados en memoria.
        """
        self._df_original: pd.DataFrame = df
        self._df_filtrado: pd.DataFrame = df.copy()
        self._query_mongo: dict[str, Any] = {}
        self._tiempo_ms: float = 0.0
        self._filtros_aplicados: list[str] = []

    def filtrar_departamento(self, deptos: list[str] | None) -> ConsultaSecopBuilder:
        """
        HU-08: Aplica filtro por uno o múltiples departamentos.
        
        - Soporta listas de strings.
        - Si deptos es None o lista vacía, no aplica restricción.
        - Filtra vectorialmente en memoria con .isin().
        - Compila el predicado para MongoDB: {"geografia.departamento": {"$in": deptos}}.
        - Registra la latencia de ejecución en milisegundos.

        Args:
            deptos (list[str] | None): Lista de nombres de departamento a filtrar.

        Returns:
            ConsultaSecopBuilder: Instancia actual para encadenamiento fluido.
        """
        if not deptos:
            return self

        # 1. Normalización y depuración de la lista de entrada
        deptos_limpios = [str(d).strip() for d in deptos if d is not None and str(d).strip()]
        if not deptos_limpios:
            return self

        inicio = time.perf_counter()

        # 2. Resolución de la columna de departamento
        col_depto = "departamento" if "departamento" in self._df_filtrado.columns else "geografia.departamento"

        if col_depto in self._df_filtrado.columns:
            # Filtrado vectorizado de alto rendimiento en Pandas
            serie_col = self._df_filtrado[col_depto].astype(str)
            mascara = serie_col.isin(deptos_limpios)

            # Si no hubo coincidencia directa por mayúsculas/minúsculas, intentar normalización
            if not mascara.any():
                deptos_upper = [d.upper() for d in deptos_limpios]
                mascara_upper = serie_col.str.upper().isin(deptos_upper)
                if mascara_upper.any():
                    mascara = mascara_upper

            self._df_filtrado = self._df_filtrado[mascara]

        # 3. Compilación del predicado para MongoDB
        self._query_mongo["geografia.departamento"] = {"$in": deptos_limpios}
        self._filtros_aplicados.append(f"departamento IN {deptos_limpios}")

        # 4. Telemetría de latencia acumulada
        duracion_ms = (time.perf_counter() - inicio) * 1000.0
        self._tiempo_ms += duracion_ms

        return self

    def filtrar_municipio(self, mpios: list[str] | None) -> ConsultaSecopBuilder:
        """
        HU-09: Aplica filtro por uno o múltiples municipios (soporte en cascada).

        - Soporta listas de strings.
        - Si mpios es None o lista vacía, no aplica restricción.
        - Filtra vectorialmente en memoria con .isin().
        - Compila el predicado para MongoDB: {"geografia.municipio": {"$in": mpios_limpios}}.
        - Registra la latencia de ejecución en milisegundos.

        Args:
            mpios (list[str] | None): Lista de nombres de municipio a filtrar.

        Returns:
            ConsultaSecopBuilder: Instancia actual para encadenamiento fluido.
        """
        if not mpios:
            return self

        # 1. Normalización y depuración de la lista de entrada
        mpios_limpios = [str(m).strip() for m in mpios if m is not None and str(m).strip()]
        if not mpios_limpios:
            return self

        inicio = time.perf_counter()

        # 2. Resolución de la columna de municipio (soporte para municipio, ciudad o geografia.municipio)
        col_mpio = None
        for candidata in ["municipio", "ciudad", "geografia.municipio"]:
            if candidata in self._df_filtrado.columns:
                col_mpio = candidata
                break

        if col_mpio is not None:
            serie_col = self._df_filtrado[col_mpio].astype(str)
            mascara = serie_col.isin(mpios_limpios)

            # Si no hubo coincidencia directa por mayúsculas/minúsculas, intentar normalización
            if not mascara.any():
                mpios_upper = [m.upper() for m in mpios_limpios]
                mascara_upper = serie_col.str.upper().isin(mpios_upper)
                if mascara_upper.any():
                    mascara = mascara_upper

            self._df_filtrado = self._df_filtrado[mascara]

        # 3. Compilación del predicado para MongoDB
        self._query_mongo["geografia.municipio"] = {"$in": mpios_limpios}
        self._filtros_aplicados.append(f"municipio IN {mpios_limpios}")

        # 4. Telemetría de latencia acumulada
        duracion_ms = (time.perf_counter() - inicio) * 1000.0
        self._tiempo_ms += duracion_ms

        return self

    def filtrar_anio(
        self, anios: list[int] | tuple[int, int] | set[int] | int | None
    ) -> ConsultaSecopBuilder:
        """
        HU-10: Aplica filtro por año(s) o rango de vigencia fiscal (2021-2026).

        - Soporta tupla de rango continuo: (2021, 2024) -> $gte, $lte.
        - Soporta lista o set discreto: [2022, 2023] -> $in.
        - Soporta entero único: 2022 -> igualdad exacta.
        - Si anios es None o colección vacía, no aplica restricción.
        - Filtra vectorialmente en Pandas y compila el predicado para MongoDB en 'tiempo.anio_vigencia'.
        - Registra la latencia acumulada en milisegundos.

        Args:
            anios: list[int] | tuple[int, int] | set[int] | int | None

        Returns:
            ConsultaSecopBuilder: Instancia actual para encadenamiento fluido.
        """
        if anios is None:
            return self

        # Colección vacía
        if isinstance(anios, (list, tuple, set)) and len(anios) == 0:
            return self

        inicio = time.perf_counter()

        # 1. Resolución de la columna de año
        col_anio = None
        for cand in ["anio_vigencia", "tiempo.anio_vigencia", "ano_firma", "anio"]:
            if cand in self._df_filtrado.columns:
                col_anio = cand
                break

        if col_anio is None:
            for cand_fecha in ["fecha_firma", "fecha_de_firma"]:
                if cand_fecha in self._df_filtrado.columns:
                    self._df_filtrado["anio_vigencia"] = pd.to_datetime(
                        self._df_filtrado[cand_fecha], errors="coerce"
                    ).dt.year.fillna(2022).astype(int)
                    col_anio = "anio_vigencia"
                    break

        if col_anio is not None:
            # Asegurar tipo numérico entero para comparación vectorial
            serie_anio = pd.to_numeric(self._df_filtrado[col_anio], errors="coerce").fillna(0).astype(int)

            # Caso 1: Rango continuo en tupla (min_anio, max_anio)
            if isinstance(anios, tuple) and len(anios) == 2:
                min_a, max_a = int(anios[0]), int(anios[1])
                if min_a > max_a:
                    min_a, max_a = max_a, min_a

                self._df_filtrado = self._df_filtrado[(serie_anio >= min_a) & (serie_anio <= max_a)]
                self._query_mongo["tiempo.anio_vigencia"] = {"$gte": min_a, "$lte": max_a}
                self._filtros_aplicados.append(f"anio_vigencia BETWEEN {min_a} AND {max_a}")

            # Caso 2: Entero único
            elif isinstance(anios, int) and not isinstance(anios, bool):
                val_anio = int(anios)
                self._df_filtrado = self._df_filtrado[serie_anio == val_anio]
                self._query_mongo["tiempo.anio_vigencia"] = val_anio
                self._filtros_aplicados.append(f"anio_vigencia == {val_anio}")

            # Caso 3: Lista discreta o conjunto de años
            elif isinstance(anios, (list, set)):
                anios_limpios = sorted([int(a) for a in anios if a is not None])
                if anios_limpios:
                    self._df_filtrado = self._df_filtrado[serie_anio.isin(anios_limpios)]
                    self._query_mongo["tiempo.anio_vigencia"] = {"$in": anios_limpios}
                    self._filtros_aplicados.append(f"anio_vigencia IN {anios_limpios}")

        # 2. Telemetría de latencia acumulada
        duracion_ms = (time.perf_counter() - inicio) * 1000.0
        self._tiempo_ms += duracion_ms

        return self

    def filtrar_modalidad(
        self, modalidades: list[str] | set[str] | str | None
    ) -> ConsultaSecopBuilder:
        """
        HU-11: Aplica filtro por una o múltiples modalidades de contratación estatal.

        - Soporta list[str], set[str] o str único.
        - Mapea al subdocumento 'clasificacion.modalidad' para MongoDB y
          a la columna correspondiente en Pandas.
        - Si modalidades es vacío o None, no aplica restricción.
        - Registra la latencia acumulada en milisegundos.

        Args:
            modalidades: list[str] | set[str] | str | None

        Returns:
            ConsultaSecopBuilder: Instancia actual para encadenamiento fluido.
        """
        if not modalidades:
            return self

        # Normalizar a lista de cadenas limpias
        if isinstance(modalidades, str):
            mods_limpias = [modalidades.strip()] if modalidades.strip() else []
        else:
            mods_limpias = [str(m).strip() for m in modalidades if m is not None and str(m).strip()]

        if not mods_limpias:
            return self

        inicio = time.perf_counter()

        # 1. Identificar columna en DataFrame plano o BSON deserializado
        col_mod = None
        for cand in ["modalidad", "clasificacion.modalidad", "modalidad_de_contratacion", "tipo_modalidad"]:
            if cand in self._df_filtrado.columns:
                col_mod = cand
                break

        if col_mod is not None:
            serie_col = self._df_filtrado[col_mod].astype(str)
            mascara = serie_col.isin(mods_limpias)

            # Fallback insensible a mayúsculas
            if not mascara.any():
                mods_upper = [m.upper() for m in mods_limpias]
                mascara_upper = serie_col.str.upper().isin(mods_upper)
                if mascara_upper.any():
                    mascara = mascara_upper

            self._df_filtrado = self._df_filtrado[mascara]

        # 2. Predicado estructurado para MongoDB en 'clasificacion.modalidad'
        if len(mods_limpias) == 1:
            self._query_mongo["clasificacion.modalidad"] = mods_limpias[0]
            self._filtros_aplicados.append(f"modalidad == '{mods_limpias[0]}'")
        else:
            self._query_mongo["clasificacion.modalidad"] = {"$in": mods_limpias}
            self._filtros_aplicados.append(f"modalidad IN {mods_limpias}")

        # 3. Telemetría de latencia acumulada
        duracion_ms = (time.perf_counter() - inicio) * 1000.0
        self._tiempo_ms += duracion_ms

        return self

    def con_tipo_contrato(
        self, tipos: list[str] | set[str] | str | None
    ) -> ConsultaSecopBuilder:
        """
        HU-12: Aplica filtro por una o múltiples tipologías contractuales
        (Obra, Prestación de servicios, Suministro, etc.).

        - Soporta list[str], set[str] o str único.
        - Mapea al subdocumento 'clasificacion.tipo_contrato' para MongoDB y
          a la columna correspondiente en Pandas.
        - Si tipos es vacío o None, no restringe los datos.
        - Registra la latencia acumulada en milisegundos.

        Args:
            tipos: list[str] | set[str] | str | None

        Returns:
            ConsultaSecopBuilder: Instancia actual para encadenamiento fluido.
        """
        if not tipos:
            return self

        # Normalizar a lista de cadenas limpias
        if isinstance(tipos, str):
            tipos_limpios = [tipos.strip()] if tipos.strip() else []
        else:
            tipos_limpios = [str(t).strip() for t in tipos if t is not None and str(t).strip()]

        if not tipos_limpios:
            return self

        inicio = time.perf_counter()

        # 1. Identificar columna en DataFrame plano o BSON deserializado
        col_tipo = None
        for cand in ["tipo_contrato", "clasificacion.tipo_contrato", "tipo_de_contrato", "tipo contrato"]:
            if cand in self._df_filtrado.columns:
                col_tipo = cand
                break

        if col_tipo is not None:
            serie_col = self._df_filtrado[col_tipo].astype(str)
            mascara = serie_col.isin(tipos_limpios)

            # Fallback insensible a mayúsculas
            if not mascara.any():
                tipos_upper = [t.upper() for t in tipos_limpios]
                mascara_upper = serie_col.str.upper().isin(tipos_upper)
                if mascara_upper.any():
                    mascara = mascara_upper

            self._df_filtrado = self._df_filtrado[mascara]

        # 2. Predicado estructurado para MongoDB en 'clasificacion.tipo_contrato'
        if len(tipos_limpios) == 1:
            self._query_mongo["clasificacion.tipo_contrato"] = tipos_limpios[0]
            self._filtros_aplicados.append(f"tipo_contrato == '{tipos_limpios[0]}'")
        else:
            self._query_mongo["clasificacion.tipo_contrato"] = {"$in": tipos_limpios}
            self._filtros_aplicados.append(f"tipo_contrato IN {tipos_limpios}")

        # 3. Telemetría de latencia acumulada
        duracion_ms = (time.perf_counter() - inicio) * 1000.0
        self._tiempo_ms += duracion_ms

        return self

    # Alias de compatibilidad semántica (HU-12 Criterio 2)
    def filtrar_tipo_contrato(
        self, tipos: list[str] | set[str] | str | None
    ) -> ConsultaSecopBuilder:
        return self.con_tipo_contrato(tipos)

    def con_rango_cuantia(
        self, min_cop: float | int | None = None, max_cop: float | int | None = None
    ) -> ConsultaSecopBuilder:
        """
        HU-13: Aplica filtro por rango de cuantía inicial (mínimo y/o máximo) en Pesos Colombianos (COP).

        - Soporta float o int para min_cop y max_cop.
        - Mapea al campo numérico 'cuantia_inicial' tanto en Pandas como en MongoDB.
        - Si ambos límites son None, no restringe los datos.
        - Si se definen límites:
            * min y max: {"cuantia_inicial": {"$gte": min_val, "$lte": max_val}}
            * solo min:  {"cuantia_inicial": {"$gte": min_val}}
            * solo max:  {"cuantia_inicial": {"$lte": max_val}}
        - Registra la latencia acumulada en milisegundos.

        Args:
            min_cop: float | int | None
            max_cop: float | int | None

        Returns:
            ConsultaSecopBuilder: Instancia actual para encadenamiento fluido.
        """
        if min_cop is None and max_cop is None:
            return self

        inicio = time.perf_counter()

        col_cuantia = None
        for cand in [
            "cuantia_inicial",
            "valor_del_contrato",
            "cuantia",
            "valor_contrato",
            "monto_contrato",
            "metricas.cuantia_inicial",
        ]:
            if cand in self._df_filtrado.columns:
                col_cuantia = cand
                break

        if col_cuantia is None:
            col_cuantia = "cuantia_inicial"

        if col_cuantia in self._df_filtrado.columns:
            # Asegurar tipo numérico continuo en Pandas
            serie_val = pd.to_numeric(self._df_filtrado[col_cuantia], errors="coerce").fillna(0.0)

            condicion_mongo: dict[str, float] = {}

            if min_cop is not None and float(min_cop) > 0:
                min_val = float(min_cop)
                self._df_filtrado = self._df_filtrado[serie_val >= min_val]
                serie_val = pd.to_numeric(self._df_filtrado[col_cuantia], errors="coerce").fillna(0.0)
                condicion_mongo["$gte"] = min_val

            if max_cop is not None and float(max_cop) > 0:
                max_val = float(max_cop)
                self._df_filtrado = self._df_filtrado[serie_val <= max_val]
                condicion_mongo["$lte"] = max_val

            if condicion_mongo:
                if "cuantia_inicial" in self._query_mongo:
                    self._query_mongo["cuantia_inicial"].update(condicion_mongo)
                else:
                    self._query_mongo["cuantia_inicial"] = condicion_mongo

                if "$gte" in condicion_mongo and "$lte" in condicion_mongo:
                    self._filtros_aplicados.append(
                        f"cuantia_inicial BETWEEN ${condicion_mongo['$gte']:,.0f} AND ${condicion_mongo['$lte']:,.0f} COP"
                    )
                elif "$gte" in condicion_mongo:
                    self._filtros_aplicados.append(f"cuantia_inicial >= ${condicion_mongo['$gte']:,.0f} COP")
                elif "$lte" in condicion_mongo:
                    self._filtros_aplicados.append(f"cuantia_inicial <= ${condicion_mongo['$lte']:,.0f} COP")

        # Telemetría de latencia acumulada
        duracion_ms = (time.perf_counter() - inicio) * 1000.0
        self._tiempo_ms += duracion_ms

        return self

    # Alias de compatibilidad semántica (HU-13 Criterio 2)
    def filtrar_cuantia(
        self, min_cop: float | int | None = None, max_cop: float | int | None = None
    ) -> ConsultaSecopBuilder:
        return self.con_rango_cuantia(min_cop=min_cop, max_cop=max_cop)

    def con_entidad_o_nit(self, query_texto: str | None) -> ConsultaSecopBuilder:
        """
        HU-14: Aplica búsqueda por Nombre o NIT de la Entidad Compradora.

        - Búsqueda insensible a mayúsculas/minúsculas y a acentos/tildes (diacrítica).
        - Admite coincidencias parciales por texto en el nombre de la institución (ej. "hospital")
          o coincidencia exacta/parcial por dígitos en el NIT (ej. "890399045").
        - Si el argumento es None, vacío o solo espacios en blanco, no aplica restricción.
        - Compila a MongoDB:
            {"$or": [
                {"entidad.nombre": {"$regex": patron, "$options": "i"}},
                {"entidad.nit": {"$regex": patron, "$options": "i"}}
            ]}
        - Registra la latencia acumulada en milisegundos.

        Args:
            query_texto (str | None): Término de búsqueda (nombre institucional o NIT).

        Returns:
            ConsultaSecopBuilder: Instancia actual para encadenamiento fluido.
        """
        if query_texto is None:
            return self

        texto_str = str(query_texto).strip()
        if not texto_str:
            return self

        query_norm = normalizar_texto_busqueda(texto_str)
        if not query_norm:
            return self

        inicio = time.perf_counter()

        # 1. Resolución de columnas de nombre de entidad y NIT
        col_nombre = None
        for cand_n in [
            "nombre_entidad", "entidad.nombre", "nombre de la entidad",
            "entidad", "entidad_compradora", "nombre_de_la_entidad"
        ]:
            if cand_n in self._df_filtrado.columns:
                col_nombre = cand_n
                break

        col_nit = None
        for cand_nit in [
            "nit_entidad", "entidad.nit", "nit", "nit de la entidad",
            "documento_entidad", "nit_de_la_entidad"
        ]:
            if cand_nit in self._df_filtrado.columns:
                col_nit = cand_nit
                break

        # Fallbacks si no se encontraron con nombres estándar
        if col_nombre is None:
            for col in self._df_filtrado.columns:
                if "entidad" in col.lower() and "nit" not in col.lower():
                    col_nombre = col
                    break

        if col_nit is None:
            for col in self._df_filtrado.columns:
                if "nit" in col.lower():
                    col_nit = col
                    break

        # 2. Filtrado vectorizado en Pandas
        mascara_total = pd.Series(False, index=self._df_filtrado.index)

        if col_nombre is not None and col_nombre in self._df_filtrado.columns:
            mascara_nombre = (
                self._df_filtrado[col_nombre]
                .astype(str)
                .map(normalizar_texto_busqueda)
                .str.contains(query_norm, regex=False)
            )
            mascara_total = mascara_total | mascara_nombre

        if col_nit is not None and col_nit in self._df_filtrado.columns:
            serie_nit_str = self._df_filtrado[col_nit].astype(str)
            mascara_nit = (
                serie_nit_str
                .map(normalizar_texto_busqueda)
                .str.contains(query_norm, regex=False)
            )
            # Si no hubo coincidencia directa y la consulta es de tipo NIT (numérica / con puntuación de NIT)
            if not mascara_nit.any() and re.match(r"^(nit\s*)?[\d\.\-\s]+$", query_norm):
                query_digits = re.sub(r"[^\d]", "", query_norm)
                if len(query_digits) >= 3:
                    serie_nit_digits = serie_nit_str.str.replace(r"[^\d]", "", regex=True)
                    mascara_nit = serie_nit_digits.str.contains(query_digits, regex=False)
            mascara_total = mascara_total | mascara_nit

        self._df_filtrado = self._df_filtrado[mascara_total]

        # 3. Compilación de predicado para MongoDB ($or)
        patron = texto_str
        self._query_mongo["$or"] = [
            {"entidad.nombre": {"$regex": patron, "$options": "i"}},
            {"entidad.nit": {"$regex": patron, "$options": "i"}},
        ]
        self._filtros_aplicados.append(f"entidad/nit CONTAINS '{patron}'")

        # 4. Telemetría de latencia acumulada
        duracion_ms = (time.perf_counter() - inicio) * 1000.0
        self._tiempo_ms += duracion_ms

        return self

    # Alias de compatibilidad semántica (HU-14 Criterio 3)
    def filtrar_entidad(self, query_texto: str | None) -> ConsultaSecopBuilder:
        """Alias semántico de con_entidad_o_nit."""
        return self.con_entidad_o_nit(query_texto)

    def con_proveedor(self, criterio: str | None) -> ConsultaSecopBuilder:
        """
        HU-15: Aplica búsqueda por Razón Social o Documento del Contratista Adjudicado.

        - Insensible a mayúsculas/minúsculas y acentos (diacrítica).
        - Soporta búsqueda parcial o exacta.
        - Mapea a 'proveedor.nombre_razon_social' y 'proveedor.documento' en Pandas y MongoDB.
        - Si criterio es None, vacío o solo espacios, no aplica restricción.
        - Compila en MongoDB una condición estructurada con $regex y opción 'i'.
        - Registra la latencia acumulada en milisegundos.

        Args:
            criterio (str | None): Razón social o documento de identificación del contratista.

        Returns:
            ConsultaSecopBuilder: Instancia actual para encadenamiento fluido.
        """
        if criterio is None:
            return self

        cadena_original = str(criterio).strip()
        if not cadena_original:
            return self

        criterio_norm = normalizar_texto_busqueda(cadena_original)
        if not criterio_norm:
            return self

        inicio = time.perf_counter()

        # 1. Detección de columnas en memoria (DF plano o estructura BSON)
        col_nombre = None
        for cand_p in [
            "proveedor",
            "proveedor.nombre_razon_social",
            "nombre_razon_social",
            "proveedor_adjudicado",
            "nombre_proveedor",
            "razon_social",
        ]:
            if cand_p in self._df_filtrado.columns:
                col_nombre = cand_p
                break

        col_doc = None
        for cand_d in [
            "documento_proveedor",
            "proveedor.documento",
            "documento",
            "nit_proveedor",
            "identificacion_proveedor",
        ]:
            if cand_d in self._df_filtrado.columns:
                col_doc = cand_d
                break

        if col_nombre is None:
            for col in self._df_filtrado.columns:
                if "proveedor" in col.lower() and "doc" not in col.lower() and "pyme" not in col.lower():
                    col_nombre = col
                    break

        if col_doc is None:
            for col in self._df_filtrado.columns:
                if "proveedor" in col.lower() and "doc" in col.lower():
                    col_doc = col
                    break

        # 2. Filtrado vectorizado en Pandas
        mascara_total = pd.Series(False, index=self._df_filtrado.index)

        if col_nombre is not None and col_nombre in self._df_filtrado.columns:
            serie_nombres = (
                self._df_filtrado[col_nombre]
                .astype(str)
                .map(normalizar_texto_busqueda)
            )
            mascara_nombre = serie_nombres.str.contains(criterio_norm, regex=False, na=False)
            mascara_total = mascara_total | mascara_nombre

        if col_doc is not None and col_doc in self._df_filtrado.columns:
            serie_docs = self._df_filtrado[col_doc].astype(str).str.strip().str.lower()
            mascara_doc = serie_docs.str.contains(criterio_norm, regex=False, na=False)
            if not mascara_doc.any() and re.match(r"^(cc|nit|ce|ti\s*)?[\d\.\-\s]+$", criterio_norm):
                criterio_digits = re.sub(r"[^\d]", "", criterio_norm)
                if len(criterio_digits) >= 3:
                    serie_docs_digits = serie_docs.str.replace(r"[^\d]", "", regex=True)
                    mascara_doc = serie_docs_digits.str.contains(criterio_digits, regex=False, na=False)
            mascara_total = mascara_total | mascara_doc

        self._df_filtrado = self._df_filtrado[mascara_total]

        # 3. Predicado estructurado para MongoDB
        patron_escapado = re.escape(cadena_original)
        condicion_mongo = {
            "$or": [
                {"proveedor.nombre_razon_social": {"$regex": patron_escapado, "$options": "i"}},
                {"proveedor.documento": {"$regex": patron_escapado, "$options": "i"}}
            ]
        }

        if "$and" not in self._query_mongo:
            self._query_mongo["$and"] = []
        self._query_mongo["$and"].append(condicion_mongo)

        self._filtros_aplicados.append(f"proveedor/doc CONTAINS '{cadena_original}'")

        # 4. Telemetría de latencia acumulada
        duracion_ms = (time.perf_counter() - inicio) * 1000.0
        self._tiempo_ms += duracion_ms

        return self

    # Alias de compatibilidad semántica (HU-15 Criterio 3)
    def filtrar_proveedor(self, criterio: str | None) -> ConsultaSecopBuilder:
        """Alias semántico de con_proveedor."""
        return self.con_proveedor(criterio)

    def con_es_pyme(self, solo_pyme: bool | str | None) -> ConsultaSecopBuilder:
        """
        HU-16: Aplica filtro por participación de micro, pequeñas y medianas empresas (PYME).

        - Acepta booleano (True / False), None, o etiquetas de UI ('Todas', 'Solo PYMES', 'No PYMES').
        - Si solo_pyme es None o indica todas las empresas, no aplica restricción.
        - Mapea al campo 'proveedor.es_pyme' en MongoDB y a la columna correspondiente en Pandas.
        - Registra latencia acumulada en milisegundos y actualiza los filtros aplicados.

        Args:
            solo_pyme (bool | str | None): Criterio de filtrado PYME.

        Returns:
            ConsultaSecopBuilder: Instancia actual para encadenamiento fluido.
        """
        if solo_pyme is None:
            return self

        valor_bool: bool | None = None
        if isinstance(solo_pyme, bool):
            valor_bool = solo_pyme
        elif isinstance(solo_pyme, str):
            limpio = solo_pyme.strip().lower()
            if limpio in ["todas", "todas las empresas", "todos", ""]:
                return self
            if limpio in ["solo pymes", "solo pyme", "sí", "si", "true", "pyme", "pymes"]:
                valor_bool = True
            elif limpio in ["no pymes", "no pyme", "no", "false", "gran empresa", "no pymes / gran empresa"]:
                valor_bool = False
            else:
                return self
        else:
            return self

        inicio = time.perf_counter()

        col_pyme = None
        for cand in ["es_pyme", "proveedor.es_pyme", "pyme", "es pyme", "es_mipyme"]:
            if cand in self._df_filtrado.columns:
                col_pyme = cand
                break

        if col_pyme is not None:
            serie = self._df_filtrado[col_pyme]
            if pd.api.types.is_bool_dtype(serie):
                mascara = (serie == valor_bool)
            else:
                mascara = (
                    serie.map(
                        lambda v: str(v).strip().lower() in ["si", "sí", "true", "1", "s", "verdadero", "yes"]
                    )
                    == valor_bool
                )
            self._df_filtrado = self._df_filtrado[mascara]

        self._query_mongo["proveedor.es_pyme"] = valor_bool
        self._filtros_aplicados.append(f"proveedor.es_pyme == {valor_bool}")

        duracion_ms = (time.perf_counter() - inicio) * 1000.0
        self._tiempo_ms += duracion_ms

        return self

    def filtrar_pyme(self, solo_pyme: bool | str | None) -> ConsultaSecopBuilder:
        """Alias semántico de con_es_pyme."""
        return self.con_es_pyme(solo_pyme)

    def con_codigo_unspsc(self, codigo_unspsc: str | None) -> ConsultaSecopBuilder:
        """
        HU-17: Aplica filtro por código completo o familia del clasificador UNSPSC.
        - Soporta búsqueda por prefijo (ej. '72' segmento, '7214' familia, '72141103' producto).
        - Tolera códigos con prefijo 'V1.' proveniente de SECOP II.
        - Mapea al subdocumento 'clasificacion.codigo_unspsc' en MongoDB.
        - Si el argumento es None, vacío o solo espacios, no aplica restricción.
        - Registra la latencia acumulada en milisegundos.

        Args:
            codigo_unspsc (str | None): Código completo de 8 dígitos o prefijo de familia/segmento.

        Returns:
            ConsultaSecopBuilder: Instancia actual para encadenamiento fluido.
        """
        if codigo_unspsc is None:
            return self

        codigo_str = str(codigo_unspsc).strip()
        if not codigo_str:
            return self

        # Limpiar espacios y remover posible prefijo 'V1.' ingresado por el usuario
        codigo_limpio = re.sub(r"^v1\.", "", codigo_str, flags=re.IGNORECASE)
        codigo_limpio = re.sub(r"[^\w]", "", codigo_limpio)

        if not codigo_limpio:
            return self

        inicio = time.perf_counter()

        col_unspsc = None
        for cand in [
            "codigo_unspsc",
            "clasificacion.codigo_unspsc",
            "codigo_de_categoria_principal",
            "codigo_principal_categoria",
            "unspsc",
            "categoria_principal",
        ]:
            if cand in self._df_filtrado.columns:
                col_unspsc = cand
                break

        if col_unspsc is None:
            for col in self._df_filtrado.columns:
                if "unspsc" in col.lower() or "categoria_principal" in col.lower():
                    col_unspsc = col
                    break

        if col_unspsc is not None and col_unspsc in self._df_filtrado.columns:
            # Normalizar columna removiendo 'V1.' si existe para comparar prefijo exacto
            serie_codigos = (
                self._df_filtrado[col_unspsc]
                .astype(str)
                .str.strip()
                .str.replace(r"^[Vv]1\.", "", regex=True)
            )
            mascara = serie_codigos.str.startswith(codigo_limpio, na=False)
            self._df_filtrado = self._df_filtrado[mascara]

        patron_escapado = re.escape(codigo_limpio)
        self._query_mongo["clasificacion.codigo_unspsc"] = {
            "$regex": f"^(V1\\.)?{patron_escapado}",
            "$options": "i",
        }
        self._filtros_aplicados.append(f"clasificacion.codigo_unspsc == '{codigo_limpio}'")

        duracion_ms = (time.perf_counter() - inicio) * 1000.0
        self._tiempo_ms += duracion_ms

        return self

    def filtrar_unspsc(self, codigo_unspsc: str | None) -> ConsultaSecopBuilder:
        """Alias semántico de con_codigo_unspsc."""
        return self.con_codigo_unspsc(codigo_unspsc)


    def reset(self) -> ConsultaSecopBuilder:
        """
        HU-18: Restablece el constructor de consultas a su estado inicial sin filtros activos.
        - Restaura el DataFrame filtrado a partir del DataFrame original en memoria.
        - Limpia por completo el diccionario de consulta $match para MongoDB.
        - Reinicia las métricas de latencia y la lista de filtros aplicados.
        - Permite reutilizar la misma instancia del Builder en ciclos consecutivos.
        
        Returns:
            ConsultaSecopBuilder: Instancia reiniciada.
        """
        self._df_filtrado = self._df_original.copy()
        self._query_mongo = {}
        self._tiempo_ms = 0.0
        self._filtros_aplicados = []
        return self

    def obtener_query_mongo(self) -> dict[str, Any]:
        """Retorna el diccionario $match compilado para MongoDB."""
        return self._query_mongo

    def obtener_dataframe(self) -> pd.DataFrame:
        """Retorna el DataFrame con los filtros aplicados hasta el momento."""
        return self._df_filtrado

    def obtener_tiempo_ms(self) -> float:
        """Retorna la latencia acumulada de las operaciones de filtrado en ms."""
        return round(self._tiempo_ms, 2)

    def obtener_filtros_aplicados(self) -> list[str]:
        """Retorna la lista de descripciones textuales de los filtros activos."""
        return list(self._filtros_aplicados)

    def contar_registros(self) -> int:
        """Retorna la cantidad de contratos resultantes tras los filtros."""
        return len(self._df_filtrado)

    def build(self) -> tuple[pd.DataFrame, dict[str, Any], float]:
        """
        Finaliza la construcción y retorna la tupla de resultados:
        (DataFrame resultante, query MongoDB compilado, latencia en ms)
        """
        return self._df_filtrado, self._query_mongo, round(self._tiempo_ms, 2)
