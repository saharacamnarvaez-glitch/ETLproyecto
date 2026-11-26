import os
import json
from pathlib import Path
import pandas as pd
import yaml

try:
    from medallon.src.logger import get_logger
except ImportError:
    from src.logger import get_logger

logger = get_logger("Capa_Gold")

ROOT_DIR = Path(__file__).resolve().parents[3]


def cargar_configuracion():
    ruta_config = ROOT_DIR / "medallon" / "config" / "config.yaml"
    try:
        with open(ruta_config, "r", encoding="utf-8") as archivo:
            return yaml.safe_load(archivo)
    except Exception as e:
        logger.error("Error al leer config.yaml: " + str(e))
        return None


def _detectar_columna(df, patrones):
    for col in df.columns:
        col_lower = str(col).lower()
        if any(p in col_lower for p in patrones):
            return col
    return None


def _limpiar_codigo(val):
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _construir_diccionarios_nombres():
    """
    Construye diccionarios codigo -> nombre real leyendo los JSON crudos de
    Bronze API (campos exactos de Socrata).
    """
    mapa_inst = {}
    mapa_dept = {
        "5": "Antioquia", "8": "Atlántico", "11": "Bogotá, D.C.", "13": "Bolívar",
        "15": "Boyacá", "17": "Caldas", "18": "Caquetá", "19": "Cauca",
        "20": "Cesar", "23": "Córdoba", "25": "Cundinamarca", "27": "Chocó",
        "41": "Huila", "44": "La Guajira", "47": "Magdalena", "50": "Meta",
        "52": "Nariño", "54": "Norte de Santander", "63": "Quindío",
        "66": "Risaralda", "68": "Santander", "70": "Sucre", "73": "Tolima",
        "76": "Valle del Cauca", "81": "Arauca", "85": "Casanare",
        "86": "Putumayo", "88": "San Andrés y Providencia", "91": "Amazonas",
        "94": "Guainía", "95": "Guaviare", "97": "Vaupés", "99": "Vichada",
    }
    mapa_prog = {}

    ruta_api = ROOT_DIR / "data" / "bronze" / "api"
    if ruta_api.exists():
        for archivo_json in sorted(ruta_api.glob("*.json")):
            try:
                registros = json.loads(archivo_json.read_text(encoding="utf-8"))
                for reg in registros:
                    cod_i = _limpiar_codigo(
                        reg.get("c_digo_de_la_instituci_n")
                        or reg.get("codigo_de_la_institucion")
                    )
                    nom_i = (
                        reg.get("instituci_n_de_educaci_n_superior_ies")
                        or reg.get("institucion_de_educacion_superior_ies")
                    )
                    if cod_i and nom_i and not str(nom_i).isdigit():
                        mapa_inst[cod_i] = str(nom_i).strip().title()

                    cod_d = _limpiar_codigo(
                        reg.get("c_digo_del_departamento_ies")
                        or reg.get("codigo_del_departamento_ies")
                    )
                    nom_d = (
                        reg.get("departamento_de_domicilio_de_la_ies")
                        or reg.get("departamento_de_domicilio_de_la_ies")
                    )
                    if cod_d and nom_d and not str(nom_d).isdigit():
                        mapa_dept[cod_d] = str(nom_d).strip().title()

                    cod_p = _limpiar_codigo(
                        reg.get("c_digo_snies_delprograma")
                        or reg.get("codigo_snies_del_programa")
                    )
                    nom_p = (
                        reg.get("programa_acad_mico")
                        or reg.get("programa_academico")
                    )
                    if cod_p and nom_p and not str(nom_p).isdigit():
                        mapa_prog[cod_p] = str(nom_p).strip().title()
            except Exception:
                continue

    return mapa_inst, mapa_dept, mapa_prog


