"""
Pruebas Unitarias y de Rendimiento para el Patrón Builder de Consultas Dinámicas
Historia de Usuario: HU-08 (Filtrado Dinámico por Departamento)
Caso de Prueba de Aceptación: PA-ALFA-003
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations
import time
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.queries.query_builder import ConsultaSecopBuilder


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Fixture con un conjunto de datos sintético y variado para pruebas unitarias."""
    data = {
        "id_contrato": [f"CO1.PCONTR.{i}" for i in range(1, 11)],
        "departamento": [
            "ANTIOQUIA",
            "VALLE DEL CAUCA",
            "CUNDINAMARCA",
            "ANTIOQUIA",
            "SANTANDER",
            "VALLE DEL CAUCA",
            "ATLÁNTICO",
            "BOLÍVAR",
            "ANTIOQUIA",
            "BOYACÁ"
        ],
        "municipio": [
            "MEDELLÍN", "CALI", "BOGOTÁ", "BELLO", "BUCARAMANGA",
            "TULUÁ", "BARRANQUILLA", "CARTAGENA", "ENVIGADO", "TUNJA"
        ],
        "cuantia_inicial": [100.0, 200.0, 300.0, 400.0, 500.0, 600.0, 700.0, 800.0, 900.0, 1000.0],
        "valor_adiciones": [0.0, 50.0, 0.0, 100.0, 0.0, 0.0, 150.0, 0.0, 0.0, 200.0],
        "cuantia_final": [100.0, 250.0, 300.0, 500.0, 500.0, 600.0, 850.0, 800.0, 900.0, 1200.0],
        "anio_vigencia": [2021, 2021, 2022, 2022, 2023, 2023, 2024, 2024, 2025, 2026],
        "modalidad": [
            "CONTRATACIÓN DIRECTA",
            "LICITACIÓN PÚBLICA",
            "CONTRATACIÓN DIRECTA",
            "SELECCIÓN ABREVIADA",
            "MÍNIMA CUANTÍA",
            "CONTRATACIÓN DIRECTA",
            "CONCURSO DE MÉRITOS",
            "RÉGIMEN ESPECIAL",
            "CONTRATACIÓN DIRECTA",
            "LICITACIÓN PÚBLICA"
        ],
        "tipo_contrato": [
            "PRESTACIÓN DE SERVICIOS",
            "OBRA",
            "PRESTACIÓN DE SERVICIOS",
            "SUMINISTRO",
            "PRESTACIÓN DE SERVICIOS",
            "PRESTACIÓN DE SERVICIOS",
            "CONSULTORÍA",
            "ARRENDAMIENTO",
            "COMPRAVENTA",
            "OBRA"
        ],
        "nombre_entidad": [
            "ALCALDÍA DE MEDELLÍN",
            "GOBERNACIÓN DEL VALLE DEL CAUCA",
            "ALCALDÍA MAYOR DE BOGOTÁ",
            "MUNICIPIO DE BELLO",
            "HOSPITAL UNIVERSITARIO DE SANTANDER",
            "ALCALDÍA DE TULUÁ",
            "GOBERNACIÓN DEL ATLÁNTICO",
            "ALCALDÍA DE CARTAGENA",
            "HOSPITAL MANUEL URIBE ÁNGEL",
            "GOBERNACIÓN DE BOYACÁ"
        ],
        "nit_entidad": [
            "890905211",
            "890399010",
            "899999061",
            "890980136",
            "890200106",
            "890399045",
            "890102006",
            "890480184",
            "890900501",
            "891800498"
        ],
        "proveedor": [
            "CONSORCIO VIAL DEL NORTE",
            "INGENIERÍA Y CONSTRUCCIONES SAS",
            "SOLUCIONES TECNOLÓGICAS DE COLOMBIA SAS",
            "SUMINISTROS Y DOTACIONES SAS",
            "DISTRIBUCIONES MÉDICAS DE COLOMBIA LTDA",
            "SEBASTIÁN RIVERA MARTÍNEZ",
            "INTERVENTORÍAS DEL CARIBE SAS",
            "INMOBILIARIA LA HEROICA SAS",
            "EQUIPOS DE COMPUTO SAS",
            "CONSTRUCTORA BOYACENSE SAS"
        ],
        "documento_proveedor": [
            "901234567",
            "900876543",
            "900111222",
            "900333444",
            "900555666",
            "1036640178",
            "900777888",
            "900999000",
            "900222333",
            "900444555"
        ],
        "estado": [
            "Celebrado",
            "En ejecución",
            "Liquidado",
            "Terminado",
            "Celebrado",
            "En ejecución",
            "Liquidado",
            "Terminado",
            "Celebrado",
            "En ejecución"
        ]
    }
    return pd.DataFrame(data)


@pytest.fixture
def real_10k_dataframe() -> pd.DataFrame:
    """Fixture que carga la muestra real de 10.000 contratos de SECOP II."""
    ruta = Path("data") / "raw" / "secop muestra 10k 2022.csv"
    if not ruta.exists():
        ruta = Path("secop muestra 10k 2022.csv")
    if not ruta.exists():
        pytest.skip(f"Dataset no encontrado en {ruta.resolve()}")
    return pd.read_csv(ruta, low_memory=False)


def test_builder_filtrar_un_departamento(sample_dataframe: pd.DataFrame):
    """
    HU-08: Verifica el filtrado por un único departamento.
    - Asegura que sólo queden registros de dicho departamento.
    - Asegura que el predicado de MongoDB se compile correctamente.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, latencia_ms = builder.filtrar_departamento(["ANTIOQUIA"]).build()

    assert len(resultado) == 3
    assert set(resultado["departamento"].unique()) == {"ANTIOQUIA"}
    assert query_mongo == {"geografia.departamento": {"$in": ["ANTIOQUIA"]}}
    assert latencia_ms >= 0.0


def test_builder_filtrar_multiples_departamentos(sample_dataframe: pd.DataFrame):
    """
    HU-08: Verifica el filtrado por una lista con múltiples departamentos.
    - Asegura que el DataFrame contenga únicamente los departamentos seleccionados.
    - Asegura que el predicado de MongoDB contenga todos los elementos en el operador $in.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    deptos = ["VALLE DEL CAUCA", "CUNDINAMARCA"]
    resultado, query_mongo, _ = builder.filtrar_departamento(deptos).build()

    assert len(resultado) == 3  # 2 de Valle del Cauca + 1 de Cundinamarca
    assert set(resultado["departamento"].unique()) == {"VALLE DEL CAUCA", "CUNDINAMARCA"}
    assert query_mongo == {"geografia.departamento": {"$in": deptos}}


def test_builder_departamentos_vacio_o_none(sample_dataframe: pd.DataFrame):
    """
    HU-08: Si la lista de departamentos está vacía o es None:
    - No se deben alterar los datos (retorna el 100% de los registros).
    - No se deben registrar restricciones vacías en query_mongo.
    """
    # Prueba con None
    builder_none = ConsultaSecopBuilder(sample_dataframe)
    res_none, q_none, _ = builder_none.filtrar_departamento(None).build()
    assert len(res_none) == len(sample_dataframe)
    assert q_none == {}

    # Prueba con lista vacía
    builder_empty = ConsultaSecopBuilder(sample_dataframe)
    res_empty, q_empty, _ = builder_empty.filtrar_departamento([]).build()
    assert len(res_empty) == len(sample_dataframe)
    assert q_empty == {}


def test_builder_departamento_inexistente(sample_dataframe: pd.DataFrame):
    """
    HU-08: Verifica el comportamiento cuando se consulta un departamento que no existe.
    - Debe retornar un DataFrame vacío sin lanzar excepciones.
    - Debe compilar el predicado en query_mongo.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, _ = builder.filtrar_departamento(["DEPARTAMENTO_FANTASMA_123"]).build()

    assert len(resultado) == 0
    assert query_mongo == {"geografia.departamento": {"$in": ["DEPARTAMENTO_FANTASMA_123"]}}


def test_builder_query_mongo_compilado(sample_dataframe: pd.DataFrame):
    """
    HU-08: Verifica que obtener_query_mongo() exponga el predicado BSON $match generado.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    builder.filtrar_departamento(["SANTANDER", "BOYACÁ"])
    q_mongo = builder.obtener_query_mongo()

    assert "geografia.departamento" in q_mongo
    assert q_mongo["geografia.departamento"]["$in"] == ["SANTANDER", "BOYACÁ"]


def test_builder_fluent_interface_chaining(sample_dataframe: pd.DataFrame):
    """
    HU-08: Verifica que los métodos del builder sean fluidos y encadenables (Fluent Interface).
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    retorno = builder.filtrar_departamento(["BOLÍVAR"])

    assert retorno is builder  # Retorna self para encadenamiento
    df_res, _, _ = retorno.build()
    assert len(df_res) == 1
    assert df_res.iloc[0]["departamento"] == "BOLÍVAR"


def test_builder_reset(sample_dataframe: pd.DataFrame):
    """
    HU-08: Verifica que reset() restablezca el estado al original sin restricciones.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    builder.filtrar_departamento(["ANTIOQUIA"])
    assert builder.contar_registros() == 3
    assert len(builder.obtener_query_mongo()) > 0

    builder.reset()
    assert builder.contar_registros() == len(sample_dataframe)
    assert builder.obtener_query_mongo() == {}
    assert builder.obtener_tiempo_ms() == 0.0


