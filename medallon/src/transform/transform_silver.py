"""
Módulo de transformación para la capa Silver del pipeline ETL Medallon.
Contiene funciones de limpieza, validación y transformación de datos
provenientes de la capa Bronze, preparándolos para la capa Silver.
"""

import glob
import json
import os
import re
from pathlib import Path
import numpy as np
import pandas as pd
import yaml

BASE_DIR = str(Path(__file__).resolve().parents[3])
DATA_BRONZE = os.path.join(BASE_DIR, "data", "bronze")
DATA_SILVER = os.path.join(BASE_DIR, "data", "silver")
TRANSFORM_DIR = os.path.join(BASE_DIR, "medallon", "src", "transform")

LLAVES_EXPLICITAS = {
    "api_matricula": ["institucion", "programa", "departamento", "periodo"],
    "desercion": ["institucion", "programa", "departamento", "periodo"],
}


def limpiar_dato(valor, tipo_dato="texto"):
    """Limpia un valor individual según el tipo de dato especificado."""
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return ""
    if tipo_dato == "texto":
        cleaned = str(valor).strip().lower()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned
    elif tipo_dato == "numeric":
        return re.sub(r"[^0-9.\-]", "", str(valor))
    return str(valor)


def limpiar_columna(df_o_nombre, nombre_columna=None, tipo="texto"):
    """Normaliza un nombre de columna (str) o limpia una columna de un DataFrame."""
    if isinstance(df_o_nombre, str) and nombre_columna is None:
        nuevo_nombre = re.sub(r"[^a-zA-Z0-9\s_-]", "", df_o_nombre.strip().lower())
        nuevo_nombre = re.sub(r"[\s-]+", "_", nuevo_nombre)
        nuevo_nombre = re.sub(r"_+", "_", nuevo_nombre).strip("_")
        return nuevo_nombre

    df = df_o_nombre
    if isinstance(nombre_columna, str):
        nuevo_nombre = re.sub(r"\s+", "_", nombre_columna.strip().lower())
        nuevo_nombre = re.sub(r"-+", "_", nuevo_nombre)
        if nuevo_nombre in df.columns and nuevo_nombre != nombre_columna:
            df.rename(columns={nombre_columna: nuevo_nombre}, inplace=True)
            return df

    if nombre_columna not in df.columns:
        raise ValueError(f"Columna '{nombre_columna}' no existe en el DataFrame.")
    if tipo == "texto":
        df[nombre_columna] = df[nombre_columna].apply(lambda x: limpiar_dato(x, "texto"))
    elif tipo == "numeric":
        df[nombre_columna] = pd.to_numeric(df[nombre_columna], errors="coerce")
    return df


def clean_dane_code(codigo, longitud=7):
    """Limpia y normaliza un código DANE a formato estándar de N dígitos."""
    if codigo is None or (isinstance(codigo, float) and np.isnan(codigo)):
        return None
    texto = str(codigo).strip()
    if re.match(r"^\d+\.0+$", texto):
        texto = texto.split(".")[0]
    codigo_limpio = re.sub(r"\D", "", texto)
    if not codigo_limpio:
        return None
    if len(codigo_limpio) >= longitud:
        return codigo_limpio[:longitud]
    return codigo_limpio.zfill(longitud)


def validar_cardinalidad(df, columna, min_val=None, max_val=None):
    """Valida la unicidad de una columna o llave compuesta en un DataFrame."""
    if isinstance(columna, str):
        columnas = [columna]
    else:
        try:
            columnas = list(columna)
        except TypeError:
            columnas = [columna]

    for col in columnas:
        if col not in df.columns:
            raise ValueError(f"Columna '{col}' no existe en el DataFrame.")

    if len(columnas) == 1:
        col = columnas[0]
        conteo_no_nulo = df[col].notna().sum()
        if df[col].duplicated().any():
            return False, f"Duplicados en la columna '{col}'"
    else:
        conteo_no_nulo = len(df.dropna(subset=columnas))
        if df.duplicated(subset=columnas).any():
            return False, f"Duplicados en la llave compuesta {columnas}"

    min_val_real = float(min_val) if min_val is not None and isinstance(min_val, (int, float)) else None
    max_val_real = float(max_val) if max_val is not None and isinstance(max_val, (int, float)) else None
    if min_val_real is not None and conteo_no_nulo < min_val_real:
        return False, f"Cardinalidad mínima no cumplida: {conteo_no_nulo} < {min_val_real}"
    if max_val_real is not None and conteo_no_nulo > max_val_real:
        return False, f"Cardinalidad máxima excedida: {conteo_no_nulo} > {max_val_real}"
    return True, None


def _construir_llave_compuesta(df, columnas):
    """Construye llaves compuestas a partir de columnas especificadas, devolviendo una lista."""
    llaves = []
    for _, fila in df.iterrows():
        partes = []
        for col in columnas:
            valor = fila[col]
            if valor is None or (isinstance(valor, float) and np.isnan(valor)):
                partes.append("NULL")
            else:
                partes.append(str(valor).strip().lower())
        llaves.append("_".join(partes))
    return llaves


