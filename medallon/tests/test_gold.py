import os
import sys
import tempfile
import shutil
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.transform.transform_gold import ejecutar_transformacion_gold, _detectar_columna


def _escribir_silver(ruta, df):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    df.to_csv(ruta, index=False, encoding='utf-8')


class TestDetectarColumna:
    def test_detectar_columna(self):
        df = pd.DataFrame({"TD - Departamento": [], "Otra Columna": []})
        col = _detectar_columna(df, ["departamento"])
        assert col == "TD - Departamento"


class TestTransformGold:
    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.ruta_silver = os.path.join(self.tmp, "silver_dataset_integrado.csv")
        self.ruta_gold = os.path.join(self.tmp, "gold_final.csv")

    def teardown_method(self):
        shutil.rmtree(self.tmp)

    def _mock_config(self, ruta_silver, ruta_gold):
        import src.transform.transform_gold as tg
        original = tg.cargar_configuracion
        tg.cargar_configuracion = lambda: {
            'paths': {'silver_dataset_integrado': ruta_silver, 'gold_final': ruta_gold}
        }
        return original

    def test_ejecutar_transformacion_gold(self):
        df = pd.DataFrame({
            "institucion": ["Universidad A", "Universidad B", "Universidad C", "Universidad D"],
            "departamento": ["05", "08", "15", "05"],
            "programa": ["Ingenieria", "Medicina", "Derecho", "Ingenieria"],
            "total_matriculas": [1000, 2000, 1500, 800],
            "tasa_desercion_2021": [0.10, 0.40, 0.25, 0.12],
        })
        _escribir_silver(self.ruta_silver, df)
        original = self._mock_config(self.ruta_silver, self.ruta_gold)
        try:
            exito = ejecutar_transformacion_gold()
            assert exito is True
            assert os.path.exists(self.ruta_gold)
            df_gold = pd.read_csv(self.ruta_gold)
            assert 'nivel_riesgo' in df_gold.columns
            assert 'institucion' in df_gold.columns
            assert 'fuente_tasa' in df_gold.columns
            assert 'es_tasa_referencia_departamental' in df_gold.columns
            assert 'granularidad_riesgo' in df_gold.columns
            # No debe haber 'Sin Datos' si todas las tasas son válidas
            assert (df_gold['nivel_riesgo'] != 'Sin Datos').all()
        finally:
            import src.transform.transform_gold as tg
            tg.cargar_configuracion = original

    def test_nivel_riesgo_no_usa_tasa_departamental_generica(self):
        """La tasa usada debe ser la propia de cada entidad, no una tasa departamental genérica."""
        df = pd.DataFrame({
            "institucion": ["Universidad A", "Universidad B"],
            "departamento": ["05", "05"],
            "programa": ["Ingenieria", "Medicina"],
            "total_matriculas": [1000, 2000],
            # Mismo departamento, tasas distintas -> prueba que se usa tasa propia
            "tasa_desercion_2021": [0.10, 0.50],
        })
        _escribir_silver(self.ruta_silver, df)
        original = self._mock_config(self.ruta_silver, self.ruta_gold)
        try:
            exito = ejecutar_transformacion_gold()
            assert exito is True
            df_gold = pd.read_csv(self.ruta_gold)
            # Ambas instituciones deben tener nivel_riesgo distinto si sus tasas difieren
            tasas = df_gold.set_index('institucion')['tasa_desercion_2021']
            assert tasas["Universidad A"] == 0.10
            assert tasas["Universidad B"] == 0.50
            # Es_tasa_referencia_departamental debe ser False (tasa propia)
            assert (df_gold['es_tasa_referencia_departamental'] == False).all()
        finally:
            import src.transform.transform_gold as tg
            tg.cargar_configuracion = original

    def test_sin_tasa_a_nivel_entidad_es_sin_datos(self):
        """Si no hay columna de tasa, nivel_riesgo debe ser 'Sin Datos', no inferirse del departamento."""
        df = pd.DataFrame({
            "institucion": ["Universidad A", "Universidad B"],
            "departamento": ["05", "08"],
            "programa": ["Ingenieria", "Medicina"],
            "total_matriculas": [1000, 2000],
        })
        _escribir_silver(self.ruta_silver, df)
        original = self._mock_config(self.ruta_silver, self.ruta_gold)
        try:
            exito = ejecutar_transformacion_gold()
            assert exito is True
            df_gold = pd.read_csv(self.ruta_gold)
            assert (df_gold['nivel_riesgo'] == 'Sin Datos').all()
        finally:
            import src.transform.transform_gold as tg
            tg.cargar_configuracion = original