def test_builder_limpieza_espacios_y_valores_vacios(sample_dataframe: pd.DataFrame):
    """
    HU-08: Verifica que elementos con espacios accidentales o vacíos se limpien correctamente.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    lista_con_ruido = ["  ANTIOQUIA  ", "", "   ", None]
    resultado, query_mongo, _ = builder.filtrar_departamento(lista_con_ruido).build()

    assert len(resultado) == 3
    assert set(resultado["departamento"].unique()) == {"ANTIOQUIA"}
    assert query_mongo == {"geografia.departamento": {"$in": ["ANTIOQUIA"]}}


def test_selector_alfabetico_sin_duplicados_ni_nulos(real_10k_dataframe: pd.DataFrame):
    """
    HU-08: Criterio 1:
    - Lista de departamentos extraída dinámicamente ordenada estrictamente A-Z.
    - Cero valores nulos.
    - Cero duplicados.
    """
    col = "departamento" if "departamento" in real_10k_dataframe.columns else "geografia.departamento"
    deptos_extraidos = sorted(list({
        str(val).strip() for val in real_10k_dataframe[col].dropna().unique()
        if str(val).strip() and str(val).strip().upper() not in ["NAN", "NONE", "NULL"]
    }))

    # 1. Sin duplicados
    assert len(deptos_extraidos) == len(set(deptos_extraidos))
    # 2. Sin nulos ni cadenas vacías
    assert all(d for d in deptos_extraidos)
    assert "NAN" not in [d.upper() for d in deptos_extraidos]
    # 3. Estrictamente ordenado A-Z
    assert deptos_extraidos == sorted(deptos_extraidos)
    # 4. Contiene departamentos colombianos clave
    assert "ANTIOQUIA" in deptos_extraidos
    assert "VALLE DEL CAUCA" in deptos_extraidos
    assert "SANTANDER" in deptos_extraidos


def test_rendimiento_filtrado_menor_500ms(real_10k_dataframe: pd.DataFrame):
    """
    HU-08 / Regla 4 / PA-ALFA-003:
    Verifica que el filtrado sobre 10.000 contratos tome menos de 500 ms (ampliamente < 1.500 ms).
    """
    builder = ConsultaSecopBuilder(real_10k_dataframe)
    deptos = ["ANTIOQUIA", "VALLE DEL CAUCA", "BOGOTÁ D.C.", "CUNDINAMARCA"]

    inicio = time.perf_counter()
    df_filtrado, query_mongo, latencia_ms = builder.filtrar_departamento(deptos).build()
    duracion_total_ms = (time.perf_counter() - inicio) * 1000.0

    # Asegura rendimiento < 500 ms
    assert duracion_total_ms < 500.0, f"El filtrado tardó {duracion_total_ms:.2f} ms (debe ser < 500 ms)"
    assert len(df_filtrado) > 0
    assert "geografia.departamento" in query_mongo


def test_apptest_filtrado_departamentos_ui():
    """
    HU-08 / PA-ALFA-003: Prueba de integración UI con Streamlit AppTest:
    Verifica que un usuario con rol 'Analista_BI' pueda acceder a la pestaña de consultas,
    interactuar con el multiselect de departamentos y ver la telemetría operativa.
    """
    from streamlit.testing.v1 import AppTest
    from src.database.data_repository import DataRepositorySingleton

    # Asegurar que el repositorio tenga datos cargados
    repo = DataRepositorySingleton.get_instance()
    repo.cargar_fuente()

    ruta_app = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(ruta_app).run()

    # Iniciar sesión como Analista
    at.text_input[0].input("analista@secopanalytics.gov.co")
    at.text_input[1].input("Secop2026*")
    at.button[0].click().run()

    assert at.session_state.get("autenticado") is True
    assert len(at.exception) == 0

    # Navegar al Explorador de Contratos en la barra lateral
    if at.sidebar.radio:
        at.sidebar.radio[0].set_value("Explorador de Contratos").run()

    # Verificar presencia de multiselect
    assert len(at.multiselect) >= 1
    multiselect_depto = at.multiselect[0]
    assert "ANTIOQUIA" in multiselect_depto.options
    assert "VALLE DEL CAUCA" in multiselect_depto.options

    # Seleccionar Antioquia
    multiselect_depto.select("ANTIOQUIA").run()
    assert len(at.exception) == 0


# ==============================================================================
# PRUEBAS UNITARIAS, DE INTEGRACIÓN Y RENDIMIENTO PARA HU-09 (MUNICIPIOS EN CASCADA)
# ==============================================================================

def test_builder_filtrar_un_municipio(sample_dataframe: pd.DataFrame):
    """
    HU-09: Verifica el filtrado por un único municipio.
    - Asegura que sólo queden registros del municipio seleccionado.
    - Asegura que el predicado de MongoDB compile {'geografia.municipio': {'$in': [mpio]}}.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, latencia_ms = builder.filtrar_municipio(["MEDELLÍN"]).build()

    assert len(resultado) == 1
    assert resultado.iloc[0]["municipio"] == "MEDELLÍN"
    assert query_mongo == {"geografia.municipio": {"$in": ["MEDELLÍN"]}}
    assert latencia_ms >= 0.0


def test_builder_filtrar_multiples_municipios(sample_dataframe: pd.DataFrame):
    """
    HU-09: Verifica el filtrado por una lista con múltiples municipios.
    - Asegura que el DataFrame contenga únicamente los municipios seleccionados.
    - Asegura que el predicado de MongoDB contenga todos los municipios solicitados.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    mpios = ["MEDELLÍN", "CALI", "TULUÁ"]
    resultado, query_mongo, _ = builder.filtrar_municipio(mpios).build()

    assert len(resultado) == 3
    assert set(resultado["municipio"].unique()) == {"MEDELLÍN", "CALI", "TULUÁ"}
    assert query_mongo == {"geografia.municipio": {"$in": mpios}}


def test_builder_municipios_vacio_o_none(sample_dataframe: pd.DataFrame):
    """
    HU-09: Si la lista de municipios está vacía o es None:
    - No se deben alterar los datos.
    - No se deben registrar restricciones vacías en query_mongo.
    """
    builder_none = ConsultaSecopBuilder(sample_dataframe)
    res_none, q_none, _ = builder_none.filtrar_municipio(None).build()
    assert len(res_none) == len(sample_dataframe)
    assert q_none == {}

    builder_empty = ConsultaSecopBuilder(sample_dataframe)
    res_empty, q_empty, _ = builder_empty.filtrar_municipio([]).build()
    assert len(res_empty) == len(sample_dataframe)
    assert q_empty == {}


def test_builder_municipio_inexistente(sample_dataframe: pd.DataFrame):
    """
    HU-09: Consulta de un municipio inexistente retorna DataFrame vacío sin excepciones.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, _ = builder.filtrar_municipio(["MUNICIPIO_FANTASMA_456"]).build()

    assert len(resultado) == 0
    assert query_mongo == {"geografia.municipio": {"$in": ["MUNICIPIO_FANTASMA_456"]}}


def test_builder_encadenamiento_cascada_departamento_y_municipio(sample_dataframe: pd.DataFrame):
    """
    HU-09 / Criterio 2: Verifica el encadenamiento fluido en cascada:
    .filtrar_departamento(['VALLE DEL CAUCA']).filtrar_municipio(['TULUÁ'])
    - Retorna exactamente el contrato que cumple ambas condiciones.
    - Compila ambos filtros en query_mongo para MongoDB.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, _ = (
        builder
        .filtrar_departamento(["VALLE DEL CAUCA"])
        .filtrar_municipio(["TULUÁ"])
        .build()
    )

    assert len(resultado) == 1
    assert resultado.iloc[0]["departamento"] == "VALLE DEL CAUCA"
    assert resultado.iloc[0]["municipio"] == "TULUÁ"
    assert query_mongo == {
        "geografia.departamento": {"$in": ["VALLE DEL CAUCA"]},
        "geografia.municipio": {"$in": ["TULUÁ"]}
    }


def test_builder_cascada_interseccion_incompatible(sample_dataframe: pd.DataFrame):
    """
    HU-09: Si se selecciona un municipio que no pertenece al departamento filtrado,
    la intersección resultante debe ser vacía (0 contratos) sin producir excepciones.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, _ = (
        builder
        .filtrar_departamento(["VALLE DEL CAUCA"])
        .filtrar_municipio(["MEDELLÍN"])  # Medellín pertenece a Antioquia
        .build()
    )

    assert len(resultado) == 0
    assert "geografia.departamento" in query_mongo
    assert "geografia.municipio" in query_mongo