def validar_cardinalidad_join(df_izq, df_der, claves, claves2=None, lado_izq="izq", lado_der="der", mensaje_error="Error de cardinalidad en join"):
    """Valida la cardinalidad de un join entre dos DataFrames usando una lista de columnas clave."""
    def _hacer_llave(df, cols):
        df_copia = df.copy()
        df_copia["_key"] = df_copia[cols].apply(lambda row: "|".join(row.astype(str)), axis=1)
        return df_copia["_key"]

    keys_izq = _hacer_llave(df_izq, claves)
    keys_der = _hacer_llave(df_der, claves2 if claves2 is not None else claves)

    total_izq = len(df_izq)
    total_der = len(df_der)
    unicos_izq = keys_izq.nunique()
    unicos_der = keys_der.nunique()

    tiene_dup_izq = unicos_izq < total_izq
    tiene_dup_der = unicos_der < total_der

    if tiene_dup_izq and tiene_dup_der:
        valido = False
        tipo = "N:N"
        msg = f"{mensaje_error}: Se encontraron duplicados en ambos lados (N:N)."
    elif tiene_dup_izq:
        valido = False
        tipo = "N:1"
        msg = f"{mensaje_error}: Se encontraron valores duplicados en la izquierda (N:1)."
    elif tiene_dup_der:
        valido = True
        tipo = "N:1"
        msg = f"{mensaje_error}: Se encontraron valores duplicados en la derecha (N:1), pero es válido."
    else:
        valido = True
        tipo = "1:1"
        msg = None

    return valido, tipo, msg


def consistencia_filas_join(izq_total, der_total, filas_resultantes, tipo_join):
    """Verifica la consistencia de las filas después de realizar un join."""
    if tipo_join in ("1:1", "N:1"):
        ok = filas_resultantes <= izq_total
    else:
        ok = True
    msg = f"{filas_resultantes} filas" if not ok else None
    return ok, msg


def _resolver_tasas_divergentes(df, claves, columna_tasa=None, umbral=0.0):
    """Agrupa por llaves compuestas y resuelve tasas divergentes calculando su media."""
    if columna_tasa is None and isinstance(claves, str):
        columna_tasa = claves
        claves = []

    if columna_tasa not in df.columns:
        return df.copy(), []

    if not claves:
        if len(df) <= 1:
            df_out = df.copy()
            df_out["_flag_tasa_divergente"] = False
            return df_out, []
        min_val = df[columna_tasa].min()
        max_val = df[columna_tasa].max()
        if (max_val - min_val) > umbral:
            media = df[columna_tasa].mean()
            df_res = pd.DataFrame({columna_tasa: [media], "_flag_tasa_divergente": [True]})
            return df_res, [{"min": min_val, "max": max_val, "promedio": media}]
        df_out = df.copy()
        df_out["_flag_tasa_divergente"] = False
        return df_out, []

    conflictos = []
    filas_res = []
    for clave_grupo, grupo in df.groupby(claves, dropna=False, sort=False):
        fila_base = grupo.iloc[0].to_dict()
        if len(grupo) > 1 and grupo[columna_tasa].nunique(dropna=True) > 1:
            media = grupo[columna_tasa].mean()
            conflictos.append({
                "clave": clave_grupo,
                "valores_originales": grupo[columna_tasa].tolist(),
                "tasa_resuelta": media,
            })
            fila_base[columna_tasa] = media
            fila_base["_flag_tasa_divergente"] = True
        else:
            fila_base["_flag_tasa_divergente"] = False
        filas_res.append(fila_base)

    df_res = pd.DataFrame(filas_res)
    return df_res, conflictos


def _buscar_columnas(df, patrones):
    """Busca columnas en un DataFrame que contienen alguno de los patrones dados."""
    encontradas = []
    for col in df.columns:
        col_lower = str(col).lower()
        if any(p in col_lower for p in patrones):
            encontradas.append(col)
    return encontradas


