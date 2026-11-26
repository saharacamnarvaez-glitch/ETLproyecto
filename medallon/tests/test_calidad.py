import os
import sys
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestCalidadIndicadores:
    def test_tasa_en_rango_valido(self):
        """Las tasas de deserción deben estar entre 0 y 1."""
        df = pd.DataFrame({"tasa": [0.0, 0.5, 1.0, -0.1, 1.5]})
        validos = df[(df["tasa"] >= 0) & (df["tasa"] <= 1)]
        assert len(validos) == 3

    def test_no_nulos_en_claves_criticas(self):
        df = pd.DataFrame({
            "institucion": ["Univ A", None, "Univ C"],
            "programa": ["Ing", "Med", None],
        })
        cols = ["institucion", "programa"]
        nulos = df[cols].isna().any(axis=1).sum()
        assert nulos == 2

    def test_duplicados_por_llave_compuesta(self):
        df = pd.DataFrame({
            "institucion": ["A", "A", "B"],
            "departamento": ["05", "05", "08"],
            "programa": ["Ing", "Ing", "Med"],
            "periodo": ["2015", "2015", "2015"],
        })
        dup = df[df.duplicated(subset=["institucion", "departamento", "programa", "periodo"], keep=False)]
        assert len(dup) == 2

    def test_distribucion_riesgo_valores_permitidos(self):
        df = pd.DataFrame({"nivel_riesgo": ["Riesgo Bajo", "Riesgo Medio", "Riesgo Alto", "Sin Datos"]})
        permitidos = {"Riesgo Bajo", "Riesgo Medio", "Riesgo Alto", "Sin Datos"}
        assert set(df["nivel_riesgo"].unique()).issubset(permitidos)

    def test_matriculas_no_negativas(self):
        df = pd.DataFrame({"total_matriculas": [100, 200, -50, 0]})
        validos = df[df["total_matriculas"] >= 0]
        assert len(validos) == 3