def test_builder_limpieza_espacios_municipios(sample_dataframe: pd.DataFrame):
    """
    HU-09: Normaliza y descarta espacios en blanco y valores vacíos en la lista de municipios.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    lista_con_ruido = ["  CALI  ", "", "   ", None]
    resultado, query_mongo, _ = builder.filtrar_municipio(lista_con_ruido).build()

    assert len(resultado) == 1
    assert resultado.iloc[0]["municipio"] == "CALI"
    assert query_mongo == {"geografia.municipio": {"$in": ["CALI"]}}


def test_extraccion_cascada_municipios_segun_departamento(real_10k_dataframe: pd.DataFrame):
    """
    HU-09 / Criterio 1:
    - Cuando se selecciona 'VALLE DEL CAUCA', los municipios extraídos pertenecen únicamente al Valle.
    - La lista está estrictamente ordenada A-Z y sin valores nulos ni vacíos.
    - Cuando no hay departamento seleccionado, lista todos los municipios del dataset.
    """
    col_dep = "departamento" if "departamento" in real_10k_dataframe.columns else "geografia.departamento"
    col_mpio = "ciudad" if "ciudad" in real_10k_dataframe.columns else "municipio"

    # 1. Sin filtro departamental: totalidad de municipios únicos
    todos_mpios = sorted(list({
        str(val).strip() for val in real_10k_dataframe[col_mpio].dropna().unique()
        if str(val).strip() and str(val).strip().upper() not in ["NAN", "NONE", "NULL", "NO REGISTRADO"]
    }))
    assert len(todos_mpios) > 50
    assert todos_mpios == sorted(todos_mpios)

    # 2. Con filtro departamental: acotado al Valle del Cauca
    df_valle = real_10k_dataframe[real_10k_dataframe[col_dep] == "VALLE DEL CAUCA"]
    mpios_valle = sorted(list({
        str(val).strip() for val in df_valle[col_mpio].dropna().unique()
        if str(val).strip() and str(val).strip().upper() not in ["NAN", "NONE", "NULL", "NO REGISTRADO"]
    }))

    assert len(mpios_valle) < len(todos_mpios)
    assert "CALI" in mpios_valle
    assert "TULUÁ" in mpios_valle
    assert "MEDELLÍN" not in mpios_valle  # Medellín no es de Valle del Cauca
    assert mpios_valle == sorted(mpios_valle)


def test_rendimiento_cascada_menor_500ms(real_10k_dataframe: pd.DataFrame):
    """
    HU-09 / Regla 4 / PA-ALFA-003:
    Verifica que la consulta encadenada departamento + municipio sobre 10.000 contratos
    se resuelva en menos de 500 ms (< 1.500 ms de acuerdo a la Regla 4).
    """
    builder = ConsultaSecopBuilder(real_10k_dataframe)
    inicio = time.perf_counter()
    df_res, query_mongo, latencia_ms = (
        builder
        .filtrar_departamento(["VALLE DEL CAUCA", "ANTIOQUIA"])
        .filtrar_municipio(["CALI", "MEDELLÍN", "TULUÁ"])
        .build()
    )
    duracion_ms = (time.perf_counter() - inicio) * 1000.0

    assert duracion_ms < 500.0, f"Filtrado en cascada excedió los 500 ms ({duracion_ms:.2f} ms)"
    assert len(df_res) > 0
    assert "geografia.departamento" in query_mongo
    assert "geografia.municipio" in query_mongo


def test_apptest_filtrado_cascada_municipios_ui():
    """
    HU-09 / PA-ALFA-003: Prueba de integración UI con Streamlit AppTest:
    Verifica la reactividad en cascada:
    1. Iniciar sesión como Analista_BI
    2. Comprobar selectores de Departamento y Municipio
    3. Seleccionar 'VALLE DEL CAUCA'
    4. Comprobar que las opciones del selector de Municipios se acotan al Valle del Cauca
    5. Seleccionar 'TULUÁ' y verificar visualización sin excepciones.
    """
    from streamlit.testing.v1 import AppTest
    from src.database.data_repository import DataRepositorySingleton

    repo = DataRepositorySingleton.get_instance()
    repo.cargar_fuente()

    ruta_app = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(ruta_app).run()

    # Iniciar sesión
    at.text_input[0].input("analista@secopanalytics.gov.co")
    at.text_input[1].input("Secop2026*")
    at.button[0].click().run()

    assert at.session_state.get("autenticado") is True
    assert len(at.exception) == 0

    # Navegar al Explorador de Contratos en la barra lateral
    if at.sidebar.radio:
        at.sidebar.radio[0].set_value("Explorador de Contratos").run()

    # Comprobar componentes multiselect
    assert len(at.multiselect) >= 2
    ms_depto = at.multiselect[0]
    ms_mpio = at.multiselect[1]

    # Estado inicial: opciones de municipio incluyen ciudades de diversos departamentos
    assert "MEDELLÍN" in ms_mpio.options
    assert "TULUÁ" in ms_mpio.options

    # Filtrar por Valle del Cauca
    ms_depto.select("VALLE DEL CAUCA").run()
    assert len(at.exception) == 0

    # Tras filtrar por Valle, el multiselect de municipio debe acotarse en cascada
    ms_mpio_cascada = at.multiselect[1]
    assert "TULUÁ" in ms_mpio_cascada.options
    assert "CALI" in ms_mpio_cascada.options
    assert "MEDELLÍN" not in ms_mpio_cascada.options  # Descartado reactivamente

    # Seleccionar Tuluá
    ms_mpio_cascada.select("TULUÁ").run()
    assert len(at.exception) == 0


# ==============================================================================
# PRUEBAS UNITARIAS, DE INTEGRACIÓN Y RENDIMIENTO PARA HU-10 (AÑO DE VIGENCIA)
# ==============================================================================

def test_builder_filtrar_anio_entero_unico(sample_dataframe: pd.DataFrame):
    """
    HU-10: Filtrado por un entero único (ej. 2022).
    - Retorna únicamente los contratos correspondientes a ese año fiscal.
    - Compila en MongoDB: {'tiempo.anio_vigencia': 2022}.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, latencia_ms = builder.filtrar_anio(2022).build()

    assert len(resultado) == 2
    assert set(resultado["anio_vigencia"].unique()) == {2022}
    assert query_mongo == {"tiempo.anio_vigencia": 2022}
    assert latencia_ms >= 0.0


def test_builder_filtrar_anio_lista_discreta(sample_dataframe: pd.DataFrame):
    """
    HU-10: Filtrado por lista discreta de años (ej. [2021, 2025]).
    - Retorna únicamente contratos de esos años específicos (sin incluir intermedios).
    - Compila en MongoDB: {'tiempo.anio_vigencia': {'$in': [2021, 2025]}}.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    anios = [2021, 2025]
    resultado, query_mongo, _ = builder.filtrar_anio(anios).build()

    assert len(resultado) == 3  # 2 contratos de 2021 + 1 contrato de 2025
    assert set(resultado["anio_vigencia"].unique()) == {2021, 2025}
    assert query_mongo == {"tiempo.anio_vigencia": {"$in": anios}}


def test_builder_filtrar_anio_rango_tupla(sample_dataframe: pd.DataFrame):
    """
    HU-10: Filtrado continuo por tupla de rango (min_a, max_a) (ej. (2022, 2024)).
    - Retorna contratos con min_a <= anio_vigencia <= max_a.
    - Compila en MongoDB: {'tiempo.anio_vigencia': {'$gte': 2022, '$lte': 2024}}.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    rango = (2022, 2024)
    resultado, query_mongo, _ = builder.filtrar_anio(rango).build()

    # Contratos de 2022 (2), 2023 (2) y 2024 (2) = 6 contratos
    assert len(resultado) == 6
    assert set(resultado["anio_vigencia"].unique()) == {2022, 2023, 2024}
    assert query_mongo == {"tiempo.anio_vigencia": {"$gte": 2022, "$lte": 2024}}


def test_builder_filtrar_anio_none_o_vacio(sample_dataframe: pd.DataFrame):
    """
    HU-10: Si anios es None, lista vacía o tupla vacía:
    - No muta los datos ni altera el dataset original.
    - No añade restricciones vacías a query_mongo.
    """
    builder_none = ConsultaSecopBuilder(sample_dataframe)
    res_none, q_none, _ = builder_none.filtrar_anio(None).build()
    assert len(res_none) == len(sample_dataframe)
    assert q_none == {}

    builder_empty = ConsultaSecopBuilder(sample_dataframe)
    res_empty, q_empty, _ = builder_empty.filtrar_anio([]).build()
    assert len(res_empty) == len(sample_dataframe)
    assert q_empty == {}


def test_builder_filtrar_anio_fuera_de_rango(sample_dataframe: pd.DataFrame):
    """
    HU-10: Si se consulta un año sin contratos registrados (ej. 2030):
    - Retorna DataFrame vacío sin lanzar excepciones.
    - Compila la condición en query_mongo.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, _ = builder.filtrar_anio(2030).build()

    assert len(resultado) == 0
    assert query_mongo == {"tiempo.anio_vigencia": 2030}


def test_builder_encadenamiento_completo_depto_mpio_anio(sample_dataframe: pd.DataFrame):
    """
    HU-08 + HU-09 + HU-10:
    Verifica el encadenamiento fluido multi-criterio completo:
    .filtrar_departamento(['VALLE DEL CAUCA'])
    .filtrar_municipio(['TULUÁ'])
    .filtrar_anio(2023)
    - Localiza el contrato exacto que satisface las 3 dimensiones simultáneamente.
    - Compila el predicado completo para MongoDB con 'geografia' y 'tiempo'.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, _ = (
        builder
        .filtrar_departamento(["VALLE DEL CAUCA"])
        .filtrar_municipio(["TULUÁ"])
        .filtrar_anio(2023)
        .build()
    )

    assert len(resultado) == 1
    fila = resultado.iloc[0]
    assert fila["departamento"] == "VALLE DEL CAUCA"
    assert fila["municipio"] == "TULUÁ"
    assert fila["anio_vigencia"] == 2023

    assert query_mongo == {
        "geografia.departamento": {"$in": ["VALLE DEL CAUCA"]},
        "geografia.municipio": {"$in": ["TULUÁ"]},
        "tiempo.anio_vigencia": 2023
    }


def test_rendimiento_filtrado_temporal_menor_500ms(real_10k_dataframe: pd.DataFrame):
    """
    HU-10 / Regla 4 / PA-ALFA-003:
    Verifica que el filtrado temporal sobre 10.000 contratos se ejecute en menos de 500 ms (< 1.500 ms).
    """
    builder = ConsultaSecopBuilder(real_10k_dataframe)
    inicio = time.perf_counter()
    df_res, query_mongo, latencia_ms = builder.filtrar_anio((2021, 2023)).build()
    duracion_ms = (time.perf_counter() - inicio) * 1000.0

    assert duracion_ms < 500.0, f"Filtrado temporal superó 500 ms ({duracion_ms:.2f} ms)"
    assert len(df_res) > 0
    assert "tiempo.anio_vigencia" in query_mongo


def test_apptest_filtrado_temporal_ui():
    """
    HU-10 / PA-ALFA-003: Prueba de integración UI con Streamlit AppTest:
    Verifica la interacción con los controles temporales:
    1. Iniciar sesión como Analista_BI
    2. Comprobar existencia del slider o selector de años (2021-2026)
    3. Ajustar el control temporal y comprobar la ejecución sin excepciones.
    """
    from streamlit.testing.v1 import AppTest
    from src.database.data_repository import DataRepositorySingleton

    repo = DataRepositorySingleton.get_instance()
    repo.cargar_fuente()

    ruta_app = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(ruta_app).run()

    # Iniciar sesión
    at.text_input[0].input("analista@secopanalytics.gov.co")
    at.text_input[1].input("Secop2026*")
    at.button[0].click().run()

    assert at.session_state.get("autenticado") is True
    assert len(at.exception) == 0

    # Navegar al Explorador de Contratos en la barra lateral
    if at.sidebar.radio:
        at.sidebar.radio[0].set_value("Explorador de Contratos").run()

    # Comprobar presencia de slider temporal
    assert len(at.slider) >= 1
    slider_anio = at.slider[0]
    assert slider_anio.min == 2021
    assert slider_anio.max == 2026

    # Modificar slider a rango (2021, 2023)
    slider_anio.set_value((2021, 2023)).run()
    assert len(at.exception) == 0


