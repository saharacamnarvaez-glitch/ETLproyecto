import os
import sqlite3
from pathlib import Path
import pandas as pd

try:
    from medallon.src.logger import get_logger
except ImportError:
    from src.logger import get_logger

logger = get_logger("Carga_DataWarehouse")

BASE_DIR = Path(__file__).resolve().parents[3]
DEFAULT_CSV = str(BASE_DIR / "data" / "gold" / "gold_final.csv")
DEFAULT_DEPT_CSV = str(BASE_DIR / "data" / "gold" / "gold_referencia_departamental.csv")
DEFAULT_DB = str(BASE_DIR / "data" / "warehouse" / "etl_warehouse.db")
LLAVE_COMPUESTA_GOLD = ["institucion", "programa", "departamento", "periodo"]


def _validar_unicidad_antes_de_cargar(df, claves=None):
    """Verifica que no haya llaves compuestas duplicadas antes de cargar al warehouse."""
    if claves is None:
        claves = LLAVE_COMPUESTA_GOLD
    columnas_presentes = [c for c in claves if c in df.columns]
    if not columnas_presentes:
        return True
    duplicados = df.duplicated(subset=columnas_presentes).sum()
    if duplicados > 0:
        logger.error(
            f"Carga abortada: se detectaron {duplicados} registros duplicados "
            f"en la llave compuesta {columnas_presentes}."
        )
        return False
    return True


def cargar_datos(df, destino=None, formato="csv", tabla="gold_final", validar_llave=True):
    """
    Carga un DataFrame a un destino de almacenamiento (CSV o Data Warehouse SQLite).
    """
    if df is None or df.empty:
        logger.warning("DataFrame vacío o None. No se carga nada.")
        return False

    if validar_llave and not _validar_unicidad_antes_de_cargar(df):
        return False

    if destino is None:
        destino = DEFAULT_DB if formato == "sqlite" else DEFAULT_CSV

    try:
        os.makedirs(os.path.dirname(os.path.abspath(destino)), exist_ok=True)

        if formato == "csv":
            df.to_csv(destino, index=False, encoding="utf-8-sig")
            logger.info(
                f"Datos cargados en CSV: {destino} "
                f"({len(df)} registros, {len(df.columns)} columnas)"
            )

        elif formato == "sqlite":
            with sqlite3.connect(destino) as conn:
                df.to_sql(tabla, conn, if_exists="replace", index=False)
            logger.info(
                f"Datos cargados en SQLite: {destino} -> tabla '{tabla}' "
                f"({len(df)} registros)"
            )

        else:
            logger.error(f"Formato no soportado: {formato}. Use 'csv' o 'sqlite'.")
            return False

        return True

    except Exception as e:
        logger.error(f"Error al cargar datos al datawarehouse: {e}")
        return False


def cargar_desde_csv(ruta_csv=DEFAULT_CSV, destino=DEFAULT_DB, tabla="gold_final", claves_unicidad=None):
    """Carga un archivo CSV de Gold directamente al Data Warehouse SQLite."""
    if not os.path.exists(ruta_csv):
        logger.error(f"No se encontró el archivo CSV: {ruta_csv}")
        return False
    df = pd.read_csv(ruta_csv, low_memory=False)
    if claves_unicidad is not None and not _validar_unicidad_antes_de_cargar(df, claves=claves_unicidad):
        return False
    return cargar_datos(df, destino=destino, formato="sqlite", tabla=tabla, validar_llave=(claves_unicidad is None))


def ejecutar_carga_completa():
    """Carga las dos tablas Gold (entidad y referencia departamental) al Data Warehouse."""
    ok_entidad = cargar_desde_csv(
        ruta_csv=DEFAULT_CSV,
        destino=DEFAULT_DB,
        tabla="gold_final",
        claves_unicidad=LLAVE_COMPUESTA_GOLD,
    )

    ok_depto = True
    if os.path.exists(DEFAULT_DEPT_CSV):
        ok_depto = cargar_desde_csv(
            ruta_csv=DEFAULT_DEPT_CSV,
            destino=DEFAULT_DB,
            tabla="gold_referencia_departamental",
            claves_unicidad=["departamento"],
        )
    else:
        logger.warning(f"No se encontró {DEFAULT_DEPT_CSV}; se omite tabla departamental.")

    return ok_entidad and ok_depto


if __name__ == "__main__":
    if ejecutar_carga_completa():
        print(f"Carga completa exitosa en SQLite: {DEFAULT_DB}")
    else:
        logger.error("La carga al Data Warehouse finalizó con errores.")