def _cargar_config_silver():
    """Carga el archivo de configuración config.yaml desde la raíz del proyecto."""
    ruta_config = os.path.join(BASE_DIR, "medallon", "config", "config.yaml")
    if os.path.exists(ruta_config):
        with open(ruta_config, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return None


def ejecutar_transformacion_silver():
    """Ejecuta el pipeline completo de transformación y cruce hacia la capa Silver."""
    print("Iniciando transformación a la capa Silver...")
    config = _cargar_config_silver()

    # 1. Leer archivos JSON extraídos de la API en Bronze
    ruta_api = os.path.join(DATA_BRONZE, "api", "*.json")
    archivos_json = sorted(glob.glob(ruta_api))

    if not archivos_json:
        print(f"ERROR: No se encontraron archivos JSON de API en {ruta_api}.")
        return False

    registros_api = []
    for archivo in archivos_json:
        with open(archivo, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                registros_api.extend(data)

    df_api = pd.DataFrame(registros_api)
    df_api.columns = [limpiar_columna(c) for c in df_api.columns]

    # Detectar y estandarizar columnas clave en API
    col_inst = (_buscar_columnas(df_api, ["institucion", "ies", "universidad"]) or [None])[0]
    col_prog = (_buscar_columnas(df_api, ["programa", "carrera"]) or [None])[0]
    col_depto = (_buscar_columnas(df_api, ["departamento"]) or [None])[0]
    col_per = (_buscar_columnas(df_api, ["periodo", "semestre", "anio", "ano"]) or [None])[0]
    col_mat = (_buscar_columnas(df_api, ["matriculados", "matricula", "cantidad", "total"]) or [None])[0]

    renombres_api = {}
    if col_inst:
        renombres_api[col_inst] = "institucion"
    if col_prog:
        renombres_api[col_prog] = "programa"
    if col_depto:
        renombres_api[col_depto] = "departamento"
    if col_per:
        renombres_api[col_per] = "periodo"
    if col_mat:
        renombres_api[col_mat] = "total_matriculas"
    df_api.rename(columns=renombres_api, inplace=True)

    for c in ["institucion", "programa", "departamento", "periodo"]:
        if c in df_api.columns:
            df_api[c] = df_api[c].apply(lambda x: limpiar_dato(x, "texto"))
    if "total_matriculas" in df_api.columns:
        df_api["total_matriculas"] = pd.to_numeric(df_api["total_matriculas"], errors="coerce").fillna(0)

    # Agregar API por llave compuesta para garantizar cardinalidad válida
    llaves_api = [c for c in ["institucion", "programa", "departamento", "periodo"] if c in df_api.columns]
    if llaves_api and "total_matriculas" in df_api.columns:
        df_api = df_api.groupby(llaves_api, as_index=False, dropna=False)["total_matriculas"].sum()

    # 2. Leer hoja departamental de SPADIES (Excel extraído en Bronze)
    ruta_excel_dir = os.path.join(DATA_BRONZE, "excel_extraido")
    ruta_td_depto = os.path.join(ruta_excel_dir, "td_departamento.csv")
    df_integrado = df_api.copy()

    if os.path.exists(ruta_td_depto) and "departamento" in df_api.columns:
        df_depto = pd.read_csv(ruta_td_depto, low_memory=False)
        df_depto.columns = [limpiar_columna(c) for c in df_depto.columns]
        col_d_depto = (_buscar_columnas(df_depto, ["departamento"]) or [None])[0]
        if col_d_depto:
            df_depto.rename(columns={col_d_depto: "departamento"}, inplace=True)
            df_depto["departamento"] = df_depto["departamento"].apply(lambda x: limpiar_dato(x, "texto"))
            df_depto = df_depto[df_depto["departamento"] != ""].copy()

            cols_num = [c for c in df_depto.columns if c != "departamento"]
            for c in cols_num:
                df_depto[c] = pd.to_numeric(df_depto[c].astype(str).str.replace(",", "."), errors="coerce")
            cols_validas = [c for c in cols_num if df_depto[c].notna().sum() > 0]

            if cols_validas:
                ultima_col = cols_validas[-1]
                df_depto_ref = df_depto[["departamento", ultima_col]].rename(
                    columns={ultima_col: "tasa_referencia_departamental"}
                )
                df_depto_ref, _ = _resolver_tasas_divergentes(
                    df_depto_ref, ["departamento"], "tasa_referencia_departamental"
                )
                df_depto_ref = df_depto_ref.drop_duplicates(subset=["departamento"])

                valido, tipo_join, msg = validar_cardinalidad_join(
                    df_api, df_depto_ref, ["departamento"]
                )
                if valido:
                    df_integrado = pd.merge(df_api, df_depto_ref, on="departamento", how="left")
                    ok_filas, _ = consistencia_filas_join(
                        len(df_api), len(df_depto_ref), len(df_integrado), tipo_join
                    )
                    if not ok_filas:
                        print("ADVERTENCIA: Inconsistencia en conteo de filas tras JOIN.")
                else:
                    print(f"ADVERTENCIA cardinalidad: {msg}")

    # 3. Guardar dataset integrado en la ruta definida en config.yaml
    if config and "paths" in config and "silver_dataset_integrado" in config["paths"]:
        ruta_salida = os.path.join(BASE_DIR, config["paths"]["silver_dataset_integrado"])
    else:
        ruta_salida = os.path.join(DATA_SILVER, "silver_dataset_integrado.csv")

    os.makedirs(os.path.dirname(os.path.abspath(ruta_salida)), exist_ok=True)
    df_integrado.to_csv(ruta_salida, index=False, encoding="utf-8")
    print(f"Dataset Silver guardado en: {ruta_salida} ({len(df_integrado)} registros)")
    print("Transformación a la capa Silver completada.")
    return True


if __name__ == "__main__":
    ejecutar_transformacion_silver()