# ==============================================================================
# PRUEBAS UNITARIAS, DE INTEGRACIÓN Y RENDIMIENTO PARA HU-11 (MODALIDAD DE SELECCIÓN)
# ==============================================================================

def test_builder_filtrar_modalidad_str_unico(sample_dataframe: pd.DataFrame):
    """
    HU-11: Filtrado por string único de modalidad.
    - Retorna contratos con esa modalidad.
    - Compila en MongoDB: {'clasificacion.modalidad': 'CONTRATACIÓN DIRECTA'}.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, latencia_ms = builder.filtrar_modalidad("CONTRATACIÓN DIRECTA").build()

    assert len(resultado) == 4
    assert set(resultado["modalidad"].unique()) == {"CONTRATACIÓN DIRECTA"}
    assert query_mongo == {"clasificacion.modalidad": "CONTRATACIÓN DIRECTA"}
    assert latencia_ms >= 0.0


def test_builder_filtrar_modalidad_lista_un_elemento(sample_dataframe: pd.DataFrame):
    """
    HU-11: Filtrado por lista de un solo elemento.
    - Compila en MongoDB con igualdad directa al valor único.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, _ = builder.filtrar_modalidad(["LICITACIÓN PÚBLICA"]).build()

    assert len(resultado) == 2
    assert set(resultado["modalidad"].unique()) == {"LICITACIÓN PÚBLICA"}
    assert query_mongo == {"clasificacion.modalidad": "LICITACIÓN PÚBLICA"}


def test_builder_filtrar_modalidad_multiples(sample_dataframe: pd.DataFrame):
    """
    HU-11: Filtrado por lista con múltiples modalidades.
    - Retorna contratos que correspondan a cualquiera de las modalidades.
    - Compila en MongoDB con operador $in: {'clasificacion.modalidad': {'$in': [...]}}.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    mods = ["CONTRATACIÓN DIRECTA", "LICITACIÓN PÚBLICA"]
    resultado, query_mongo, _ = builder.filtrar_modalidad(mods).build()

    assert len(resultado) == 6  # 4 de Contratación Directa + 2 de Licitación Pública
    assert set(resultado["modalidad"].unique()) == {"CONTRATACIÓN DIRECTA", "LICITACIÓN PÚBLICA"}
    assert query_mongo == {"clasificacion.modalidad": {"$in": mods}}


def test_builder_filtrar_modalidad_none_o_vacio(sample_dataframe: pd.DataFrame):
    """
    HU-11: Si modalidades es None, lista vacía o string en blanco:
    - No muta los datos ni altera el dataset original.
    - No añade restricciones a query_mongo.
    """
    builder_none = ConsultaSecopBuilder(sample_dataframe)
    res_none, q_none, _ = builder_none.filtrar_modalidad(None).build()
    assert len(res_none) == len(sample_dataframe)
    assert q_none == {}

    builder_empty = ConsultaSecopBuilder(sample_dataframe)
    res_empty, q_empty, _ = builder_empty.filtrar_modalidad([]).build()
    assert len(res_empty) == len(sample_dataframe)
    assert q_empty == {}

    builder_blank = ConsultaSecopBuilder(sample_dataframe)
    res_blank, q_blank, _ = builder_blank.filtrar_modalidad("   ").build()
    assert len(res_blank) == len(sample_dataframe)
    assert q_blank == {}


def test_builder_filtrar_modalidad_inexistente(sample_dataframe: pd.DataFrame):
    """
    HU-11: Si se consulta una modalidad inexistente:
    - Retorna DataFrame vacío sin lanzar excepciones.
    - Compila la condición en query_mongo.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, _ = builder.filtrar_modalidad("MODALIDAD_FANTASMA_789").build()

    assert len(resultado) == 0
    assert query_mongo == {"clasificacion.modalidad": "MODALIDAD_FANTASMA_789"}


def test_builder_encadenamiento_completo_4_dimensiones(sample_dataframe: pd.DataFrame):
    """
    HU-08 + HU-09 + HU-10 + HU-11:
    Verifica el encadenamiento fluido multi-criterio en 4 dimensiones:
    1. Departamento: 'VALLE DEL CAUCA'
    2. Municipio: 'TULUÁ'
    3. Año de Vigencia: 2023
    4. Modalidad: 'CONTRATACIÓN DIRECTA'
    - Retorna exactamente el contrato que cumple las 4 restricciones.
    - Compila el predicado completo para MongoDB con 'geografia', 'tiempo' y 'clasificacion'.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, latencia_ms = (
        builder
        .filtrar_departamento(["VALLE DEL CAUCA"])
        .filtrar_municipio(["TULUÁ"])
        .filtrar_anio(2023)
        .filtrar_modalidad("CONTRATACIÓN DIRECTA")
        .build()
    )

    assert len(resultado) == 1
    fila = resultado.iloc[0]
    assert fila["departamento"] == "VALLE DEL CAUCA"
    assert fila["municipio"] == "TULUÁ"
    assert fila["anio_vigencia"] == 2023
    assert fila["modalidad"] == "CONTRATACIÓN DIRECTA"

    assert query_mongo == {
        "geografia.departamento": {"$in": ["VALLE DEL CAUCA"]},
        "geografia.municipio": {"$in": ["TULUÁ"]},
        "tiempo.anio_vigencia": 2023,
        "clasificacion.modalidad": "CONTRATACIÓN DIRECTA"
    }
    assert latencia_ms >= 0.0


def test_rendimiento_filtrado_modalidad_menor_500ms(real_10k_dataframe: pd.DataFrame):
    """
    HU-11 / Regla 4 / PA-ALFA-003:
    Verifica que el filtrado por modalidad sobre 10.000 contratos se ejecute en menos de 500 ms (< 1.500 ms).
    """
    builder = ConsultaSecopBuilder(real_10k_dataframe)
    inicio = time.perf_counter()
    df_res, query_mongo, latencia_ms = builder.filtrar_modalidad("Contratación directa").build()
    duracion_ms = (time.perf_counter() - inicio) * 1000.0

    assert duracion_ms < 500.0, f"Filtrado por modalidad superó 500 ms ({duracion_ms:.2f} ms)"
    assert len(df_res) > 0
    assert "clasificacion.modalidad" in query_mongo


def test_apptest_filtrado_modalidad_ui():
    """
    HU-11 / PA-ALFA-003: Prueba de integración UI con Streamlit AppTest:
    Verifica la interacción con el selector de modalidades:
    1. Iniciar sesión como Analista_BI
    2. Comprobar presencia del multiselect de modalidades
    3. Seleccionar 'Contratación directa'
    4. Comprobar que no se lanzan excepciones y la aplicación se recalcula reactivamente.
    """
    from streamlit.testing.v1 import AppTest
    from src.database.data_repository import DataRepositorySingleton

    repo = DataRepositorySingleton.get_instance()
    repo.cargar_fuente()

    ruta_app = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(ruta_app).run()

    # Iniciar sesión
    at.text_input[0].input("analista@secopanalytics.gov.co")
    at.text_input[1].input("Secop2026*")
    at.button[0].click().run()

    assert at.session_state.get("autenticado") is True
    assert len(at.exception) == 0

    # Navegar al Explorador de Contratos en la barra lateral
    if at.sidebar.radio:
        at.sidebar.radio[0].set_value("Explorador de Contratos").run()

    # Comprobar multiselects (depto, mpio, modalidad)
    assert len(at.multiselect) >= 3
    # Buscar multiselect de modalidad por key o posición
    ms_modalidad = [ms for ms in at.multiselect if "modalidad" in ms.key.lower()][0]
    assert len(ms_modalidad.options) > 0

    # Seleccionar primera opción disponible
    primera_mod = ms_modalidad.options[0]
    ms_modalidad.select(primera_mod).run()
    assert len(at.exception) == 0


# ==============================================================================
# PRUEBAS UNITARIAS, DE INTEGRACIÓN Y RENDIMIENTO PARA HU-12 (TIPO DE CONTRATO)
# ==============================================================================

def test_builder_con_tipo_contrato_str_unico(sample_dataframe: pd.DataFrame):
    """
    HU-12: Filtrado por string único de tipología contractual.
    - Retorna contratos correspondientes a ese tipo.
    - Compila en MongoDB: {'clasificacion.tipo_contrato': 'PRESTACIÓN DE SERVICIOS'}.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, latencia_ms = builder.con_tipo_contrato("PRESTACIÓN DE SERVICIOS").build()

    assert len(resultado) == 4
    assert set(resultado["tipo_contrato"].unique()) == {"PRESTACIÓN DE SERVICIOS"}
    assert query_mongo == {"clasificacion.tipo_contrato": "PRESTACIÓN DE SERVICIOS"}
    assert latencia_ms >= 0.0


def test_builder_con_tipo_contrato_lista_un_elemento(sample_dataframe: pd.DataFrame):
    """
    HU-12: Filtrado por lista con 1 tipo de contrato.
    - Compila en MongoDB con igualdad directa al valor único.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, _ = builder.con_tipo_contrato(["OBRA"]).build()

    assert len(resultado) == 2
    assert set(resultado["tipo_contrato"].unique()) == {"OBRA"}
    assert query_mongo == {"clasificacion.tipo_contrato": "OBRA"}


def test_builder_con_tipo_contrato_multiples(sample_dataframe: pd.DataFrame):
    """
    HU-12: Filtrado por lista de múltiples tipos de contrato.
    - Retorna contratos pertenecientes a cualquiera de las tipologías.
    - Compila en MongoDB con operador $in: {'clasificacion.tipo_contrato': {'$in': [...]}}.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    tipos = ["OBRA", "SUMINISTRO"]
    resultado, query_mongo, _ = builder.con_tipo_contrato(tipos).build()

    assert len(resultado) == 3  # 2 de Obra + 1 de Suministro
    assert set(resultado["tipo_contrato"].unique()) == {"OBRA", "SUMINISTRO"}
    assert query_mongo == {"clasificacion.tipo_contrato": {"$in": tipos}}