def _generar_gold_referencia_departamental(mapa_dept):
    """
    Construye una segunda tabla Gold separada exclusivamente a nivel departamento
    (granularidad_riesgo = 'departamento') usando los datos oficiales de SPADIES.
    """
    candidatos = [
        ROOT_DIR / "data" / "silver" / "silver_td_departamento.csv",
        ROOT_DIR / "data" / "bronze" / "excel_extraido" / "td_departamento.csv",
    ]
    ruta_fuente = next((p for p in candidatos if p.exists()), None)
    if not ruta_fuente:
        logger.warning("No se encontro archivo de TD - departamento para referencia regional.")
        return False

    try:
        df_raw = pd.read_csv(ruta_fuente, header=None, low_memory=False)
        fila_header = None
        for idx, row in df_raw.head(15).iterrows():
            texto_fila = " ".join(str(v).lower() for v in row.values if pd.notna(v))
            if "departamento" in texto_fila and any(str(y) in texto_fila for y in range(2010, 2026)):
                fila_header = idx
                break

        if fila_header is not None:
            df_dept = pd.read_csv(ruta_fuente, skiprows=fila_header, low_memory=False)
        else:
            df_dept = pd.read_csv(ruta_fuente, low_memory=False)

        col_dept = _detectar_columna(df_dept, ["departamento"])
        if not col_dept:
            return False

        df_dept = df_dept.dropna(subset=[col_dept]).copy()
        df_dept[col_dept] = df_dept[col_dept].astype(str).str.strip()
        df_dept = df_dept[
            ~df_dept[col_dept].str.lower().isin(["nan", "none", "", "total", "total nacional", "fuente"])
            & ~df_dept[col_dept].str.lower().str.startswith(("fuente", "nota", "elaborado"))
        ]

        cols_anios = [c for c in df_dept.columns if any(str(y) in str(c) for y in range(2015, 2026))]
        if not cols_anios:
            return False

        ultimo_anio = sorted(cols_anios)[-1]
        df_ref = pd.DataFrame()
        df_ref["departamento"] = df_dept[col_dept].apply(
            lambda x: mapa_dept.get(_limpiar_codigo(x), str(x).strip().title())
        )
        df_ref["periodo_referencia"] = str(ultimo_anio).strip()
        df_ref["tasa_desercion_departamental"] = (
            df_dept[ultimo_anio]
            .astype(str)
            .str.replace("%", "", regex=False)
            .str.replace(",", ".", regex=False)
            .str.strip()
        )
        df_ref["tasa_desercion_departamental"] = pd.to_numeric(
            df_ref["tasa_desercion_departamental"], errors="coerce"
        )
        mask_pct = df_ref["tasa_desercion_departamental"] > 1
        df_ref.loc[mask_pct, "tasa_desercion_departamental"] = (
            df_ref.loc[mask_pct, "tasa_desercion_departamental"] / 100.0
        )

        df_ref = df_ref.dropna(subset=["tasa_desercion_departamental"]).drop_duplicates(subset=["departamento"])
        df_ref["fuente_tasa"] = "SPADIES_MEN"
        df_ref["granularidad_riesgo"] = "departamento"

        ruta_salida_ref = ROOT_DIR / "data" / "gold" / "gold_referencia_departamental.csv"
        df_ref.to_csv(ruta_salida_ref, index=False, encoding="utf-8-sig")
        logger.info(
            f"Tabla Gold de referencia departamental exportada en: {ruta_salida_ref} "
            f"({len(df_ref)} departamentos)"
        )
        return True
    except Exception as e:
        logger.warning(f"No se pudo generar gold_referencia_departamental.csv: {e}")
        return False


