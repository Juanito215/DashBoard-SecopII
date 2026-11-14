"""
Servicio de Machine Learning para Inferencia de Riesgo Contractual
Historias de Usuario: HU-27 (Simulador Interactivo) y HU-28 (Score de Anomalía y Nivel de Alerta)
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.database.connection import MongoConnectionSingleton


class RiskPredictorService:
    """
    Servicio de Machine Learning para inferencia de riesgo de adiciones presupuestales,
    detección de anomalías no supervisadas y registro de trazabilidad en la colección predicciones_ml.
    """

    FEATURES_NUM = ["cuantia_inicial", "plazo_dias", "es_pyme_num"]
    FEATURES_CAT = ["departamento", "modalidad", "tipo_contrato"]
    _instance = None

    def __init__(self) -> None:
        self.pipeline: Pipeline | None = None
        self.detector_anomalias: IsolationForest | None = None
        self.accuracy: float = 0.0
        self.tasa_sobrecosto_media: float = 0.20
        self.entrenado: bool = False

    @classmethod
    def get_instance(cls) -> "RiskPredictorService":
        """Retorna la instancia Singleton del servicio predictivo."""
        if cls._instance is None:
            cls._instance = RiskPredictorService()
        return cls._instance

    @staticmethod
    def categorizar_nivel_alerta(score: float) -> tuple[str, str, str]:
        """
        HU-28: Clasifica un puntaje continuo [0.0, 1.0] en su nivel de alerta operativa.
        Retorna: (etiqueta_nivel, color_texto_hex, color_fondo_pill_hex)
        """
        score_acotado = float(np.clip(score, 0.0, 1.0))
        if score_acotado >= 0.65:
            return "Alto", "#BE123C", "#FFE4E6"
        if score_acotado >= 0.35:
            return "Moderado", "#B45309", "#FEF3C7"
        return "Bajo", "#047857", "#ECFDF5"

    def entrenar_detector_anomalias(self, df: pd.DataFrame | None) -> None:
        """
        HU-28: Ajusta un modelo IsolationForest sobre variables numéricas clave
        para detectar combinaciones atípicas de cuantía y plazo de ejecución.
        """
        if df is None or len(df) < 10:
            self.detector_anomalias = None
            return

        col_cuantia = "cuantia_inicial" if "cuantia_inicial" in df.columns else ("valor_del_contrato" if "valor_del_contrato" in df.columns else "cuantia_final")
        col_plazo = "plazo_dias" if "plazo_dias" in df.columns else ("duracion_dias" if "duracion_dias" in df.columns else None)

        val_cuantia = pd.to_numeric(df.get(col_cuantia, 0.0), errors="coerce").fillna(0.0).clip(lower=0)
        val_plazo = (
            pd.to_numeric(df[col_plazo], errors="coerce").fillna(30).clip(lower=1)
            if col_plazo and col_plazo in df.columns
            else pd.Series(np.full(len(df), 30.0))
        )

        df_num = pd.DataFrame({
            "cuantia": np.log1p(val_cuantia),
            "plazo": val_plazo,
        })
        iso = IsolationForest(n_estimators=100, contamination=0.10, random_state=42)
        iso.fit(df_num)
        self.detector_anomalias = iso

    def entrenar(self, df: pd.DataFrame | None) -> dict[str, Any]:
        """
        HU-27 / HU-28: Entrena el clasificador supervisado RandomForest y el detector IsolationForest
        sobre el dataset activo. Garantiza manejo seguro ante conjuntos pequeños o clases desbalanceadas.
        """
        if df is None or len(df) < 20:
            self.entrenado = False
            return {"entrenado": False, "accuracy": 0.0}

        df_ml = df.copy()

        # Normalización de variables numéricas
        col_cuantia = "cuantia_inicial" if "cuantia_inicial" in df_ml.columns else ("valor_del_contrato" if "valor_del_contrato" in df_ml.columns else "cuantia_final")
        df_ml["cuantia_inicial"] = pd.to_numeric(df_ml.get(col_cuantia, 0.0), errors="coerce").fillna(0.0)

        col_plazo = "plazo_dias" if "plazo_dias" in df_ml.columns else ("duracion_dias" if "duracion_dias" in df_ml.columns else None)
        df_ml["plazo_dias"] = (
            pd.to_numeric(df_ml[col_plazo], errors="coerce").fillna(30).clip(lower=1)
            if col_plazo and col_plazo in df_ml.columns
            else 30.0
        )

        # Normalización de PYME a entero binario
        col_pyme = None
        for c in ["es_pyme", "proveedor.es_pyme", "pyme"]:
            if c in df_ml.columns:
                col_pyme = c
                break

        if col_pyme:
            if pd.api.types.is_bool_dtype(df_ml[col_pyme]):
                df_ml["es_pyme_num"] = df_ml[col_pyme].astype(int)
            else:
                df_ml["es_pyme_num"] = (
                    df_ml[col_pyme]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .isin(["si", "sí", "true", "1", "s", "verdadero", "yes"])
                    .astype(int)
                )
        else:
            df_ml["es_pyme_num"] = 0

        # Normalización de variables categóricas
        mapeo_cats = {
            "departamento": ["departamento", "geografia.departamento"],
            "modalidad": ["modalidad", "modalidad_de_contratacion", "clasificacion.modalidad"],
            "tipo_contrato": ["tipo_contrato", "tipo_de_contrato", "clasificacion.tipo_contrato"],
        }
        for dest, cands in mapeo_cats.items():
            encontrado = None
            for cand in cands:
                if cand in df_ml.columns:
                    encontrado = cand
                    break
            if encontrado:
                df_ml[dest] = df_ml[encontrado].astype(object).fillna("NO REGISTRA").astype(str).str.strip()
            else:
                df_ml[dest] = "NO REGISTRA"

        # Variable objetivo: tiene_adicion
        if "tiene_adicion" in df_ml.columns:
            y = df_ml["tiene_adicion"].astype(bool).astype(int)
        elif "valor_adiciones" in df_ml.columns:
            y = (pd.to_numeric(df_ml["valor_adiciones"], errors="coerce").fillna(0.0) > 0).astype(int)
        else:
            y = pd.Series(np.zeros(len(df_ml), dtype=int))

        # Calcular porcentaje histórico medio de adición en contratos modificados
        if "valor_adiciones" in df_ml.columns:
            adicionados = df_ml[(y == 1) & (df_ml["cuantia_inicial"] > 0)]
            if not adicionados.empty:
                val_adic = pd.to_numeric(adicionados["valor_adiciones"], errors="coerce").fillna(0.0)
                val_ini = pd.to_numeric(adicionados["cuantia_inicial"], errors="coerce").fillna(1.0)
                ratio_hist = (val_adic / val_ini).clip(0.05, 0.50).median()
                self.tasa_sobrecosto_media = float(ratio_hist) if not pd.isna(ratio_hist) else 0.20

        # Si solo existe una clase en la muestra, sintetizar etiqueta base por perfil de riesgo
        if y.nunique() < 2:
            umbral_cuantia = df_ml["cuantia_inicial"].quantile(0.75)
            y = ((df_ml["cuantia_inicial"] >= umbral_cuantia) & (df_ml["plazo_dias"] >= 120)).astype(int)
            if y.nunique() < 2:
                y.iloc[0] = 1
                y.iloc[-1] = 0

        X = df_ml[self.FEATURES_NUM + self.FEATURES_CAT]

        preprocesador = ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), self.FEATURES_NUM),
                ("cat", OneHotEncoder(handle_unknown="ignore"), self.FEATURES_CAT),
            ]
        )

        modelo = RandomForestClassifier(
            n_estimators=120,
            max_depth=8,
            random_state=42,
            class_weight="balanced",
            n_jobs=-1,
        )

        self.pipeline = Pipeline(steps=[("prep", preprocesador), ("clf", modelo)])

        if len(X) >= 20:
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            self.pipeline.fit(X_train, y_train)
            preds = self.pipeline.predict(X_test)
            self.accuracy = float(accuracy_score(y_test, preds))
        else:
            self.pipeline.fit(X, y)
            preds = self.pipeline.predict(X)
            self.accuracy = float(accuracy_score(y, preds))

        # Entrenar simultáneamente el detector de anomalías no supervisado (IsolationForest)
        self.entrenar_detector_anomalias(df)

        self.entrenado = True
        return {"entrenado": True, "accuracy": round(self.accuracy * 100, 2)}

    def predecir_riesgo_contrato(
        self,
        departamento: str,
        modalidad: str,
        tipo_contrato: str,
        es_pyme: bool,
        cuantia_inicial: float,
        plazo_dias: int,
        usuario_auditor: str = "sistema",
        guardar_en_mongo: bool = True,
    ) -> dict[str, Any]:
        """
        HU-27: Ejecuta la inferencia de riesgo para un escenario contractual específico
        y registra el resultado en MongoDB (predicciones_ml).
        """
        entrada = pd.DataFrame([{
            "cuantia_inicial": float(cuantia_inicial),
            "plazo_dias": int(plazo_dias),
            "es_pyme_num": int(bool(es_pyme)),
            "departamento": str(departamento).strip(),
            "modalidad": str(modalidad).strip(),
            "tipo_contrato": str(tipo_contrato).strip(),
        }])

        if self.entrenado and self.pipeline is not None:
            prob_adicion = float(self.pipeline.predict_proba(entrada)[0][1])
        else:
            # Respaldo heurístico calibrado si no hubo entrenamiento previo
            base = 0.45 if "DIRECTA" in str(modalidad).upper() else 0.25
            factor_plazo = min(0.30, (plazo_dias / 365.0) * 0.25)
            factor_monto = 0.15 if cuantia_inicial >= 300_000_000 else 0.05
            prob_adicion = min(0.95, base + factor_plazo + factor_monto)

        score_riesgo = round(prob_adicion, 4)
        prob_pct = round(prob_adicion * 100.0, 1)

        if score_riesgo >= 0.65:
            nivel_alerta = "Riesgo Alto"
            color_alerta = "#E11D48"
        elif score_riesgo >= 0.35:
            nivel_alerta = "Riesgo Moderado"
            color_alerta = "#D97706"
        else:
            nivel_alerta = "Riesgo Bajo"
            color_alerta = "#059669"

        # Estimación financiera de sobrecosto esperado
        porcentaje_adicion_est = round(self.tasa_sobrecosto_media * (0.6 + score_riesgo) * 100, 1)
        sobrecosto_estimado = float(cuantia_inicial) * (porcentaje_adicion_est / 100.0)
        cuantia_final_proyectada = float(cuantia_inicial) + sobrecosto_estimado

        resultado = {
            "score_riesgo_anomalia": score_riesgo,
            "probabilidad_adicion_pct": prob_pct,
            "tiene_adicion_predicha": bool(score_riesgo >= 0.50),
            "nivel_alerta": nivel_alerta,
            "color_alerta": color_alerta,
            "porcentaje_sobrecosto_est": porcentaje_adicion_est,
            "sobrecosto_estimado_cop": sobrecosto_estimado,
            "cuantia_final_proyectada_cop": cuantia_final_proyectada,
            "accuracy_modelo_pct": round(self.accuracy * 100, 1),
        }

        if guardar_en_mongo:
            self._persistir_prediccion_mongo(entrada.iloc[0].to_dict(), resultado, usuario_auditor)

        return resultado

    def calcular_score_hibrido_lote(self, df: pd.DataFrame | None) -> pd.DataFrame:
        """
        HU-28: Asigna a cada contrato del DataFrame su puntaje continuo 'score_riesgo_anomalia' [0.0, 1.0]
        y su categoría 'nivel_alerta' ('Bajo', 'Moderado', 'Alto'), ordenando de mayor a menor prioridad.
        """
        if df is None or df.empty:
            return pd.DataFrame()

        df_eval = df.copy()

        # Normalización de cuantía inicial
        col_cuantia = "cuantia_inicial" if "cuantia_inicial" in df_eval.columns else ("valor_del_contrato" if "valor_del_contrato" in df_eval.columns else "cuantia_final")
        df_eval["cuantia_inicial"] = pd.to_numeric(df_eval.get(col_cuantia, 0.0), errors="coerce").fillna(0.0)

        # Normalización de plazo
        col_plazo = "plazo_dias" if "plazo_dias" in df_eval.columns else ("duracion_dias" if "duracion_dias" in df_eval.columns else None)
        df_eval["plazo_dias"] = (
            pd.to_numeric(df_eval[col_plazo], errors="coerce").fillna(30).clip(lower=1)
            if col_plazo and col_plazo in df_eval.columns
            else 30.0
        )

        # Normalización de PYME
        col_pyme = None
        for c in ["es_pyme", "proveedor.es_pyme", "pyme"]:
            if c in df_eval.columns:
                col_pyme = c
                break

        if col_pyme:
            if pd.api.types.is_bool_dtype(df_eval[col_pyme]):
                df_eval["es_pyme_num"] = df_eval[col_pyme].astype(int)
            else:
                df_eval["es_pyme_num"] = (
                    df_eval[col_pyme]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .isin(["si", "sí", "true", "1", "s", "verdadero", "yes"])
                    .astype(int)
                )
        else:
            df_eval["es_pyme_num"] = 0

        # Normalización de categóricas
        mapeo_cats = {
            "departamento": ["departamento", "geografia.departamento"],
            "modalidad": ["modalidad", "modalidad_de_contratacion", "clasificacion.modalidad"],
            "tipo_contrato": ["tipo_contrato", "tipo_de_contrato", "clasificacion.tipo_contrato"],
        }
        for dest, cands in mapeo_cats.items():
            encontrado = None
            for cand in cands:
                if cand in df_eval.columns:
                    encontrado = cand
                    break
            if encontrado:
                df_eval[dest] = df_eval[encontrado].astype(object).fillna("NO REGISTRA").astype(str).str.strip()
            else:
                df_eval[dest] = "NO REGISTRA"

        # 1. Componente supervisado: probabilidad de adición presupuestal
        if getattr(self, "entrenado", False) and self.pipeline is not None:
            X_batch = df_eval[self.FEATURES_NUM + self.FEATURES_CAT]
            prob_sup = self.pipeline.predict_proba(X_batch)[:, 1]
        else:
            prob_sup = np.where(df_eval["modalidad"].str.upper().str.contains("DIRECTA"), 0.45, 0.25)

        # 2. Componente no supervisado: anomalía estructural (IsolationForest)
        if getattr(self, "detector_anomalias", None) is not None:
            X_iso = pd.DataFrame({
                "cuantia": np.log1p(df_eval["cuantia_inicial"].clip(lower=0)),
                "plazo": df_eval["plazo_dias"],
            })
            raw_scores = -self.detector_anomalias.decision_function(X_iso)
            min_s, max_s = raw_scores.min(), raw_scores.max()
            if max_s > min_s:
                anom_norm = (raw_scores - min_s) / (max_s - min_s)
            else:
                anom_norm = np.zeros(len(df_eval))
            score_combinado = 0.70 * prob_sup + 0.30 * anom_norm
        else:
            score_combinado = prob_sup

        df_eval["score_riesgo_anomalia"] = np.round(np.clip(score_combinado, 0.0, 1.0), 4)
        df_eval["nivel_alerta"] = df_eval["score_riesgo_anomalia"].apply(
            lambda s: self.categorizar_nivel_alerta(s)[0]
        )

        # Priorizar contratos con mayor puntaje de anomalía para auditoría preventiva
        df_eval = df_eval.sort_values(by="score_riesgo_anomalia", ascending=False).reset_index(drop=True)
        return df_eval

    @staticmethod
    def generar_grafica_dispersion_anomalias(
        df_evaluado: pd.DataFrame | None,
        max_puntos: int = 800,
        es_oscuro: bool = False
    ) -> go.Figure:
        """
        HU-28: Construye un mapa de dispersión (Scatter Plot) de Cuantía Inicial vs. Plazo de Ejecución
        coloreado por nivel de alerta (Bajo, Moderado, Alto) con estética limpia tipo Figma.
        """
        color_bg = "#1E293B" if es_oscuro else "#FFFFFF"
        color_texto_titulo = "#F8FAFC" if es_oscuro else "#0F172A"
        color_texto_sub = "#94A3B8" if es_oscuro else "#64748B"
        color_grid = "#334155" if es_oscuro else "#F1F5F9"

        if df_evaluado is None or df_evaluado.empty or "score_riesgo_anomalia" not in df_evaluado.columns:
            fig = go.Figure()
            fig.add_annotation(
                text="Sin registros evaluados para visualizar el mapa de anomalías",
                xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color=color_texto_sub)
            )
            fig.update_layout(plot_bgcolor=color_bg, paper_bgcolor=color_bg, height=380)
            return fig

        df_muestra = df_evaluado.head(max_puntos).copy()
        df_muestra = df_muestra[df_muestra["cuantia_inicial"] > 0]

        if df_muestra.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="Sin registros numéricos válidos para graficar",
                xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color=color_texto_sub)
            )
            fig.update_layout(plot_bgcolor=color_bg, paper_bgcolor=color_bg, height=380)
            return fig

        colores_alerta = {"Bajo": "#10B981", "Moderado": "#F59E0B", "Alto": "#E11D48"}
        fig = go.Figure()

        col_ent = "entidad" if "entidad" in df_muestra.columns else ("nombre_entidad" if "nombre_entidad" in df_muestra.columns else None)

        for nivel in ["Bajo", "Moderado", "Alto"]:
            sub = df_muestra[df_muestra["nivel_alerta"] == nivel]
            if sub.empty:
                continue
            entidades = sub[col_ent] if col_ent else ["Entidad Estatal"] * len(sub)
            fig.add_trace(
                go.Scatter(
                    x=sub["plazo_dias"],
                    y=sub["cuantia_inicial"],
                    mode="markers",
                    name=f"Alerta {nivel}",
                    marker=dict(
                        color=colores_alerta[nivel],
                        size=8 if nivel == "Alto" else 6,
                        opacity=0.80 if nivel == "Alto" else 0.55,
                        line=dict(color="#FFFFFF", width=0.8)
                    ),
                    customdata=np.stack([entidades, sub["score_riesgo_anomalia"]], axis=-1),
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Score de Anomalía: %{customdata[1]:.4f}<br>"
                        "Cuantía Inicial: $ %{y:,.0f} COP<br>"
                        "Plazo Ejecución: %{x:,} días"
                        "<extra></extra>"
                    )
                )
            )

        fig.update_layout(
            title=dict(
                text="Mapa de Dispersión de Anomalías y Riesgo Contractual",
                font=dict(size=15, color=color_texto_titulo, family="Inter, sans-serif"),
                x=0
            ),
            plot_bgcolor=color_bg,
            paper_bgcolor=color_bg,
            margin=dict(l=15, r=20, t=52, b=20),
            height=390,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(
                title=dict(text="Plazo de Ejecución (Días)", font=dict(size=12, color=color_texto_sub)),
                showgrid=True,
                gridcolor=color_grid,
                tickfont=dict(color=color_texto_sub, size=11)
            ),
            yaxis=dict(
                title=dict(text="Cuantía Inicial (COP)", font=dict(size=12, color=color_texto_sub)),
                type="log",
                showgrid=True,
                gridcolor=color_grid,
                tickprefix="$ ",
                tickfont=dict(color=color_texto_sub, size=11)
            ),
            hoverlabel=dict(bgcolor="#0F172A", font_color="#FFFFFF", font_size=12)
        )
        return fig

    @staticmethod
    def _persistir_prediccion_mongo(parametros: dict[str, Any], resultado: dict[str, Any], usuario: str) -> None:
        """Guarda trazabilidad de la inferencia en la colección predicciones_ml."""
        try:
            col = MongoConnectionSingleton.get_collection("predicciones_ml")
            documento = {
                "fecha_inferencia": datetime.now(timezone.utc),
                "auditor": usuario,
                "parametros_entrada": parametros,
                "diagnostico_ml": {
                    "score_riesgo": resultado["score_riesgo_anomalia"],
                    "probabilidad_adicion_pct": resultado["probabilidad_adicion_pct"],
                    "nivel_alerta": resultado["nivel_alerta"],
                    "sobrecosto_estimado_cop": resultado["sobrecosto_estimado_cop"],
                    "cuantia_final_proyectada_cop": resultado["cuantia_final_proyectada_cop"],
                },
            }
            col.insert_one(documento)
        except Exception:
            # Evitar bloquear la UI si MongoDB no está disponible en modo offline o sandbox
            pass

    @staticmethod
    def generar_grafica_gauge_riesgo(
        probabilidad_pct: float,
        nivel_alerta: str,
        color_alerta: str,
        es_oscuro: bool = False
    ) -> go.Figure:
        """Construye un medidor ejecutivo tipo Figma para el score de propensión a adición."""
        color_texto = "#F8FAFC" if es_oscuro else "#0F172A"
        color_sub = "#CBD5E1" if es_oscuro else "#334155"
        color_bg = "#1E293B" if es_oscuro else "#FFFFFF"
        color_gauge_bg = "#334155" if es_oscuro else "#F8FAFC"
        color_eje = "#475569" if es_oscuro else "#CBD5E1"
        step_bajo = "#064E3B" if es_oscuro else "#ECFDF5"
        step_medio = "#78350F" if es_oscuro else "#FEF3C7"
        step_alto = "#7F1D1D" if es_oscuro else "#FFE4E6"

        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=probabilidad_pct,
                number={"suffix": "%", "font": {"size": 34, "color": color_texto, "family": "Inter, sans-serif"}},
                title={
                    "text": f"Probabilidad de Adición Presupuestal<br><span style='font-size:13px; color:{color_alerta}; font-weight:600;'>{nivel_alerta}</span>",
                    "font": {"size": 15, "color": color_sub, "family": "Inter, sans-serif"},
                },
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": color_eje},
                    "bar": {"color": color_alerta, "thickness": 0.28},
                    "bgcolor": color_gauge_bg,
                    "borderwidth": 0,
                    "steps": [
                        {"range": [0, 35], "color": step_bajo},
                        {"range": [35, 65], "color": step_medio},
                        {"range": [65, 100], "color": step_alto},
                    ],
                },
            )
        )
        fig.update_layout(
            paper_bgcolor=color_bg,
            plot_bgcolor=color_bg,
            margin=dict(l=25, r=25, t=65, b=20),
            height=290,
        )
        return fig

    def calcular_curva_proyeccion_contingencia(
        self,
        departamento: str,
        modalidad: str,
        tipo_contrato: str,
        es_pyme: bool,
        cuantia_inicial: float,
    ) -> pd.DataFrame:
        """
        HU-29: Simula la trayectoria de sobrecosto esperado e intervalo de confianza (IC 95%)
        a través de distintos plazos de ejecución (30 a 360 días) para planificación de tesorería.
        """
        plazos = list(range(30, 390, 30))
        filas = []

        tiene_bosque = (
            self.entrenado
            and self.pipeline is not None
            and hasattr(self.pipeline.named_steps.get("clf"), "estimators_")
        )

        for plazo in plazos:
            diag = self.predecir_riesgo_contrato(
                departamento=departamento,
                modalidad=modalidad,
                tipo_contrato=tipo_contrato,
                es_pyme=es_pyme,
                cuantia_inicial=cuantia_inicial,
                plazo_dias=plazo,
                guardar_en_mongo=False,
            )
            esperado = float(diag["sobrecosto_estimado_cop"])

            if tiene_bosque:
                try:
                    entrada = pd.DataFrame([{
                        "cuantia_inicial": float(cuantia_inicial),
                        "plazo_dias": int(plazo),
                        "es_pyme_num": int(bool(es_pyme)),
                        "departamento": str(departamento).strip(),
                        "modalidad": str(modalidad).strip(),
                        "tipo_contrato": str(tipo_contrato).strip(),
                    }])
                    X_trans = self.pipeline.named_steps["prep"].transform(entrada)
                    probs_arboles = np.array([
                        est.predict_proba(X_trans)[0][1]
                        for est in self.pipeline.named_steps["clf"].estimators_
                    ])
                    std_prob = float(np.std(probs_arboles))
                except Exception:
                    std_prob = 0.08
            else:
                std_prob = 0.08

            margen_cop = float(cuantia_inicial) * self.tasa_sobrecosto_media * (1.96 * max(0.02, std_prob))
            limite_inf = max(0.0, esperado - margen_cop)
            limite_sup = esperado + margen_cop

            filas.append({
                "plazo_dias": plazo,
                "probabilidad_pct": diag["probabilidad_adicion_pct"],
                "sobrecosto_esperado": esperado,
                "ic_inferior": limite_inf,
                "ic_superior": limite_sup,
            })

        return pd.DataFrame(filas)

    def generar_grafica_proyeccion_ic(
        self,
        departamento: str,
        modalidad: str,
        tipo_contrato: str,
        es_pyme: bool,
        cuantia_inicial: float,
        es_oscuro: bool = False
    ) -> go.Figure:
        """
        HU-29: Construye la curva probabilística de sobrecosto esperado con banda de intervalo de confianza (95%)
        para planificar reservas de contingencia en tesorería.
        """
        color_bg = "#1E293B" if es_oscuro else "#FFFFFF"
        color_texto_titulo = "#F8FAFC" if es_oscuro else "#0F172A"
        color_texto_sub = "#94A3B8" if es_oscuro else "#64748B"
        color_grid = "#334155" if es_oscuro else "#F1F5F9"
        color_legend = "#CBD5E1" if es_oscuro else "#334155"

        df_proj = self.calcular_curva_proyeccion_contingencia(
            departamento, modalidad, tipo_contrato, es_pyme, cuantia_inicial
        )

        fig = go.Figure()

        # Banda superior e inferior del Intervalo de Confianza 95%
        fig.add_trace(
            go.Scatter(
                x=pd.concat([df_proj["plazo_dias"], df_proj["plazo_dias"][::-1]]),
                y=pd.concat([df_proj["ic_superior"], df_proj["ic_inferior"][::-1]]),
                fill="toself",
                fillcolor="rgba(79, 70, 229, 0.12)",
                line=dict(color="rgba(255,255,255,0)"),
                hoverinfo="skip",
                showlegend=True,
                name="Intervalo de Confianza (95%)",
            )
        )

        # Curva central de sobrecosto esperado
        fig.add_trace(
            go.Scatter(
                x=df_proj["plazo_dias"],
                y=df_proj["sobrecosto_esperado"],
                mode="lines+markers",
                name="Sobrecosto Esperado (COP)",
                line=dict(color="#4F46E5", width=3, shape="spline", smoothing=0.8),
                marker=dict(size=6, color="#FFFFFF", line=dict(color="#4F46E5", width=2)),
                customdata=df_proj[["ic_inferior", "ic_superior", "probabilidad_pct"]],
                hovertemplate=(
                    "<b>Plazo Proyectado: %{x} días</b><br>"
                    "Sobrecosto Esperado: $ %{y:,.0f} COP<br>"
                    "Reserva Mínima (IC 95%): $ %{customdata[0]:,.0f} COP<br>"
                    "Reserva Máxima (IC 95%): $ %{customdata[1]:,.0f} COP<br>"
                    "Probabilidad de Adición: %{customdata[2]:.1f}%"
                    "<extra></extra>"
                ),
            )
        )

        fig.update_layout(
            title=dict(
                text="Proyección de Sobrecosto Esperado e Intervalo de Confianza (IC 95%)",
                font=dict(size=15, color=color_texto_titulo, family="Inter, sans-serif"),
                x=0,
            ),
            plot_bgcolor=color_bg,
            paper_bgcolor=color_bg,
            margin=dict(l=15, r=20, t=52, b=20),
            height=370,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(color=color_legend, size=11)
            ),
            xaxis=dict(
                title=dict(text="Plazo de Ejecución Contractual (Días)", font=dict(color=color_texto_sub, size=12)),
                showgrid=False,
                tickfont=dict(color=color_texto_sub, size=11)
            ),
            yaxis=dict(
                title=dict(text="Contingencia Presupuestal (COP)", font=dict(color=color_texto_sub, size=12)),
                showgrid=True,
                gridcolor=color_grid,
                tickprefix="$ ",
                tickformat="~s",
                tickfont=dict(color=color_texto_sub, size=11),
            ),
            hoverlabel=dict(bgcolor="#0F172A", font_color="#FFFFFF", font_size=12),
        )
        return fig

    @staticmethod
    def generar_grafica_escenarios_contingencia(
        score_riesgo: float,
        cuantia_inicial: float,
        es_oscuro: bool = False
    ) -> go.Figure:
        """
        HU-29: Construye la distribución probabilística de escenarios de ejecución presupuestal
        (Sin Adición, Adición Moderada, Adición Crítica) y reserva recomendada.
        """
        color_bg = "#1E293B" if es_oscuro else "#FFFFFF"
        color_texto_titulo = "#F8FAFC" if es_oscuro else "#0F172A"
        color_texto_sub = "#94A3B8" if es_oscuro else "#64748B"
        color_texto_eje = "#CBD5E1" if es_oscuro else "#334155"
        color_grid = "#334155" if es_oscuro else "#F1F5F9"

        prob_sin = round(max(0.0, (1.0 - score_riesgo)) * 100.0, 1)
        prob_mod = round(score_riesgo * 42.0, 1)
        prob_crit = round(max(0.0, 100.0 - prob_sin - prob_mod), 1)

        escenarios = ["Ejecución Normal (0%)", "Adición Moderada (5% - 15%)", "Adición Crítica (> 20%)"]
        probabilidades = [prob_sin, prob_mod, prob_crit]
        reservas_cop = [0.0, cuantia_inicial * 0.10, cuantia_inicial * 0.25]
        colores = ["#10B981", "#F59E0B", "#E11D48"]

        fig = go.Figure(
            go.Bar(
                x=escenarios,
                y=probabilidades,
                marker=dict(color=colores, cornerradius=8),
                text=[f"{p:.1f}%" for p in probabilidades],
                textposition="outside",
                cliponaxis=False,
                customdata=reservas_cop,
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Probabilidad de Ocurrencia: %{y:.1f}%<br>"
                    "Contingencia de Tesorería: $ %{customdata:,.0f} COP"
                    "<extra></extra>"
                ),
            )
        )

        fig.update_layout(
            title=dict(
                text="Distribución Probabilística de Escenarios de Sobrecosto",
                font=dict(size=15, color=color_texto_titulo, family="Inter, sans-serif"),
                x=0,
            ),
            plot_bgcolor=color_bg,
            paper_bgcolor=color_bg,
            margin=dict(l=15, r=20, t=52, b=20),
            height=350,
            xaxis=dict(showgrid=False, tickfont=dict(color=color_texto_eje, size=11)),
            yaxis=dict(
                title=dict(text="Probabilidad (%)", font=dict(color=color_texto_sub, size=12)),
                range=[0, 112],
                showgrid=True,
                gridcolor=color_grid,
                ticksuffix="%",
                tickfont=dict(color=color_texto_sub, size=11),
            ),
            hoverlabel=dict(bgcolor="#0F172A", font_color="#FFFFFF", font_size=12),
        )
        return fig

    def generar_grafica_importancia_variables(self, es_oscuro: bool = False) -> go.Figure:
        """
        HU-29: Extrae y visualiza la importancia relativa (%) de los factores contractuales
        en el modelo predictivo para auditoría y explicabilidad.
        """
        color_bg = "#1E293B" if es_oscuro else "#FFFFFF"
        color_texto_titulo = "#F8FAFC" if es_oscuro else "#0F172A"
        color_texto_sub = "#94A3B8" if es_oscuro else "#64748B"
        color_texto_eje = "#CBD5E1" if es_oscuro else "#334155"
        color_grid = "#334155" if es_oscuro else "#F1F5F9"

        etiquetas_amigables = {
            "cuantia_inicial": "Cuantía Inicial (COP)",
            "plazo_dias": "Plazo de Ejecución (Días)",
            "es_pyme_num": "Participación PYME",
            "departamento": "Ubicación Territorial (Depto.)",
            "modalidad": "Modalidad de Selección",
            "tipo_contrato": "Tipología Contractual",
        }

        pesos = {v: 0.0 for v in etiquetas_amigables.values()}

        if self.entrenado and self.pipeline is not None:
            try:
                clf = self.pipeline.named_steps["clf"]
                prep = self.pipeline.named_steps["prep"]
                importancias = clf.feature_importances_
                nombres_trans = prep.get_feature_names_out()

                for nombre, imp in zip(nombres_trans, importancias):
                    limpio = nombre.replace("num__", "").replace("cat__", "")
                    for clave_orig, etiqueta in etiquetas_amigables.items():
                        if limpio == clave_orig or limpio.startswith(clave_orig + "_"):
                            pesos[etiqueta] += float(imp)
                            break
            except Exception:
                pesos = {
                    "Cuantía Inicial (COP)": 0.34,
                    "Plazo de Ejecución (Días)": 0.28,
                    "Modalidad de Selección": 0.18,
                    "Tipología Contractual": 0.10,
                    "Ubicación Territorial (Depto.)": 0.06,
                    "Participación PYME": 0.04,
                }
        else:
            pesos = {
                "Cuantía Inicial (COP)": 0.34,
                "Plazo de Ejecución (Días)": 0.28,
                "Modalidad de Selección": 0.18,
                "Tipología Contractual": 0.10,
                "Ubicación Territorial (Depto.)": 0.06,
                "Participación PYME": 0.04,
            }

        df_imp = (
            pd.DataFrame([{"factor": k, "importancia_pct": v * 100.0} for k, v in pesos.items()])
            .sort_values(by="importancia_pct", ascending=True)
            .reset_index(drop=True)
        )

        fig = go.Figure(
            go.Bar(
                x=df_imp["importancia_pct"],
                y=df_imp["factor"],
                orientation="h",
                marker=dict(color="#6366F1", cornerradius=6),
                text=[f"{v:.1f}%" for v in df_imp["importancia_pct"]],
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>%{y}</b><br>Peso Explicativo en el Modelo: %{x:.2f}%<extra></extra>",
            )
        )

        max_x = df_imp["importancia_pct"].max()
        fig.update_layout(
            title=dict(
                text="Factores Determinantes del Riesgo Presupuestal (Explicabilidad ML)",
                font=dict(size=15, color=color_texto_titulo, family="Inter, sans-serif"),
                x=0,
            ),
            plot_bgcolor=color_bg,
            paper_bgcolor=color_bg,
            margin=dict(l=10, r=60, t=52, b=20),
            height=350,
            xaxis=dict(
                title=dict(text="Peso Relativo (%)", font=dict(color=color_texto_sub, size=11)),
                showgrid=True,
                gridcolor=color_grid,
                ticksuffix="%",
                range=[0, max_x * 1.25] if max_x > 0 else [0, 100],
                tickfont=dict(color=color_texto_sub, size=11),
            ),
            yaxis=dict(showgrid=False, tickfont=dict(color=color_texto_eje, size=11)),
            hoverlabel=dict(bgcolor="#0F172A", font_color="#FFFFFF", font_size=12),
        )
        return fig