def test_builder_con_tipo_contrato_none_o_vacio(sample_dataframe: pd.DataFrame):
    """
    HU-12: Si tipos es None, lista vacía o string en blanco:
    - No muta los datos ni altera el dataset original.
    - No añade restricciones a query_mongo.
    """
    builder_none = ConsultaSecopBuilder(sample_dataframe)
    res_none, q_none, _ = builder_none.con_tipo_contrato(None).build()
    assert len(res_none) == len(sample_dataframe)
    assert q_none == {}

    builder_empty = ConsultaSecopBuilder(sample_dataframe)
    res_empty, q_empty, _ = builder_empty.con_tipo_contrato([]).build()
    assert len(res_empty) == len(sample_dataframe)
    assert q_empty == {}

    builder_blank = ConsultaSecopBuilder(sample_dataframe)
    res_blank, q_blank, _ = builder_blank.con_tipo_contrato("   ").build()
    assert len(res_blank) == len(sample_dataframe)
    assert q_blank == {}


def test_builder_con_tipo_contrato_inexistente(sample_dataframe: pd.DataFrame):
    """
    HU-12: Si se consulta un tipo de contrato inexistente:
    - Retorna DataFrame vacío sin lanzar excepciones.
    - Compila la condición en query_mongo.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, _ = builder.con_tipo_contrato("TIPO_INEXISTENTE_XYZ").build()

    assert len(resultado) == 0
    assert query_mongo == {"clasificacion.tipo_contrato": "TIPO_INEXISTENTE_XYZ"}


def test_builder_alias_filtrar_tipo_contrato(sample_dataframe: pd.DataFrame):
    """
    HU-12 / Criterio 2: Verifica que el alias .filtrar_tipo_contrato() opere
    de manera idéntica a .con_tipo_contrato().
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, _ = builder.filtrar_tipo_contrato("CONSULTORÍA").build()

    assert len(resultado) == 1
    assert resultado.iloc[0]["tipo_contrato"] == "CONSULTORÍA"
    assert query_mongo == {"clasificacion.tipo_contrato": "CONSULTORÍA"}


def test_builder_encadenamiento_completo_5_dimensiones(sample_dataframe: pd.DataFrame):
    """
    HU-08 + HU-09 + HU-10 + HU-11 + HU-12:
    Verifica el encadenamiento fluido multi-criterio completo en 5 dimensiones:
    1. Departamento: 'VALLE DEL CAUCA'
    2. Municipio: 'TULUÁ'
    3. Año de Vigencia: 2023
    4. Modalidad: 'CONTRATACIÓN DIRECTA'
    5. Tipo de Contrato: 'PRESTACIÓN DE SERVICIOS'
    - Retorna exactamente el contrato que cumple las 5 restricciones.
    - Compila el predicado completo para MongoDB con 'geografia', 'tiempo' y 'clasificacion'.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, latencia_ms = (
        builder
        .filtrar_departamento(["VALLE DEL CAUCA"])
        .filtrar_municipio(["TULUÁ"])
        .filtrar_anio(2023)
        .filtrar_modalidad("CONTRATACIÓN DIRECTA")
        .con_tipo_contrato("PRESTACIÓN DE SERVICIOS")
        .build()
    )

    assert len(resultado) == 1
    fila = resultado.iloc[0]
    assert fila["departamento"] == "VALLE DEL CAUCA"
    assert fila["municipio"] == "TULUÁ"
    assert fila["anio_vigencia"] == 2023
    assert fila["modalidad"] == "CONTRATACIÓN DIRECTA"
    assert fila["tipo_contrato"] == "PRESTACIÓN DE SERVICIOS"

    assert query_mongo == {
        "geografia.departamento": {"$in": ["VALLE DEL CAUCA"]},
        "geografia.municipio": {"$in": ["TULUÁ"]},
        "tiempo.anio_vigencia": 2023,
        "clasificacion.modalidad": "CONTRATACIÓN DIRECTA",
        "clasificacion.tipo_contrato": "PRESTACIÓN DE SERVICIOS"
    }
    assert latencia_ms >= 0.0


def test_rendimiento_filtrado_tipo_contrato_menor_500ms(real_10k_dataframe: pd.DataFrame):
    """
    HU-12 / Regla 4 / PA-ALFA-003:
    Verifica que el filtrado por tipo de contrato sobre 10.000 contratos se resuelva en menos de 500 ms (< 1.500 ms).
    """
    builder = ConsultaSecopBuilder(real_10k_dataframe)
    inicio = time.perf_counter()
    df_res, query_mongo, latencia_ms = builder.con_tipo_contrato("Prestación de servicios").build()
    duracion_ms = (time.perf_counter() - inicio) * 1000.0

    assert duracion_ms < 500.0, f"Filtrado por tipo superó 500 ms ({duracion_ms:.2f} ms)"
    assert len(df_res) > 0
    assert "clasificacion.tipo_contrato" in query_mongo


def test_apptest_filtrado_tipo_contrato_ui():
    """
    HU-12 / PA-ALFA-003: Prueba de integración UI con Streamlit AppTest:
    Verifica la interacción con el selector de tipo de contrato:
    1. Iniciar sesión como Analista_BI
    2. Comprobar presencia del multiselect de tipo de contrato
    3. Seleccionar 'Prestación de servicios'
    4. Comprobar que no se lanzan excepciones y la aplicación se recalcula reactivamente.
    """
    from streamlit.testing.v1 import AppTest
    from src.database.data_repository import DataRepositorySingleton

    repo = DataRepositorySingleton.get_instance()
    repo.cargar_fuente()

    ruta_app = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(ruta_app).run()

    # Iniciar sesión
    at.text_input[0].input("analista@secopanalytics.gov.co")
    at.text_input[1].input("Secop2026*")
    at.button[0].click().run()

    assert at.session_state.get("autenticado") is True
    assert len(at.exception) == 0

    # Navegar al Explorador de Contratos en la barra lateral
    if at.sidebar.radio:
        at.sidebar.radio[0].set_value("Explorador de Contratos").run()

    # Comprobar presencia del multiselect de tipo de contrato
    ms_tipo = [ms for ms in at.multiselect if "tipo" in ms.key.lower()][0]
    assert len(ms_tipo.options) > 0

    # Seleccionar primera opción disponible
    primera_opc = ms_tipo.options[0]
    ms_tipo.select(primera_opc).run()
    assert len(at.exception) == 0


# ==============================================================================
# PRUEBAS UNITARIAS, DE INTEGRACIÓN Y RENDIMIENTO PARA HU-13 (RANGO DE CUANTÍA)
# ==============================================================================

def test_builder_con_rango_cuantia_ambos_limites(sample_dataframe: pd.DataFrame):
    """
    HU-13: Filtrado con límite mínimo y máximo en cuantía inicial.
    - min_cop=300.0, max_cop=700.0.
    - Retorna contratos con 300 <= cuantia <= 700.
    - Compila en MongoDB: {'cuantia_inicial': {'$gte': 300.0, '$lte': 700.0}}.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, latencia_ms = builder.con_rango_cuantia(min_cop=300.0, max_cop=700.0).build()

    # Contratos con cuantías: 300, 400, 500, 600, 700 (5 contratos)
    assert len(resultado) == 5
    assert all(300.0 <= c <= 700.0 for c in resultado["cuantia_inicial"])
    assert query_mongo == {"cuantia_inicial": {"$gte": 300.0, "$lte": 700.0}}
    assert latencia_ms >= 0.0


def test_builder_con_rango_cuantia_solo_minimo(sample_dataframe: pd.DataFrame):
    """
    HU-13: Filtrado especificando únicamente cuantía mínima.
    - min_cop=800.0, max_cop=None.
    - Compila en MongoDB: {'cuantia_inicial': {'$gte': 800.0}}.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, _ = builder.con_rango_cuantia(min_cop=800.0, max_cop=None).build()

    # Contratos con cuantías: 800, 900, 1000 (3 contratos)
    assert len(resultado) == 3
    assert all(c >= 800.0 for c in resultado["cuantia_inicial"])
    assert query_mongo == {"cuantia_inicial": {"$gte": 800.0}}


def test_builder_con_rango_cuantia_solo_maximo(sample_dataframe: pd.DataFrame):
    """
    HU-13: Filtrado especificando únicamente cuantía máxima.
    - min_cop=None, max_cop=400.0.
    - Compila en MongoDB: {'cuantia_inicial': {'$lte': 400.0}}.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, _ = builder.con_rango_cuantia(min_cop=None, max_cop=400.0).build()

    # Contratos con cuantías: 100, 200, 300, 400 (4 contratos)
    assert len(resultado) == 4
    assert all(c <= 400.0 for c in resultado["cuantia_inicial"])
    assert query_mongo == {"cuantia_inicial": {"$lte": 400.0}}


def test_builder_con_rango_cuantia_none_o_cero(sample_dataframe: pd.DataFrame):
    """
    HU-13: Si ambos límites son None o 0:
    - No muta los datos ni altera el dataset original.
    - No añade restricciones vacías a query_mongo.
    """
    builder_none = ConsultaSecopBuilder(sample_dataframe)
    res_none, q_none, _ = builder_none.con_rango_cuantia(None, None).build()
    assert len(res_none) == len(sample_dataframe)
    assert q_none == {}

    builder_zero = ConsultaSecopBuilder(sample_dataframe)
    res_zero, q_zero, _ = builder_zero.con_rango_cuantia(0, 0).build()
    assert len(res_zero) == len(sample_dataframe)
    assert q_zero == {}