def ejecutar_transformacion_gold():
    logger.info("Iniciando transformacion de la Capa Gold...")
    config = cargar_configuracion()
    if not config:
        return False

    ruta_silver = str(ROOT_DIR / config["paths"]["silver_dataset_integrado"])
    ruta_gold_final = str(ROOT_DIR / config["paths"]["gold_final"])

    if not os.path.exists(ruta_silver):
        logger.error(f"No se encontro el dataset integrado de Silver en: {ruta_silver}")
        return False

    logger.info("Leyendo dataset integrado de Silver...")
    df_integrado = pd.read_csv(ruta_silver, low_memory=False)

    col_institucion = _detectar_columna(df_integrado, ["institucion", "universidad"])
    col_departamento = _detectar_columna(df_integrado, ["departamento"])
    col_programa = _detectar_columna(df_integrado, ["programa", "carrera"])
    col_matriculados = _detectar_columna(df_integrado, ["matriculados", "matricula", "total_matriculas"])
    col_tasa = _detectar_columna(df_integrado, ["desercion", "tasa", "abandono"])

    columnas_clave = [c for c in [col_institucion, col_departamento, col_programa, col_matriculados, col_tasa] if c]

    if not columnas_clave:
        logger.error("No se encontraron columnas clave para construir la tabla Gold.")
        return False

    df_gold = df_integrado[columnas_clave].copy()

    renombres = {}
    if col_institucion:
        renombres[col_institucion] = "institucion"
    if col_departamento:
        renombres[col_departamento] = "departamento"
    if col_programa:
        renombres[col_programa] = "programa"
    if col_matriculados:
        renombres[col_matriculados] = "total_matriculas"
    if col_tasa:
        renombres[col_tasa] = "tasa_desercion_2021"
    df_gold.rename(columns=renombres, inplace=True)

    # Enriquecimiento de nombres textuales reales (conservando códigos originales)
    mapa_inst, mapa_dept, mapa_prog = _construir_diccionarios_nombres()

    if "institucion" in df_gold.columns:
        df_gold["codigo_institucion"] = df_gold["institucion"].apply(_limpiar_codigo)
        df_gold["institucion"] = df_gold["codigo_institucion"].apply(
            lambda c: mapa_inst.get(c, f"IES Código {c}" if c.isdigit() else c)
        )

    if "departamento" in df_gold.columns:
        df_gold["codigo_departamento"] = df_gold["departamento"].apply(_limpiar_codigo)
        df_gold["departamento"] = df_gold["codigo_departamento"].apply(
            lambda c: mapa_dept.get(c, f"Depto Código {c}" if c.isdigit() else c)
        )

    if "programa" in df_gold.columns:
        df_gold["codigo_programa"] = df_gold["programa"].apply(_limpiar_codigo)
        df_gold["programa"] = df_gold["codigo_programa"].apply(
            lambda c: mapa_prog.get(c, f"Programa SNIES {c}" if c.isdigit() else c)
        )

    if "tasa_desercion_2021" in df_gold.columns:
        df_gold["tasa_desercion_2021"] = pd.to_numeric(df_gold["tasa_desercion_2021"], errors="coerce")

    # Consolidar por llave compuesta final (institucion, departamento, programa)
    # para garantizar unicidad 1:1 en Gold y en el Data Warehouse
    claves_gold = [c for c in ["institucion", "departamento", "programa"] if c in df_gold.columns]
    if claves_gold:
        agg_dict = {}
        if "total_matriculas" in df_gold.columns:
            df_gold["total_matriculas"] = pd.to_numeric(df_gold["total_matriculas"], errors="coerce").fillna(0)
            agg_dict["total_matriculas"] = "sum"
        for col_cod in ["codigo_institucion", "codigo_departamento", "codigo_programa"]:
            if col_cod in df_gold.columns:
                agg_dict[col_cod] = "first"
        if "tasa_desercion_2021" in df_gold.columns:
            agg_dict["tasa_desercion_2021"] = "mean"

        df_gold = df_gold.groupby(claves_gold, as_index=False, dropna=False).agg(agg_dict)

    # Fase 4: Clasificacion de riesgo por granularidad correcta
    df_gold["fuente_tasa"] = "propia_entidad"
    df_gold["es_tasa_referencia_departamental"] = False
    df_gold["granularidad_riesgo"] = "entidad"

    if "tasa_desercion_2021" in df_gold.columns:
        logger.info("Calculando indicador de nivel de riesgo por entidad academica (tasa propia)...")
        tasas_validas = df_gold["tasa_desercion_2021"].dropna()
        if len(tasas_validas) > 0:
            promedio_nacional = tasas_validas.mean()
            desviacion_estandar = tasas_validas.std()

            def clasificar_riesgo(x):
                if pd.isna(x):
                    return "Sin Datos"
                if x > promedio_nacional + desviacion_estandar:
                    return "Riesgo Alto"
                elif x < promedio_nacional - desviacion_estandar:
                    return "Riesgo Bajo"
                else:
                    return "Riesgo Medio"

            df_gold["nivel_riesgo"] = df_gold["tasa_desercion_2021"].apply(clasificar_riesgo)
            df_gold["desviacion_promedio_nacional_pct"] = (
                (df_gold["tasa_desercion_2021"] - promedio_nacional) / promedio_nacional * 100
            ).round(2)
        else:
            df_gold["nivel_riesgo"] = "Sin Datos"
    else:
        df_gold["nivel_riesgo"] = "Sin Datos"

    os.makedirs(os.path.dirname(ruta_gold_final), exist_ok=True)
    df_gold.to_csv(ruta_gold_final, index=False, encoding="utf-8-sig")
    logger.info(f"Dataset final Gold exportado exitosamente a: {ruta_gold_final} ({len(df_gold)} registros)")

    # Generar también la tabla Gold de referencia departamental (granularidad separada)
    _generar_gold_referencia_departamental(mapa_dept)

    return True


if __name__ == "__main__":
    ejecutar_transformacion_gold()