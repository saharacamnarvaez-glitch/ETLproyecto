import os
import sys
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.transform.transform_silver import (
    limpiar_dato, limpiar_columna, clean_dane_code,
    validar_cardinalidad, _construir_llave_compuesta, _buscar_columnas,
    _resolver_tasas_divergentes,
)


class TestLimpieza:
    def test_limpiar_dato(self):
        assert limpiar_dato(" Universidad de Narino ") == "universidad de narino"
        assert limpiar_dato("  CASA   Y  LUGAR  ") == "casa y lugar"
        assert limpiar_dato(None) == ""
        assert limpiar_dato(float("nan")) == ""

    def test_limpiar_columna(self):
        assert limpiar_columna("TD - Departamento") == "td_departamento"
        assert limpiar_columna("  Tasa de Desercion  ") == "tasa_de_desercion"


class TestDANE:
    def test_clean_dane_code(self):
        assert clean_dane_code("5", 2) == "05"
        assert clean_dane_code("15.0", 5) == "00015"
        assert clean_dane_code(None, 5) is None
        assert clean_dane_code("", 5) is None


class TestCardinalidadSimple:
    def test_validar_cardinalidad_valida(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        valido, msg = validar_cardinalidad(df, ["a"], "test")
        assert valido is True

    def test_validar_cardinalidad_duplicados(self):
        df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "y", "z"]})
        valido, msg = validar_cardinalidad(df, ["a"], "test")
        assert valido is False
        assert "duplic" in msg.lower()


class TestLlaveCompuesta:
    def test_construir_llave_compuesta(self):
        df = pd.DataFrame({
            "institucion": ["Univ A", "Univ B"],
            "departamento": ["05", "08"],
        })
        llave = _construir_llave_compuesta(df, ["institucion", "departamento"])
        assert list(llave) == ["univ a_05", "univ b_08"]

    def test_buscar_columnas(self):
        df = pd.DataFrame({"TD - departamento": [], "otra": []})
        cols = _buscar_columnas(df, ["departamento"])
        assert "TD - departamento" in cols


class TestTasasDivergentes:
    def test_resolver_tasas_divergentes_promedio(self):
        df = pd.DataFrame({
            "institucion": ["Univ A", "Univ A"],
            "programa": ["Ing", "Ing"],
            "tasa": [0.10, 0.30],
        })
        df_res, conflictos = _resolver_tasas_divergentes(
            df, ["institucion", "programa"], "tasa"
        )
        assert len(conflictos) == 1
        assert df_res["tasa"].nunique() == 1
        assert abs(df_res["tasa"].iloc[0] - 0.20) < 1e-9
        assert df_res["_flag_tasa_divergente"].all()

    def test_resolver_tasas_divergentes_sin_conflicto(self):
        df = pd.DataFrame({
            "institucion": ["Univ A", "Univ B"],
            "programa": ["Ing", "Med"],
            "tasa": [0.10, 0.20],
        })
        df_res, conflictos = _resolver_tasas_divergentes(
            df, ["institucion", "programa"], "tasa"
        )
        assert len(conflictos) == 0
        assert not df_res["_flag_tasa_divergente"].any()

    def test_resolver_sin_columna_tasa(self):
        df = pd.DataFrame({"institucion": ["Univ A"]})
        df_res, conflictos = _resolver_tasas_divergentes(df, ["institucion"], "tasa_inexistente")
        assert len(conflictos) == 0
        assert df_res.equals(df)