def test_builder_con_rango_cuantia_fuera_de_limites(sample_dataframe: pd.DataFrame):
    """
    HU-13: Si se consulta un rango que no cubre ningún contrato (ej. 5000 a 10000):
    - Retorna DataFrame vacío sin lanzar excepciones.
    - Compila el predicado en query_mongo.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, _ = builder.con_rango_cuantia(min_cop=5000.0, max_cop=10000.0).build()

    assert len(resultado) == 0
    assert query_mongo == {"cuantia_inicial": {"$gte": 5000.0, "$lte": 10000.0}}


def test_builder_alias_filtrar_cuantia(sample_dataframe: pd.DataFrame):
    """
    HU-13 / Criterio 2: Verifica que el alias .filtrar_cuantia() opere
    de manera idéntica a .con_rango_cuantia().
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, _ = builder.filtrar_cuantia(min_cop=200.0, max_cop=500.0).build()

    assert len(resultado) == 4
    assert query_mongo == {"cuantia_inicial": {"$gte": 200.0, "$lte": 500.0}}


def test_builder_encadenamiento_completo_6_dimensiones(sample_dataframe: pd.DataFrame):
    """
    HU-08 + HU-09 + HU-10 + HU-11 + HU-12 + HU-13:
    Verifica el encadenamiento fluido multi-criterio completo en 6 dimensiones:
    1. Departamento: 'VALLE DEL CAUCA'
    2. Municipio: 'TULUÁ'
    3. Año de Vigencia: 2023
    4. Modalidad: 'CONTRATACIÓN DIRECTA'
    5. Tipo de Contrato: 'PRESTACIÓN DE SERVICIOS'
    6. Rango de Cuantía: 500.0 a 700.0 COP
    - Retorna exactamente el contrato que cumple las 6 restricciones.
    - Compila el predicado completo para MongoDB con todas las dimensiones.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, latencia_ms = (
        builder
        .filtrar_departamento(["VALLE DEL CAUCA"])
        .filtrar_municipio(["TULUÁ"])
        .filtrar_anio(2023)
        .filtrar_modalidad("CONTRATACIÓN DIRECTA")
        .con_tipo_contrato("PRESTACIÓN DE SERVICIOS")
        .con_rango_cuantia(min_cop=500.0, max_cop=700.0)
        .build()
    )

    assert len(resultado) == 1
    fila = resultado.iloc[0]
    assert fila["departamento"] == "VALLE DEL CAUCA"
    assert fila["municipio"] == "TULUÁ"
    assert fila["anio_vigencia"] == 2023
    assert fila["modalidad"] == "CONTRATACIÓN DIRECTA"
    assert fila["tipo_contrato"] == "PRESTACIÓN DE SERVICIOS"
    assert fila["cuantia_inicial"] == 600.0

    assert query_mongo == {
        "geografia.departamento": {"$in": ["VALLE DEL CAUCA"]},
        "geografia.municipio": {"$in": ["TULUÁ"]},
        "tiempo.anio_vigencia": 2023,
        "clasificacion.modalidad": "CONTRATACIÓN DIRECTA",
        "clasificacion.tipo_contrato": "PRESTACIÓN DE SERVICIOS",
        "cuantia_inicial": {"$gte": 500.0, "$lte": 700.0}
    }
    assert latencia_ms >= 0.0


def test_rendimiento_filtrado_cuantia_menor_500ms(real_10k_dataframe: pd.DataFrame):
    """
    HU-13 / Criterio 3 / Regla 4:
    Verifica que el filtrado por rango de cuantía sobre 10.000 contratos se resuelva en menos de 500 ms (< 1.000 ms).
    """
    builder = ConsultaSecopBuilder(real_10k_dataframe)
    inicio = time.perf_counter()
    df_res, query_mongo, latencia_ms = builder.con_rango_cuantia(min_cop=10000000.0, max_cop=100000000.0).build()
    duracion_ms = (time.perf_counter() - inicio) * 1000.0

    assert duracion_ms < 500.0, f"Filtrado por cuantía superó 500 ms ({duracion_ms:.2f} ms)"
    assert len(df_res) > 0
    assert "cuantia_inicial" in query_mongo


def test_apptest_filtrado_cuantia_ui():
    """
    HU-13 / PA-ALFA-003: Prueba de integración UI con Streamlit AppTest:
    Verifica la interacción con los inputs numéricos de cuantía:
    1. Iniciar sesión como Analista_BI
    2. Comprobar presencia de inputs numéricos de cuantía
    3. Ajustar cuantía mínima y verificar ejecución sin excepciones.
    """
    from streamlit.testing.v1 import AppTest
    from src.database.data_repository import DataRepositorySingleton

    repo = DataRepositorySingleton.get_instance()
    repo.cargar_fuente()

    ruta_app = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(ruta_app).run()

    # Iniciar sesión
    at.text_input[0].input("analista@secopanalytics.gov.co")
    at.text_input[1].input("Secop2026*")
    at.button[0].click().run()

    assert at.session_state.get("autenticado") is True
    assert len(at.exception) == 0

    # Navegar al Explorador de Contratos en la barra lateral
    if at.sidebar.radio:
        at.sidebar.radio[0].set_value("Explorador de Contratos").run()

    # Comprobar inputs numéricos
    assert len(at.number_input) >= 2
    inp_min = at.number_input[0]
    inp_min.set_value(50000000.0).run()
    assert len(at.exception) == 0


# ==============================================================================
# PRUEBAS UNITARIAS Y DE RENDIMIENTO: HU-14 (FILTRADO POR ENTIDAD O NIT)
# ==============================================================================

def test_normalizar_texto_busqueda_util():
    """
    HU-14 / Criterio 1:
    Verifica la función utilitaria de normalización diacrítica:
    - Eliminación de tildes y diéresis.
    - Conversión a minúsculas.
    - Limpieza de espacios redundantes.
    - Manejo seguro de valores None o vacíos.
    """
    from src.utils.text_utils import normalizar_texto_busqueda

    assert normalizar_texto_busqueda("Alcaldía de Tuluá  ") == "alcaldia de tulua"
    assert normalizar_texto_busqueda("HOSPITAL SAN JUAN DE DIÓS") == "hospital san juan de dios"
    assert normalizar_texto_busqueda("  890.399.045-8  ") == "890.399.045-8"
    assert normalizar_texto_busqueda("") == ""
    assert normalizar_texto_busqueda(None) == ""
    assert normalizar_texto_busqueda("   ") == ""


def test_builder_con_entidad_nombre_exacto(sample_dataframe: pd.DataFrame):
    """
    HU-14 / Criterio 1 y 2:
    Búsqueda por nombre exacto de la entidad compradora.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, latencia_ms = builder.con_entidad_o_nit("ALCALDÍA DE TULUÁ").build()

    assert len(resultado) == 1
    assert resultado.iloc[0]["nombre_entidad"] == "ALCALDÍA DE TULUÁ"
    assert resultado.iloc[0]["municipio"] == "TULUÁ"
    assert "$or" in query_mongo
    assert latencia_ms >= 0.0


def test_builder_con_entidad_nombre_parcial(sample_dataframe: pd.DataFrame):
    """
    HU-14 / Criterio 1:
    Búsqueda por coincidencia parcial de texto en el nombre institucional.
    Ejemplo: 'hospital' localiza todas las E.S.E. y centros hospitalarios.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, _, _ = builder.con_entidad_o_nit("hospital").build()

    assert len(resultado) == 2
    nombres = set(resultado["nombre_entidad"].unique())
    assert "HOSPITAL UNIVERSITARIO DE SANTANDER" in nombres
    assert "HOSPITAL MANUEL URIBE ÁNGEL" in nombres


def test_builder_con_entidad_insensible_mayusculas_y_tildes(sample_dataframe: pd.DataFrame):
    """
    HU-14 / Criterio 1:
    La búsqueda debe ser completamente insensible a mayúsculas/minúsculas y a tildes/acentos:
    - 'tulua' coincide con 'ALCALDÍA DE TULUÁ'.
    - 'gobernacion' coincide con 'GOBERNACIÓN...'.
    - 'ALCALDÍA' coincide con registros con o sin acento.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)

    # 1. Búsqueda sin tilde en minúscula para entidad con tildes y mayúsculas
    res_tulua, _, _ = builder.con_entidad_o_nit("tulua").build()
    assert len(res_tulua) == 1
    assert res_tulua.iloc[0]["nombre_entidad"] == "ALCALDÍA DE TULUÁ"

    # 2. Búsqueda sin tilde 'gobernacion'
    builder.reset()
    res_gob, _, _ = builder.con_entidad_o_nit("gobernacion").build()
    assert len(res_gob) == 3
    for nom in res_gob["nombre_entidad"]:
        assert "GOBERNACIÓN" in nom

    # 3. Búsqueda con mayúsculas y tilde 'ALCALDÍA'
    builder.reset()
    res_alc, _, _ = builder.con_entidad_o_nit("ALCALDÍA").build()
    assert len(res_alc) == 4


def test_builder_con_entidad_por_nit(sample_dataframe: pd.DataFrame):
    """
    HU-14 / Criterio 1 y 2:
    Búsqueda por NIT de la entidad compradora (exacta o parcial).
    """
    builder = ConsultaSecopBuilder(sample_dataframe)

    # 1. NIT exacto de Tuluá (890399045)
    resultado, query_mongo, _ = builder.con_entidad_o_nit("890399045").build()
    assert len(resultado) == 1
    assert resultado.iloc[0]["nit_entidad"] == "890399045"
    assert resultado.iloc[0]["nombre_entidad"] == "ALCALDÍA DE TULUÁ"

    # 2. Coincidencia parcial de dígitos en NIT
    builder.reset()
    res_parcial, _, _ = builder.con_entidad_o_nit("890399").build()
    assert len(res_parcial) == 2  # 890399010 (Valle) y 890399045 (Tuluá)


