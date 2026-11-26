import os
import sys
import tempfile
import shutil
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from medallon.src.transform.transform_silver import (
    limpiar_dato, limpiar_columna, clean_dane_code,
    validar_cardinalidad, validar_cardinalidad_join,
    _construir_llave_compuesta, _buscar_columnas,
    _resolver_tasas_divergentes, LLAVES_EXPLICITAS,
)
from medallon.src.transform.transform_gold import ejecutar_transformacion_gold


@pytest.fixture
def tmp_dirs():
    """Crea directorios temporales para silver y gold."""
    tmp = tempfile.mkdtemp()
    silver_dir = os.path.join(tmp, "silver")
    gold_dir = os.path.join(tmp, "gold")
    os.makedirs(silver_dir, exist_ok=True)
    os.makedirs(gold_dir, exist_ok=True)
    yield {"tmp": tmp, "silver": silver_dir, "gold": gold_dir}
    shutil.rmtree(tmp)


@pytest.fixture
def df_api_matricula():
    """DataFrame sintÃ©tico de matrÃ­culas (API) con llave Ãºnica."""
    return pd.DataFrame({
        "institucion": ["Universidad A", "Universidad A", "Universidad B"],
        "programa": ["Ingenieria", "Medicina", "Ingenieria"],
        "departamento": ["05", "05", "08"],
        "periodo": ["2015", "2015", "2015"],
        "matriculados": [1000, 2000, 1500],
    })


@pytest.fixture
def df_desercion_entidad():
    """DataFrame de deserciÃ³n a nivel entidad (1:1 con API)."""
    return pd.DataFrame({
        "institucion": ["Universidad A", "Universidad A", "Universidad B"],
        "programa": ["Ingenieria", "Medicina", "Ingenieria"],
        "departamento": ["05", "05", "08"],
        "periodo": ["2015", "2015", "2015"],
        "tasa_desercion": [0.10, 0.20, 0.15],
    })


@pytest.fixture
def df_desercion_tasas_divergentes():
    """DataFrame con mismas llaves pero tasas distintas (para probar resoluciÃ³n)."""
    return pd.DataFrame({
        "institucion": ["Universidad A", "Universidad A"],
        "programa": ["Ingenieria", "Ingenieria"],
        "departamento": ["05", "05"],
        "periodo": ["2015", "2015"],
        "tasa_desercion": [0.10, 0.30],
        "total_matriculas": [1000, 1000],
    })


@pytest.fixture
def df_silver_integrado():
    """DataFrame integrado de Silver listo para Gold."""
    return pd.DataFrame({
        "institucion": ["Universidad A", "Universidad B", "Universidad C", "Universidad D"],
        "departamento": ["05", "08", "15", "05"],
        "programa": ["Ingenieria", "Medicina", "Derecho", "Ingenieria"],
        "total_matriculas": [1000, 2000, 1500, 800],
        "tasa_desercion_2021": [0.10, 0.40, 0.25, 0.12],
    })