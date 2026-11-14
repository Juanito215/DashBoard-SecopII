"""
Suite de Pruebas Automatizadas del Servicio de Exportación y Reportes CSV
Historia de Usuario: HU-30 (Exportación de Datos Filtrados y Reportes a CSV)
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest

from src.database.data_repository import DataRepositorySingleton
from src.utils.export_service import ExportService


@pytest.fixture
def sample_export_dataframe() -> pd.DataFrame:
    """Fixture con contratos de prueba con caracteres especiales en español y montos."""
    return pd.DataFrame({
        "id_proceso": ["CO1.PCONTR.1001", "CO1.PCONTR.1002"],
        "id_contrato": ["CTR-2022-001", "CTR-2022-002"],
        "anio_vigencia": [2022, 2023],
        "departamento": ["Valle del Cauca", "Boyacá"],
        "municipio": ["Tuluá", "Tunja"],
        "entidad": ["Alcaldía Municipal de Tuluá", "Gobernación de Boyacá"],
        "nit_entidad": ["890399045-3", "891800498-1"],
        "modalidad": ["Contratación directa", "Licitación pública"],
        "tipo_contrato": ["Prestación de servicios", "Obra pública"],
        "estado": ["Terminado", "En ejecución"],
        "proveedor": ["Consorcio Caña & Azúcar", "Ingeniería de Vías SAS"],
        "documento_proveedor": ["900123456", "901987654"],
        "es_pyme": [True, False],
        "codigo_unspsc": ["80111600", "72141103"],
        "cuantia_inicial": [150_000_000.0, 1_200_000_000.0],
        "valor_adiciones": [20_000_000.0, 0.0],
        "cuantia_final": [170_000_000.0, 1_200_000_000.0],
        "plazo_dias": [180, 365],
        "tiene_adicion": [True, False],
        "score_riesgo_anomalia": [0.6850, 0.2210],
        "nivel_alerta": ["Alto", "Bajo"],
        "_id": ["mongo_internal_id_1", "mongo_internal_id_2"],
    })


def test_preparar_dataframe_exportacion_columnas_clave(sample_export_dataframe: pd.DataFrame):
    """
    HU-30 / Criterio 1: Valida que la selección de columnas clave filtre,
    renombre a títulos ejecutivos y elimine identificadores internos (_id).
    """
    df_preparado = ExportService.preparar_dataframe_exportacion(
        sample_export_dataframe, solo_columnas_clave=True
    )

    assert not df_preparado.empty
    assert "_id" not in df_preparado.columns
    assert "ID_Proceso" in df_preparado.columns
    assert "Entidad_Compradora" in df_preparado.columns
    assert "Cuantia_Inicial_COP" in df_preparado.columns
    assert "Valor_Adiciones_COP" in df_preparado.columns
    assert "Cuantia_Final_COP" in df_preparado.columns
    assert "Contratista_Adjudicado" in df_preparado.columns
    assert "Nivel_Alerta_ML" in df_preparado.columns


def test_preparar_dataframe_exportacion_dataset_completo(sample_export_dataframe: pd.DataFrame):
    """
    HU-30 / Criterio 1: Valida que la opción de dataset completo conserve todas
    las columnas originales excluyendo solo atributos internos (_id).
    """
    df_completo = ExportService.preparar_dataframe_exportacion(
        sample_export_dataframe, solo_columnas_clave=False
    )

    assert not df_completo.empty
    assert "_id" not in df_completo.columns
    assert "id_proceso" in df_completo.columns
    assert "entidad" in df_completo.columns
    assert len(df_completo.columns) == len(sample_export_dataframe.columns) - 1


def test_preparar_dataframe_exportacion_vacio_o_none():
    """
    HU-30: Valida que ante DataFrames vacíos o None se retorne un DataFrame vacío sin excepciones.
    """
    assert ExportService.preparar_dataframe_exportacion(None).empty
    assert ExportService.preparar_dataframe_exportacion(pd.DataFrame()).empty


def test_generar_csv_bytes_bom_utf8_compatibilidad_excel(sample_export_dataframe: pd.DataFrame):
    """
    HU-30 / Criterio 2: Valida la inclusión del Byte Order Mark (BOM: \xef\xbb\xbf)
    y la integridad de caracteres especiales en español (tildes, ñ, $, &) para Excel.
    """
    csv_bytes = ExportService.generar_csv_bytes(sample_export_dataframe, solo_columnas_clave=True)

    assert isinstance(csv_bytes, bytes)
    assert len(csv_bytes) > 0

    # Comprobación del prefijo BOM de UTF-8 (0xEF, 0xBB, 0xBF)
    assert csv_bytes.startswith(b"\xef\xbb\xbf")

    # Decodificación limpia con utf-8-sig
    texto_decodificado = csv_bytes.decode("utf-8-sig")
    assert "Tuluá" in texto_decodificado
    assert "Boyacá" in texto_decodificado
    assert "Caña & Azúcar" in texto_decodificado
    assert "Licitación pública" in texto_decodificado


def test_generar_csv_bytes_separadores_configurables(sample_export_dataframe: pd.DataFrame):
    """
    HU-30 / Criterio 2: Valida la alternancia entre separadores coma (,) y punto y coma (;).
    """
    csv_coma = ExportService.generar_csv_bytes(sample_export_dataframe, separador=",").decode("utf-8-sig")
    assert "," in csv_coma.splitlines()[0]

    csv_punto_coma = ExportService.generar_csv_bytes(sample_export_dataframe, separador=";").decode("utf-8-sig")
    assert ";" in csv_punto_coma.splitlines()[0]


def test_generar_csv_bytes_conjunto_vacio():
    """
    HU-30 / Criterio 3: Valida que ante DataFrames vacíos se retorne b"" sin fallos.
    """
    assert ExportService.generar_csv_bytes(None) == b""
    assert ExportService.generar_csv_bytes(pd.DataFrame()) == b""


def test_generar_nombre_archivo_nomenclatura():
    """
    HU-30 / Criterio 2: Valida el patrón de nomenclatura del reporte con sello de tiempo.
    """
    nombre = ExportService.generar_nombre_archivo()
    assert nombre.startswith("SECOP_Analytics_Reporte_")
    assert nombre.endswith(".csv")


def test_registrar_auditoria_exportacion_tolerancia_fallos():
    """
    HU-30 / Criterio 3: Valida el registro en auditoria_descargas con tolerancia a fallos.
    """
    ExportService.registrar_auditoria_exportacion(
        usuario="auditor_prueba@secopanalytics.gov.co",
        total_registros=150,
        query_match={"geografia.departamento": "VALLE DEL CAUCA"}
    )


def test_apptest_consultas_view_export_ui():
    """
    HU-30 / Criterios 1, 2 y 3: Prueba de integración con Streamlit AppTest:
    1. Iniciar sesión como Analista_BI
    2. Navegar a 'Explorador de Contratos'
    3. Comprobar que se rendericen los selectores de formato de reporte y el botón de descarga.
    """
    from streamlit.testing.v1 import AppTest

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

    # Navegar a Explorador de Contratos
    if at.sidebar.radio:
        at.sidebar.radio[0].set_value("Explorador de Contratos").run()

    assert len(at.exception) == 0

    # Comprobar componentes de exportación HU-30 en la vista
    html_consultas = " ".join([m.value for m in at.markdown if hasattr(m, "value")])
    assert "Contratos Filtrados" in html_consultas

    # Verificar que los radio buttons de opciones de exportación existan
    radios_labels = [r.label for r in at.radio]
    assert any("Estructura del Reporte" in str(lbl) for lbl in radios_labels)
    assert any("Separador de Campos" in str(lbl) for lbl in radios_labels)

    # Verificar que el botón de descarga exista
    btn_descarga = [d for d in at.download_button if "Descargar" in str(d.label)]
    assert len(btn_descarga) > 0
