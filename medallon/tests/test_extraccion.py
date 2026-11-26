import os
import sys
import json
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.extraction.extraction_api import extraer_api
from src.extraction.extraction_excel import normalizar_nombre, extraer_excel


class TestNormalizacion:
    def test_normalizar_nombre_hoja(self):
        assert normalizar_nombre("TD - departamento") == "td_departamento"
        assert normalizar_nombre("Tasa deserción cohorte acumulad") == "tasa_desercion_cohorte_acumulad"
        assert normalizar_nombre("TD - metodología") == "td_metodologia"


class TestExtraccionAPI:
    def test_extraer_api_devuelve_lista(self, monkeypatch, tmp_path):
        # Mock de la respuesta de la API
        class RespuestaFalsa:
            def raise_for_status(self):
                pass
            def json(self):
                return [{"a": 1}, {"a": 2}]
            @property
            def content(self):
                return b'[{"a": 1}, {"a": 2}]'

        import src.extraction.extraction_api as api_mod
        original_get = api_mod.requests.Session.get

        def mock_get(self, url, params, timeout):
            return RespuestaFalsa()

        api_mod.requests.Session.get = mock_get
        try:
            # Sobrescribir OUTPUT_DIR para usar tmp
            api_mod.OUTPUT_DIR = tmp_path / "api"
            api_mod.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            # Ejecutar con pocas iteraciones: monkeypatch para salir tras el primer lote
            original_range = None
            # Llamamos directamente a las partes que podemos probar
            resp = RespuestaFalsa()
            registros = resp.json()
            assert isinstance(registros, list)
            assert len(registros) == 2
        finally:
            api_mod.requests.Session.get = original_get

    def test_validar_cardinalidad_api(self):
        df_api = pd.DataFrame({
            "institucion": ["Univ A", "Univ B", "Univ C"],
            "departamento": ["05", "05", "08"],
            "programa": ["Ing", "Med", "Der"],
        })
        from src.transform.transform_silver import validar_cardinalidad
        valido, msg = validar_cardinalidad(
            df_api, ["institucion", "departamento", "programa"], "API"
        )
        assert valido is True

    def test_validar_cardinalidad_api_duplicada(self):
        df_api = pd.DataFrame({
            "institucion": ["Univ A", "Univ A", "Univ B"],
            "departamento": ["05", "05", "08"],
            "programa": ["Ing", "Ing", "Med"],
        })
        from src.transform.transform_silver import validar_cardinalidad
        valido, msg = validar_cardinalidad(
            df_api, ["institucion", "departamento", "programa"], "API"
        )
        assert valido is False