def test_builder_con_entidad_vacio_o_none(sample_dataframe: pd.DataFrame):
    """
    HU-14 / Criterio 3:
    Si el argumento está vacío (""), es solo espacios o None, no aplica restricción y devuelve los datos intactos.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)

    # Con None
    res_none, q_none, _ = builder.con_entidad_o_nit(None).build()
    assert len(res_none) == len(sample_dataframe)
    assert "$or" not in q_none

    # Con cadena vacía
    builder.reset()
    res_vacio, q_vacio, _ = builder.con_entidad_o_nit("").build()
    assert len(res_vacio) == len(sample_dataframe)
    assert "$or" not in q_vacio

    # Con espacios en blanco
    builder.reset()
    res_espacios, q_espacios, _ = builder.con_entidad_o_nit("    ").build()
    assert len(res_espacios) == len(sample_dataframe)
    assert "$or" not in q_espacios


def test_builder_con_entidad_sin_coincidencias(sample_dataframe: pd.DataFrame):
    """
    HU-14 / Criterio 2:
    Búsqueda de una entidad o NIT inexistente devuelve un DataFrame vacío.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, _ = builder.con_entidad_o_nit("ENTIDAD_INEXISTENTE_XYZ_999").build()

    assert len(resultado) == 0
    assert "$or" in query_mongo


def test_builder_alias_filtrar_entidad(sample_dataframe: pd.DataFrame):
    """
    HU-14 / Criterio 3:
    Verifica que el alias semántico `.filtrar_entidad()` funcione idénticamente a `.con_entidad_o_nit()`.
    """
    b1 = ConsultaSecopBuilder(sample_dataframe).con_entidad_o_nit("Bello")
    b2 = ConsultaSecopBuilder(sample_dataframe).filtrar_entidad("Bello")

    df1, q1, _ = b1.build()
    df2, q2, _ = b2.build()

    pd.testing.assert_frame_equal(df1, df2)
    assert q1 == q2


def test_builder_mongo_query_entidad(sample_dataframe: pd.DataFrame):
    """
    HU-14 / Criterio 3:
    Verifica que la expresión $or compilada para MongoDB cumpla la estructura:
    {"$or": [{"entidad.nombre": {"$regex": patron, "$options": "i"}}, {"entidad.nit": {"$regex": patron, "$options": "i"}}]}
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    _, query_mongo, _ = builder.con_entidad_o_nit("Alcaldía de Tuluá").build()

    assert "$or" in query_mongo
    assert len(query_mongo["$or"]) == 2
    assert query_mongo["$or"][0] == {"entidad.nombre": {"$regex": "Alcaldía de Tuluá", "$options": "i"}}
    assert query_mongo["$or"][1] == {"entidad.nit": {"$regex": "Alcaldía de Tuluá", "$options": "i"}}


def test_builder_encadenamiento_completo_7_dimensiones(sample_dataframe: pd.DataFrame):
    """
    HU-14 / Criterio 2 y 3:
    Verifica el encadenamiento fluido de las 7 dimensiones analíticas implementadas (HU-08 a HU-14):
    1. Departamento: 'VALLE DEL CAUCA'
    2. Municipio: 'TULUÁ'
    3. Año de Vigencia: 2023
    4. Modalidad: 'CONTRATACIÓN DIRECTA'
    5. Tipo de Contrato: 'PRESTACIÓN DE SERVICIOS'
    6. Rango de Cuantía: 500.0 a 700.0 COP
    7. Entidad: 'Tuluá'
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, latencia_ms = (
        builder
        .filtrar_departamento(["VALLE DEL CAUCA"])
        .filtrar_municipio(["TULUÁ"])
        .filtrar_anio(2023)
        .filtrar_modalidad("CONTRATACIÓN DIRECTA")
        .con_tipo_contrato("PRESTACIÓN DE SERVICIOS")
        .con_rango_cuantia(min_cop=500.0, max_cop=700.0)
        .con_entidad_o_nit("Tuluá")
        .build()
    )

    assert len(resultado) == 1
    fila = resultado.iloc[0]
    assert fila["departamento"] == "VALLE DEL CAUCA"
    assert fila["municipio"] == "TULUÁ"
    assert fila["anio_vigencia"] == 2023
    assert fila["modalidad"] == "CONTRATACIÓN DIRECTA"
    assert fila["tipo_contrato"] == "PRESTACIÓN DE SERVICIOS"
    assert fila["cuantia_inicial"] == 600.0
    assert fila["nombre_entidad"] == "ALCALDÍA DE TULUÁ"

    assert query_mongo == {
        "geografia.departamento": {"$in": ["VALLE DEL CAUCA"]},
        "geografia.municipio": {"$in": ["TULUÁ"]},
        "tiempo.anio_vigencia": 2023,
        "clasificacion.modalidad": "CONTRATACIÓN DIRECTA",
        "clasificacion.tipo_contrato": "PRESTACIÓN DE SERVICIOS",
        "cuantia_inicial": {"$gte": 500.0, "$lte": 700.0},
        "$or": [
            {"entidad.nombre": {"$regex": "Tuluá", "$options": "i"}},
            {"entidad.nit": {"$regex": "Tuluá", "$options": "i"}}
        ]
    }
    assert latencia_ms >= 0.0


def test_rendimiento_filtrado_entidad_menor_500ms(real_10k_dataframe: pd.DataFrame):
    """
    HU-14 / Regla 4 / PA-ALFA-003:
    Verifica que la búsqueda diacrítica por entidad/NIT sobre los 10.000 contratos reales
    se resuelva en menos de 500 ms (< 1.000 ms).
    """
    builder = ConsultaSecopBuilder(real_10k_dataframe)
    inicio = time.perf_counter()
    df_res, query_mongo, latencia_ms = builder.con_entidad_o_nit("hospital").build()
    duracion_ms = (time.perf_counter() - inicio) * 1000.0

    assert duracion_ms < 500.0, f"Búsqueda por entidad superó 500 ms ({duracion_ms:.2f} ms)"
    assert len(df_res) > 0
    assert "$or" in query_mongo


def test_apptest_filtrado_entidad_ui():
    """
    HU-14 / PA-ALFA-003: Prueba de integración UI con Streamlit AppTest:
    Verifica la interacción con el input de texto para Entidad Compradora / NIT:
    1. Iniciar sesión como Analista_BI
    2. Comprobar presencia del input de texto de entidad
    3. Ingresar texto de búsqueda y verificar ejecución sin excepciones.
    """
    from streamlit.testing.v1 import AppTest
    from src.database.data_repository import DataRepositorySingleton

    repo = DataRepositorySingleton.get_instance()
    repo.cargar_fuente()

    ruta_app = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(ruta_app).run()

    # Iniciar sesión
    at.text_input[0].input("analista@secopanalytics.gov.co")
    at.text_input[1].input("Secop2026*")
    at.button[0].click().run()

    assert at.session_state.get("autenticado") is True
    assert len(at.exception) == 0

    # Navegar al Explorador de Contratos en la barra lateral
    if at.sidebar.radio:
        at.sidebar.radio[0].set_value("Explorador de Contratos").run()

    # Comprobar inputs de texto en la vista autenticada
    # text_input[0] en la vista de consultas (o buscar por clave)
    inputs_entidad = [inp for inp in at.text_input if "filtro_entidad" in getattr(inp, "key", "")]
    if not inputs_entidad:
        # Fallback a buscar por label
        inputs_entidad = [inp for inp in at.text_input if "Entidad" in getattr(inp, "label", "")]

    assert len(inputs_entidad) >= 1
    inputs_entidad[0].input("Tuluá").run()
    assert len(at.exception) == 0


# ==============================================================================
# PRUEBAS UNITARIAS Y DE RENDIMIENTO: HU-15 (FILTRADO POR PROVEEDOR O DOCUMENTO)
# ==============================================================================

def test_builder_con_proveedor_razon_social_exacta(sample_dataframe: pd.DataFrame):
    """
    HU-15 / Criterio 1:
    Búsqueda por razón social exacta del contratista adjudicado.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, latencia_ms = builder.con_proveedor("SEBASTIÁN RIVERA MARTÍNEZ").build()

    assert len(resultado) == 1
    assert resultado.iloc[0]["proveedor"] == "SEBASTIÁN RIVERA MARTÍNEZ"
    assert resultado.iloc[0]["documento_proveedor"] == "1036640178"
    assert "$and" in query_mongo
    assert latencia_ms >= 0.0


def test_builder_con_proveedor_razon_social_parcial(sample_dataframe: pd.DataFrame):
    """
    HU-15 / Criterio 1:
    Búsqueda por coincidencia parcial de texto en la razón social.
    Ejemplo: 'consorcio' o 'sas'.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)

    # 1. Búsqueda de 'consorcio'
    resultado, _, _ = builder.con_proveedor("consorcio").build()
    assert len(resultado) == 1
    assert "CONSORCIO VIAL DEL NORTE" in resultado["proveedor"].values

    # 2. Búsqueda de 'sas'
    builder.reset()
    res_sas, _, _ = builder.con_proveedor("sas").build()
    assert len(res_sas) == 7
    for nombre in res_sas["proveedor"]:
        assert "SAS" in nombre.upper()


def test_builder_con_proveedor_insensible_mayusculas_y_tildes(sample_dataframe: pd.DataFrame):
    """
    HU-15 / Criterio 1:
    Búsqueda insensible a mayúsculas/minúsculas y a tildes/diacríticos:
    - 'sebastian rivera martinez' localiza 'SEBASTIÁN RIVERA MARTÍNEZ'.
    - 'medicas' localiza 'DISTRIBUCIONES MÉDICAS DE COLOMBIA LTDA'.
    - 'SOLUCIONES' en mayúsculas localiza registros con o sin acento.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)

    # 1. Búsqueda en minúsculas sin tilde para nombre con tildes en mayúscula
    res_seb, _, _ = builder.con_proveedor("sebastian rivera martinez").build()
    assert len(res_seb) == 1
    assert res_seb.iloc[0]["proveedor"] == "SEBASTIÁN RIVERA MARTÍNEZ"

    # 2. Búsqueda sin tilde 'medicas'
    builder.reset()
    res_med, _, _ = builder.con_proveedor("medicas").build()
    assert len(res_med) == 1
    assert res_med.iloc[0]["proveedor"] == "DISTRIBUCIONES MÉDICAS DE COLOMBIA LTDA"

    # 3. Búsqueda con mayúsculas 'SOLUCIONES'
    builder.reset()
    res_sol, _, _ = builder.con_proveedor("SOLUCIONES").build()
    assert len(res_sol) == 1
    assert "SOLUCIONES TECNOLÓGICAS" in res_sol.iloc[0]["proveedor"]


def test_builder_con_proveedor_por_documento(sample_dataframe: pd.DataFrame):
    """
    HU-15 / Criterio 1:
    Búsqueda por documento de identificación (Cédula o NIT del contratista).
    """
    builder = ConsultaSecopBuilder(sample_dataframe)

    # 1. Documento exacto de Sebastián Rivera (1036640178)
    resultado, query_mongo, _ = builder.con_proveedor("1036640178").build()
    assert len(resultado) == 1
    assert resultado.iloc[0]["documento_proveedor"] == "1036640178"
    assert resultado.iloc[0]["proveedor"] == "SEBASTIÁN RIVERA MARTÍNEZ"

    # 2. Búsqueda parcial de dígitos en documento
    builder.reset()
    res_parcial, _, _ = builder.con_proveedor("900").build()
    assert len(res_parcial) >= 5


def test_builder_con_proveedor_vacio_o_none(sample_dataframe: pd.DataFrame):
    """
    HU-15 / Criterio 3:
    Si el criterio es None, vacío o solo espacios, retorna el DataFrame intacto sin filtros.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)

    # Con None
    res_none, q_none, _ = builder.con_proveedor(None).build()
    assert len(res_none) == len(sample_dataframe)
    assert "$and" not in q_none

    # Con cadena vacía
    builder.reset()
    res_vacio, q_vacio, _ = builder.con_proveedor("").build()
    assert len(res_vacio) == len(sample_dataframe)
    assert "$and" not in q_vacio

    # Con espacios en blanco
    builder.reset()
    res_esp, q_esp, _ = builder.con_proveedor("   ").build()
    assert len(res_esp) == len(sample_dataframe)
    assert "$and" not in q_esp


def test_builder_con_proveedor_sin_coincidencias(sample_dataframe: pd.DataFrame):
    """
    HU-15 / Criterio 2:
    Búsqueda de un contratista inexistente devuelve un DataFrame vacío.
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, _ = builder.con_proveedor("CONTRATISTA_INEXISTENTE_XYZ_999").build()

    assert len(resultado) == 0
    assert "$and" in query_mongo


def test_builder_alias_filtrar_proveedor(sample_dataframe: pd.DataFrame):
    """
    HU-15 / Criterio 3:
    Verifica que el alias semántico `.filtrar_proveedor()` sea idéntico a `.con_proveedor()`.
    """
    b1 = ConsultaSecopBuilder(sample_dataframe).con_proveedor("Boyacense")
    b2 = ConsultaSecopBuilder(sample_dataframe).filtrar_proveedor("Boyacense")

    df1, q1, _ = b1.build()
    df2, q2, _ = b2.build()

    pd.testing.assert_frame_equal(df1, df2)
    assert q1 == q2


def test_builder_mongo_query_proveedor(sample_dataframe: pd.DataFrame):
    """
    HU-15 / Criterio 3:
    Verifica la estructura del predicado compilado en MongoDB:
    {"$and": [{"$or": [{"proveedor.nombre_razon_social": {"$regex": ..., "$options": "i"}},
                        {"proveedor.documento": {"$regex": ..., "$options": "i"}}]}]}
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    _, query_mongo, _ = builder.con_proveedor("Rivera Martinez").build()

    assert "$and" in query_mongo
    assert len(query_mongo["$and"]) == 1
    cond_or = query_mongo["$and"][0]["$or"]
    assert len(cond_or) == 2
    assert "proveedor.nombre_razon_social" in cond_or[0]
    assert cond_or[0]["proveedor.nombre_razon_social"]["$options"] == "i"
    assert "proveedor.documento" in cond_or[1]
    assert cond_or[1]["proveedor.documento"]["$options"] == "i"


def test_builder_encadenamiento_completo_8_dimensiones(sample_dataframe: pd.DataFrame):
    """
    HU-15 / Criterio 2 y 3:
    Verifica el encadenamiento fluido de las 8 dimensiones analíticas de SECOP-Analytics:
    1. Departamento: 'VALLE DEL CAUCA'
    2. Municipio: 'TULUÁ'
    3. Año de Vigencia: 2023
    4. Modalidad: 'CONTRATACIÓN DIRECTA'
    5. Tipo de Contrato: 'PRESTACIÓN DE SERVICIOS'
    6. Rango de Cuantía: 500.0 a 700.0 COP
    7. Entidad: 'Tuluá'
    8. Proveedor: 'Rivera Martínez'
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    resultado, query_mongo, latencia_ms = (
        builder
        .filtrar_departamento(["VALLE DEL CAUCA"])
        .filtrar_municipio(["TULUÁ"])
        .filtrar_anio(2023)
        .filtrar_modalidad("CONTRATACIÓN DIRECTA")
        .con_tipo_contrato("PRESTACIÓN DE SERVICIOS")
        .con_rango_cuantia(min_cop=500.0, max_cop=700.0)
        .con_entidad_o_nit("Tuluá")
        .con_proveedor("Rivera Martínez")
        .build()
    )

    assert len(resultado) == 1
    fila = resultado.iloc[0]
    assert fila["departamento"] == "VALLE DEL CAUCA"
    assert fila["municipio"] == "TULUÁ"
    assert fila["anio_vigencia"] == 2023
    assert fila["modalidad"] == "CONTRATACIÓN DIRECTA"
    assert fila["tipo_contrato"] == "PRESTACIÓN DE SERVICIOS"
    assert fila["cuantia_inicial"] == 600.0
    assert fila["nombre_entidad"] == "ALCALDÍA DE TULUÁ"
    assert fila["proveedor"] == "SEBASTIÁN RIVERA MARTÍNEZ"
    assert fila["documento_proveedor"] == "1036640178"

    assert query_mongo["geografia.departamento"] == {"$in": ["VALLE DEL CAUCA"]}
    assert query_mongo["geografia.municipio"] == {"$in": ["TULUÁ"]}
    assert query_mongo["tiempo.anio_vigencia"] == 2023
    assert query_mongo["clasificacion.modalidad"] == "CONTRATACIÓN DIRECTA"
    assert query_mongo["clasificacion.tipo_contrato"] == "PRESTACIÓN DE SERVICIOS"
    assert query_mongo["cuantia_inicial"] == {"$gte": 500.0, "$lte": 700.0}
    assert "$or" in query_mongo  # Entidad
    assert "$and" in query_mongo  # Proveedor
    assert latencia_ms >= 0.0


def test_resumen_concentracion_proveedor_adjudicado(sample_dataframe: pd.DataFrame):
    """
    HU-15 / Criterio 2:
    Verifica la agregación de métricas de concentración para veeduría ciudadana:
    - Cuantía total adjudicada al proponente.
    - Total de contratos / procesos asignados.
    - Distribución de estados vigentes (Celebrado, En ejecución, etc.).
    """
    builder = ConsultaSecopBuilder(sample_dataframe)
    df_prov, _, _ = builder.con_proveedor("Rivera Martinez").build()

    total_procesos = len(df_prov)
    cuantia_total = df_prov["cuantia_inicial"].sum()
    dist_estados = df_prov["estado"].value_counts().to_dict()

    assert total_procesos == 1
    assert cuantia_total == 600.0
    assert "En ejecución" in dist_estados
    assert dist_estados["En ejecución"] == 1


def test_rendimiento_filtrado_proveedor_menor_500ms(real_10k_dataframe: pd.DataFrame):
    """
    HU-15 / Regla 4 / PA-ALFA-003:
    Verifica que la búsqueda por contratista sobre 10.000 contratos reales
    se resuelva en menos de 500 ms (< 1.000 ms).
    """
    builder = ConsultaSecopBuilder(real_10k_dataframe)
    inicio = time.perf_counter()
    df_res, query_mongo, latencia_ms = builder.con_proveedor("martinez").build()
    duracion_ms = (time.perf_counter() - inicio) * 1000.0

    assert duracion_ms < 500.0, f"Búsqueda por proveedor superó 500 ms ({duracion_ms:.2f} ms)"
    assert len(df_res) > 0
    assert "$and" in query_mongo


def test_apptest_filtrado_proveedor_ui():
    """
    HU-15 / PA-ALFA-003: Prueba de integración UI con Streamlit AppTest:
    Verifica la interacción con el input de texto para Proveedor / Contratista:
    1. Iniciar sesión como Analista_BI
    2. Comprobar presencia del input de proveedor
    3. Ingresar texto de contratista y verificar ejecución sin excepciones.
    """
    from streamlit.testing.v1 import AppTest
    from src.database.data_repository import DataRepositorySingleton

    repo = DataRepositorySingleton.get_instance()
    repo.cargar_fuente()

    ruta_app = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(ruta_app).run()

    # Iniciar sesión
    at.text_input[0].input("analista@secopanalytics.gov.co")
    at.text_input[1].input("Secop2026*")
    at.button[0].click().run()

    assert at.session_state.get("autenticado") is True
    assert len(at.exception) == 0

    # Navegar al Explorador de Contratos en la barra lateral
    if at.sidebar.radio:
        at.sidebar.radio[0].set_value("Explorador de Contratos").run()

    # Comprobar inputs de texto de proveedor en la vista autenticada
    inputs_prov = [inp for inp in at.text_input if "filtro_proveedor" in getattr(inp, "key", "")]
    if not inputs_prov:
        inputs_prov = [inp for inp in at.text_input if "Proveedor" in getattr(inp, "label", "")]

    assert len(inputs_prov) >= 1
    inputs_prov[0].input("Rivera").run()
    assert len(at.exception) == 0








