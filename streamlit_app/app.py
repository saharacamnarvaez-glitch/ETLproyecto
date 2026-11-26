import glob
import os
import json
import sqlite3
import unicodedata
import urllib.request
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ==============================================================================
# 1. CONFIGURACION GENERAL DE LA APLICACION (SIN EMOJIS)
# ==============================================================================
st.set_page_config(
    page_title="Plataforma Analitica | Desercion en Educacion Superior",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .stApp {
            background-color: #F4F6F9;
            color: #1E293B;
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }
        .exec-banner {
            background: linear-gradient(135deg, #0B1F3A 0%, #163A63 60%, #1E4E8C 100%);
            padding: 1.75rem 2.25rem;
            border-radius: 10px;
            border-left: 6px solid #0D9488;
            color: #FFFFFF;
            margin-bottom: 1.5rem;
            box-shadow: 0 6px 18px rgba(11, 31, 58, 0.14);
        }
        .exec-banner .kicker {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 1.6px;
            color: #5EEAD4;
            font-weight: 700;
            margin-bottom: 0.35rem;
        }
        .exec-banner h1 {
            color: #FFFFFF;
            font-size: 1.85rem;
            font-weight: 700;
            margin: 0 0 0.45rem 0;
            line-height: 1.2;
        }
        .exec-banner p {
            color: #CBD5E1;
            font-size: 0.98rem;
            margin: 0;
            max-width: 940px;
        }
        div[data-testid="metric-container"] {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-top: 4px solid #1E4E8C;
            padding: 1.1rem 1.25rem;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
        }
        div[data-testid="metric-container"] label {
            color: #475569 !important;
            font-weight: 600 !important;
            font-size: 0.82rem !important;
            text-transform: uppercase;
            letter-spacing: 0.4px;
        }
        div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
            color: #0B1F3A !important;
            font-weight: 700 !important;
            font-size: 1.6rem !important;
        }
        .decision-brief {
            background-color: #FFFFFF;
            border: 1px solid #CBD5E1;
            border-left: 5px solid #0B1F3A;
            padding: 1.15rem 1.4rem;
            border-radius: 8px;
            margin: 0.5rem 0 1.5rem 0;
            box-shadow: 0 2px 6px rgba(15, 23, 42, 0.03);
        }
        .decision-brief .title {
            font-size: 0.82rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: #1E4E8C;
            margin-bottom: 0.35rem;
        }
        .decision-brief .body {
            font-size: 0.96rem;
            color: #1E293B;
            line-height: 1.55;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #E2E8F0;
            padding: 6px;
            border-radius: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 42px;
            background-color: transparent;
            border-radius: 6px;
            color: #334155;
            font-weight: 600;
            padding: 0 16px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #0B1F3A !important;
            color: #FFFFFF !important;
        }
        section[data-testid="stSidebar"] {
            background-color: #FFFFFF;
            border-right: 1px solid #E2E8F0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# 2. CATALOGOS OFICIALES Y ENRIQUECIMIENTO DESDE WAREHOUSE / BRONZE / SILVER
# ==============================================================================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(BASE_DIR, "data", "warehouse", "etl_warehouse.db")
CSV_GOLD_PATH = os.path.join(BASE_DIR, "data", "gold", "gold_final.csv")
CSV_GOLD_DEPT_PATH = os.path.join(BASE_DIR, "data", "gold", "gold_referencia_departamental.csv")
API_GOLD_URL = os.getenv("API_GOLD_URL", "http://127.0.0.1:8000/gold")

PALETA_RIESGO = {
    "Riesgo Alto": "#B91C1C",
    "Riesgo Medio": "#D97706",
    "Riesgo Bajo": "#0D9488",
    "Sin Datos": "#64748B",
}

PALETA_AZULES = ["#0B1F3A", "#163A63", "#1E4E8C", "#2B6CB0", "#4299E1", "#0D9488"]

CODIGOS_DANE_DEPTO = {
    "5": "Antioquia", "05": "Antioquia",
    "8": "Atlantico", "08": "Atlantico",
    "11": "Bogota D.C.",
    "13": "Bolivar",
    "15": "Boyaca",
    "17": "Caldas",
    "18": "Caqueta",
    "19": "Cauca",
    "20": "Cesar",
    "23": "Cordoba",
    "25": "Cundinamarca",
    "27": "Choco",
    "41": "Huila",
    "44": "La Guajira",
    "47": "Magdalena",
    "50": "Meta",
    "52": "Narino",
    "54": "Norte De Santander",
    "63": "Quindio",
    "66": "Risaralda",
    "68": "Santander",
    "70": "Sucre",
    "73": "Tolima",
    "76": "Valle Del Cauca",
    "81": "Arauca",
    "85": "Casanare",
    "86": "Putumayo",
    "88": "San Andres Y Providencia",
    "91": "Amazonas",
    "94": "Guainia",
    "95": "Guaviare",
    "97": "Vaupes",
    "99": "Vichada",
}

CODIGOS_SNIES_IES_PRINCIPALES = {
    "1101": "Universidad Nacional De Colombia",
    "1102": "Universidad Nacional De Colombia (Medellin)",
    "1103": "Universidad Nacional De Colombia (Manizales)",
    "1104": "Universidad Nacional De Colombia (Palmira)",
    "1105": "Universidad Pedagogica Y Tecnologica De Colombia - Uptc",
    "1110": "Universidad Del Cauca",
    "1111": "Universidad Tecnologica De Pereira - Utp",
    "1112": "Universidad De Caldas",
    "1113": "Universidad Pedagogica Nacional",
    "1114": "Universidad Distrital Francisco Jose De Caldas",
    "1115": "Universidad Del Quindio",
    "1117": "Universidad Militar Nueva Granada",
    "1118": "Universidad Surcolombiana",
    "1119": "Universidad De La Amazonia",
    "1120": "Universidad De Los Llanos",
    "1121": "Universidad Tecnologica Del Choco",
    "1122": "Universidad Popular Del Cesar",
    "1201": "Universidad De Antioquia",
    "1202": "Universidad Del Atlantico",
    "1203": "Universidad Del Valle",
    "1204": "Universidad Industrial De Santander - Uis",
    "1205": "Universidad De Cartagena",
    "1206": "Universidad De Narino",
    "1207": "Universidad Del Tolima",
    "1208": "Universidad De Cordoba",
    "1209": "Universidad Francisco De Paula Santander",
    "1210": "Universidad De Pamplona",
    "1212": "Universidad Del Magdalena",
    "1213": "Universidad De Sucre",
    "1301": "Escuela Superior De Administracion Publica - Esap",
    "1701": "Pontificia Universidad Javeriana",
    "1702": "Pontificia Universidad Javeriana (Cali)",
    "1703": "Universidad Incca De Colombia",
    "1704": "Universidad Santo Tomas",
    "1706": "Universidad Externado De Colombia",
    "1707": "Fundacion Universidad De Bogota Jorge Tadeo Lozano",
    "1709": "Universidad Central",
    "1710": "Universidad Pontificia Bolivariana",
    "1712": "Universidad De La Sabana",
    "1713": "Universidad Eafit",
    "1714": "Universidad Del Norte",
    "1715": "Colegio Mayor De Nuestra Senora Del Rosario",
    "1718": "Universidad De San Buenaventura",
    "1722": "Universidad De La Salle",
    "1725": "Universidad Libre",
    "1727": "Universidad Cooperativa De Colombia",
    "1728": "Universidad Autonoma De Bucaramanga - Unab",
    "1732": "Universidad Tecnologica De Bolivar",
    "1803": "Universidad Santiago De Cali",
    "1804": "Universidad De Medellin",
    "1805": "Universidad Simon Bolivar",
    "1813": "Universidad De Los Andes",
    "1814": "Universidad Icesi",
    "1815": "Universidad Ean",
    "1818": "Universidad Autonoma De Occidente",
    "1820": "Universidad Antonio Narino",
    "1823": "Universidad El Bosque",
    "1824": "Universidad Sergio Arboleda",
    "1826": "Universidad Catolica De Colombia",
    "1828": "Universidad Manizales",
    "1833": "Universidad De Santander - Udes",
    "2102": "Universidad Nacional Abierta Y A Distancia - Unad",
    "2104": "Instituto Tecnologico Metropolitano - Itm",
    "2106": "Politecnico Colombiano Jaime Isaza Cadavid",
    "2110": "Unidades Tecnologicas De Santander - Uts",
    "2114": "Institucion Universitaria Pascual Bravo",
    "2701": "Corporacion Universitaria Minuto De Dios - Uniminuto",
    "2704": "Fundacion Universitaria Del Area Andina",
    "2710": "Politecnico Grancolombiano",
    "2711": "Corporacion Unificada Nacional De Educacion Superior - Cun",
    "2715": "Fundacion Universitaria Los Libertadores",
    "2723": "Corporacion Universitaria Iberoamericana",
    "2725": "Corporacion Universitaria Remington",
    "2811": "Fundacion Universitaria San Martin",
    "2812": "Universidad Ecci",
    "2829": "Corporacion Universitaria Americana",
    "2832": "Fundacion Universitaria Compensar",
    "2849": "Fundacion Universitaria Catolica Lumen Gentium",
    "3102": "Institucion Universitaria Antonio Jose Camacho",
    "3103": "Escuela Nacional Del Deporte",
    "3104": "Instituto Departamental De Bellas Artes",
    "3107": "Instituto Tecnico Central",
    "3114": "Instituto Tecnologico Del Putumayo",
    "3115": "Instituto Tolimense De Formacion Tecnica Profesional - Itfip",
    "3117": "Institucion Universitaria Colegio Mayor De Antioquia",
    "3204": "Unidad Central Del Valle Del Cauca - Uceva",
    "3301": "Colegio Mayor De Bolivar",
    "3702": "Fundacion Universitaria Konrad Lorenz",
    "3808": "Corporacion Universitaria Comfacauca - Unicomfacauca",
    "3817": "Fundacion Universitaria De Popayan",
    "4102": "Instituto Nacional De Formacion Tecnica Profesional - Infotep",
    "4814": "Corporacion Universitaria Autonoma Del Cauca",
    "9110": "Servicio Nacional De Aprendizaje - Sena",
}


def _normalizar_busqueda(texto):
    if not isinstance(texto, str):
        texto = str(texto)
    nfkd = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return sin_tildes.lower().strip()


def _limpiar_codigo(val):
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s.strip()


def _encontrar_columna(df, exactos, parciales):
    cols_lower = {c.lower().strip(): c for c in df.columns}
    for cand in exactos:
        if cand in cols_lower:
            return cols_lower[cand]
    for col_l, col_orig in cols_lower.items():
        if any(p in col_l for p in parciales):
            return col_orig
    return None


@st.cache_data(ttl=600)
def construir_diccionarios_nombres():
    """Extrae y combina diccionarios codigo->nombre de IES, Programas y Tasas."""
    mapa_ies = dict(CODIGOS_SNIES_IES_PRINCIPALES)
    mapa_prog = {}
    mapa_tasa_depto = {}

    # 1. Leer tasas departamentales oficiales desde SQLite o gold_referencia_departamental.csv
    df_dep_oficial = pd.DataFrame()
    if os.path.exists(DB_PATH):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                df_dep_oficial = pd.read_sql_query("SELECT * FROM gold_referencia_departamental", conn)
        except Exception:
            pass
    if df_dep_oficial.empty and os.path.exists(CSV_GOLD_DEPT_PATH):
        try:
            df_dep_oficial = pd.read_csv(CSV_GOLD_DEPT_PATH, low_memory=False)
        except Exception:
            pass

    if not df_dep_oficial.empty and "departamento" in df_dep_oficial.columns and "tasa_desercion_departamental" in df_dep_oficial.columns:
        for _, row in df_dep_oficial.dropna(subset=["departamento", "tasa_desercion_departamental"]).iterrows():
            dep_norm = _normalizar_busqueda(str(row["departamento"]))
            val = float(row["tasa_desercion_departamental"])
            mapa_tasa_depto[dep_norm] = round(val * 100.0 if val <= 1.0 else val, 2)

    # 2. Enriquecer nombres desde Bronze API JSON si están disponibles
    rutas_bronze_json = sorted(glob.glob(os.path.join(BASE_DIR, "data", "bronze", "api", "*.json")))
    for ruta_j in rutas_bronze_json[:3]:
        try:
            with open(ruta_j, "r", encoding="utf-8") as f:
                data_j = json.load(f)
            if isinstance(data_j, list):
                for reg in data_j:
                    cod_i = _limpiar_codigo(reg.get("c_digo_de_la_instituci_n") or reg.get("codigo_de_la_institucion"))
                    nom_i = reg.get("instituci_n_de_educaci_n_superior_ies") or reg.get("institucion_de_educacion_superior_ies")
                    if cod_i and nom_i and not str(nom_i).isdigit():
                        mapa_ies[cod_i] = str(nom_i).strip().title()

                    cod_p = _limpiar_codigo(reg.get("c_digo_snies_delprograma") or reg.get("codigo_snies_del_programa"))
                    nom_p = reg.get("programa_acad_mico") or reg.get("programa_academico")
                    if cod_p and nom_p and not str(nom_p).isdigit():
                        mapa_prog[cod_p] = str(nom_p).strip().title()
        except Exception:
            continue

    return mapa_ies, mapa_prog, mapa_tasa_depto


@st.cache_data(ttl=120)
def cargar_datos_warehouse(modo_fuente="Automatico (SQLite / CSV)"):
    """Consulta gold_final y traduce todos los codigos a nombres reales legibles."""
    df = pd.DataFrame()
    origen = "Sin conexion"

    if modo_fuente == "API REST FastAPI (localhost:8000)":
        try:
            with urllib.request.urlopen(API_GOLD_URL, timeout=4) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                if isinstance(payload, list):
                    df = pd.DataFrame(payload)
                elif isinstance(payload, dict):
                    for key in ["data", "records", "gold", "items", "results"]:
                        if key in payload and isinstance(payload[key], list):
                            df = pd.DataFrame(payload[key])
                            break
                if not df.empty:
                    origen = "FastAPI Endpoint (/gold)"
        except Exception:
            df = pd.DataFrame()

    if df.empty and os.path.exists(DB_PATH):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                tablas = pd.read_sql_query(
                    "SELECT name FROM sqlite_master WHERE type='table'", conn
                )["name"].tolist()
                tabla_obj = "gold_final" if "gold_final" in tablas else (tablas[0] if tablas else None)
                if tabla_obj:
                    df = pd.read_sql_query(f"SELECT * FROM {tabla_obj}", conn)
                    origen = f"Data Warehouse SQLite (tabla: {tabla_obj})"
        except Exception:
            df = pd.DataFrame()

    if df.empty and os.path.exists(CSV_GOLD_PATH):
        df = pd.read_csv(CSV_GOLD_PATH, low_memory=False)
        origen = f"Capa Gold CSV ({os.path.basename(CSV_GOLD_PATH)})"

    if df.empty:
        return df, origen

    mapa_ies, mapa_prog, mapa_tasa_depto = construir_diccionarios_nombres()

    col_inst = _encontrar_columna(
        df,
        ["nombre_institucion", "institucion", "ies", "cod_institucion"],
        ["institucion", "universidad", "ies"],
    )
    col_depto = _encontrar_columna(
        df,
        ["nombre_departamento", "departamento_oferta", "departamento", "depto", "cod_departamento"],
        ["departamento", "depto"],
    )
    col_prog = _encontrar_columna(
        df,
        ["nombre_programa", "programa_academico", "programa", "codigo_programa", "snies_programa"],
        ["programa", "carrera"],
    )
    col_mat = _encontrar_columna(
        df,
        ["total_matriculas", "matriculados", "matricula"],
        ["matricul", "total"],
    )
    col_tasa = _encontrar_columna(
        df,
        ["tasa_desercion_2021", "tasa_desercion", "tasa_propia"],
        ["tasa_desercion", "desercion"],
    )
    col_riesgo = _encontrar_columna(
        df,
        ["nivel_riesgo", "riesgo"],
        ["nivel_riesgo", "riesgo"],
    )

    def _traducir_inst(val):
        s = _limpiar_codigo(val)
        if not s or s.lower() == "nan":
            return "No especificado"
        if s in mapa_ies:
            return mapa_ies[s]
        if s.isdigit():
            return f"Institucion SNIES {s}"
        return s.title()

    def _traducir_depto(val):
        s = _limpiar_codigo(val)
        if s in CODIGOS_DANE_DEPTO:
            return CODIGOS_DANE_DEPTO[s]
        if s.zfill(2) in CODIGOS_DANE_DEPTO:
            return CODIGOS_DANE_DEPTO[s.zfill(2)]
        return s.title() if s and s.lower() != "nan" else "No especificado"

    def _traducir_prog(val):
        s = _limpiar_codigo(val)
        if not s or s.lower() == "nan":
            return "No especificado"
        if s in mapa_prog:
            return mapa_prog[s]
        if s.isdigit():
            return f"Programa SNIES {s}"
        return s.title()

    df_norm = pd.DataFrame()
    df_norm["institucion"] = df[col_inst].apply(_traducir_inst) if col_inst else "No especificado"
    df_norm["departamento"] = df[col_depto].apply(_traducir_depto) if col_depto else "No especificado"
    df_norm["programa"] = df[col_prog].apply(_traducir_prog) if col_prog else "No especificado"
    df_norm["total_matriculas"] = (
        pd.to_numeric(df[col_mat], errors="coerce").fillna(0) if col_mat else 0
    )

    df_norm["tasa_desercion_2021"] = (
        pd.to_numeric(df[col_tasa], errors="coerce") if col_tasa else np.nan
    )
    df_norm["tasa_ref_departamental"] = df_norm["departamento"].apply(
        lambda d: mapa_tasa_depto.get(_normalizar_busqueda(d), np.nan)
    )

    df_norm["nivel_riesgo"] = (
        df[col_riesgo].fillna("Sin Datos").astype(str).str.strip()
        if col_riesgo
        else "Sin Datos"
    )

    df_norm["_indice_busqueda"] = (
        df_norm["institucion"] + " " + df_norm["programa"] + " " + df_norm["departamento"]
    ).apply(_normalizar_busqueda)

    df_norm["segmento_matricula"] = pd.cut(
        df_norm["total_matriculas"],
        bins=[-1, 50, 250, 1000, float("inf")],
        labels=[
            "Micro (0 - 50)",
            "Pequena (51 - 250)",
            "Mediana (251 - 1,000)",
            "Masiva (> 1,000)",
        ],
    ).astype(str)

    return df_norm, origen


# ==============================================================================
# 3. ENCABEZADO EJECUTIVO
# ==============================================================================
st.markdown(
    """
    <div class="exec-banner">
        <div class="kicker">Analitica Estrategica de Educacion Superior | Inteligencia Institucional</div>
        <h1>Tablero de Control: Cobertura y Permanencia en Educacion Superior</h1>
        <p>Plataforma gerencial para evaluar concentracion territorial, demanda academica, benchmarking institucional y proyeccion de impacto en retencion estudiantil en Colombia.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# 4. BARRA LATERAL DE CONTROL Y BUSQUEDA INTERACTIVA
# ==============================================================================
with st.sidebar:
    st.subheader("Fuente y Buscador Global")

    modo_conexion = st.selectbox(
        "Origen de datos",
        options=["Automatico (SQLite / CSV)", "API REST FastAPI (localhost:8000)"],
        index=0,
    )

    df_raw, fuente_datos = cargar_datos_warehouse(modo_conexion)

    if df_raw.empty:
        st.error("No se encontraron datos disponibles en SQLite, CSV ni API.")
        st.stop()

    busqueda_global = st.text_input(
        "Busqueda rapida por palabra clave",
        placeholder="Ej. Valle, Bogota, Ingenieria, Unad...",
        help="Busca simultaneamente en institucion, programa y departamento (ignora tildes y mayusculas).",
    ).strip()

    if st.button("Recargar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.subheader("Filtros Segmentados")

    deptos_opciones = sorted(df_raw["departamento"].unique().tolist())
    deptos_sel = st.multiselect(
        "Departamento",
        options=deptos_opciones,
        default=[],
        placeholder="Todos los departamentos",
    )
    df_f1 = df_raw[df_raw["departamento"].isin(deptos_sel)] if deptos_sel else df_raw

    inst_opciones = sorted(df_f1["institucion"].unique().tolist())
    inst_sel = st.multiselect(
        "Institucion de Educacion Superior",
        options=inst_opciones,
        default=[],
        placeholder="Todas las instituciones",
    )
    df_f2 = df_f1[df_f1["institucion"].isin(inst_sel)] if inst_sel else df_f1

    prog_opciones = sorted(df_f2["programa"].unique().tolist())
    prog_sel = st.multiselect(
        "Programa Academico",
        options=prog_opciones,
        default=[],
        placeholder="Todos los programas",
    )
    df_f3 = df_f2[df_f2["programa"].isin(prog_sel)] if prog_sel else df_f2

    riesgos_opciones = sorted(df_f3["nivel_riesgo"].unique().tolist())
    riesgos_sel = st.multiselect(
        "Nivel de Riesgo",
        options=riesgos_opciones,
        default=[],
        placeholder="Todos los niveles",
    )
    df_f4 = df_f3[df_f3["nivel_riesgo"].isin(riesgos_sel)] if riesgos_sel else df_f3

    max_mat_val = int(df_raw["total_matriculas"].max()) if len(df_raw) > 0 else 1000
    tope_slider = max(100, min(max_mat_val, 5000))
    min_mat_sel = st.slider(
        "Matricula minima por registro",
        min_value=0,
        max_value=tope_slider,
        value=0,
        step=25,
    )
    df_filtrado = df_f4[df_f4["total_matriculas"] >= min_mat_sel].copy()

    if busqueda_global:
        termino = _normalizar_busqueda(busqueda_global)
        df_filtrado = df_filtrado[
            df_filtrado["_indice_busqueda"].str.contains(termino, regex=False, na=False)
        ].copy()

    st.divider()
    st.caption(f"Conexion activa: {fuente_datos}")
    st.caption(f"Registros en vista: {len(df_filtrado):,} de {len(df_raw):,}")

if df_filtrado.empty:
    st.warning("No existen registros para la combinacion de filtros actual. Modifique los criterios en el panel izquierdo.")
    st.stop()

# ==============================================================================
# 5. INDICADORES CLAVE DE DESEMPENO (KPIs) Y SINTESIS EJECUTIVA
# ==============================================================================
total_estudiantes = int(df_filtrado["total_matriculas"].sum())
total_base = df_raw["total_matriculas"].sum()
pct_estudiantes = (total_estudiantes / total_base * 100) if total_base > 0 else 0

total_instituciones = df_filtrado["institucion"].nunique()
total_programas = df_filtrado["programa"].nunique()
total_deptos = df_filtrado["departamento"].nunique()

tasas_propias = df_filtrado["tasa_desercion_2021"].dropna()
tasas_ref_dep = df_filtrado["tasa_ref_departamental"].dropna()

if len(tasas_propias) > 0:
    valor_tasa = f"{tasas_propias.mean():.2f}%"
    sub_tasa = f"Tasa propia ({len(tasas_propias):,} reg.)"
elif len(tasas_ref_dep) > 0:
    valor_tasa = f"{tasas_ref_dep.mean():.2f}%"
    sub_tasa = "Referencia regional SPADIES"
else:
    valor_tasa = "Sin reporte"
    sub_tasa = "Sin imputacion departamental"

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric(
    label="Matricula Total",
    value=f"{total_estudiantes:,}",
    delta=f"{pct_estudiantes:.1f}% del universo total",
    delta_color="off",
)
k2.metric(
    label="Instituciones (IES)",
    value=f"{total_instituciones:,}",
    delta=f"{int(total_estudiantes / max(1, total_instituciones)):,} est. / IES",
    delta_color="off",
)
k3.metric(
    label="Programas Activos",
    value=f"{total_programas:,}",
    delta=f"{int(total_estudiantes / max(1, total_programas)):,} est. / programa",
    delta_color="off",
)
k4.metric(
    label="Cobertura Territorial",
    value=f"{total_deptos} deptos",
    delta=f"{len(df_filtrado):,} registros activos",
    delta_color="off",
)
k5.metric(
    label="Tasa Referencia Desercion",
    value=valor_tasa,
    delta=sub_tasa,
    delta_color="off",
)

agg_depto = df_filtrado.groupby("departamento")["total_matriculas"].sum().sort_values(ascending=False)
lider_depto = agg_depto.index[0]
part_depto = (agg_depto.iloc[0] / total_estudiantes * 100) if total_estudiantes > 0 else 0

agg_inst = df_filtrado.groupby("institucion")["total_matriculas"].sum().sort_values(ascending=False)
lider_inst = agg_inst.index[0]
part_inst = (agg_inst.iloc[0] / total_estudiantes * 100) if total_estudiantes > 0 else 0

agg_prog = df_filtrado.groupby("programa")["total_matriculas"].sum().sort_values(ascending=False)
lider_prog = agg_prog.index[0]

st.markdown(
    f"""
    <div class="decision-brief">
        <div class="title">Diagnostico Ejecutivo de la Seleccion Actual</div>
        <div class="body">
            La consulta actual abarca <strong>{total_estudiantes:,} estudiantes</strong> ({pct_estudiantes:.1f}% del total consolidado)
            distribuidos en <strong>{total_instituciones:,} instituciones</strong> y <strong>{total_programas:,} programas academicos</strong>.
            Territorialmente, <strong>{lider_depto}</strong> concentra el <strong>{part_depto:.1f}%</strong> de la matricula filtrada,
            mientras que <strong>{lider_inst}</strong> lidera la participacion institucional con el <strong>{part_inst:.1f}%</strong>.
            El programa con mayor volumen estudiantil en este segmento es <strong>{lider_prog}</strong>.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# 6. PESTANAS FUNCIONALES PARA TOMA DE DECISIONES
# ==============================================================================
tab_regional, tab_institucional, tab_comparador, tab_simulador, tab_explorador = st.tabs(
    [
        "1. Cobertura Regional y Pareto",
        "2. Ranking Institucional y Programas",
        "3. Comparador de Instituciones",
        "4. Simulador de Retencion Estudiantil",
        "5. Buscador Granular y Exportacion",
    ]
)

with tab_regional:
    col_r1, col_r2 = st.columns([3, 2])

    with col_r1:
        st.subheader("Distribucion Departamental de la Matricula")
        df_dep = (
            df_filtrado.groupby("departamento", as_index=False)
            .agg(
                matricula=("total_matriculas", "sum"),
                instituciones=("institucion", "nunique"),
                programas=("programa", "nunique"),
            )
            .sort_values("matricula", ascending=False)
        )
        max_dep_slider = max(6, min(33, len(df_dep)))
        val_dep_slider = min(15, len(df_dep))
        if len(df_dep) > 5:
            top_n_dep = st.slider(
                "Numero de departamentos en grafico",
                min_value=5,
                max_value=max_dep_slider,
                value=val_dep_slider,
                key="slider_dep",
            )
        else:
            top_n_dep = len(df_dep)

        df_dep_top = df_dep.head(top_n_dep).sort_values("matricula", ascending=True)

        fig_dep = px.bar(
            df_dep_top,
            x="matricula",
            y="departamento",
            orientation="h",
            text_auto=".2s",
            color="matricula",
            color_continuous_scale=["#64748B", "#1E4E8C", "#0B1F3A"],
            hover_data={"instituciones": True, "programas": True, "matricula": ":,"},
            labels={
                "matricula": "Estudiantes Matriculados",
                "departamento": "Departamento",
                "instituciones": "IES",
                "programas": "Programas",
            },
        )
        fig_dep.update_layout(
            height=460,
            coloraxis_showscale=False,
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            margin=dict(l=10, r=25, t=15, b=20),
            xaxis=dict(gridcolor="#E2E8F0"),
        )
        st.plotly_chart(fig_dep, use_container_width=True)

    with col_r2:
        st.subheader("Curva de Concentracion Territorial (Pareto)")
        df_pareto = df_dep.head(12).copy()
        df_pareto["acumulado_pct"] = (
            df_pareto["matricula"].cumsum() / max(1, df_dep["matricula"].sum()) * 100
        ).round(1)

        fig_pareto = go.Figure()
        fig_pareto.add_trace(
            go.Bar(
                x=df_pareto["departamento"],
                y=df_pareto["matricula"],
                name="Matricula",
                marker_color="#1E4E8C",
            )
        )
        fig_pareto.add_trace(
            go.Scatter(
                x=df_pareto["departamento"],
                y=df_pareto["acumulado_pct"],
                name="% Acumulado",
                yaxis="y2",
                mode="lines+markers",
                line=dict(color="#0D9488", width=3),
                marker=dict(size=7),
            )
        )
        fig_pareto.update_layout(
            height=460,
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            margin=dict(l=10, r=10, t=15, b=65),
            xaxis=dict(tickangle=-35),
            yaxis=dict(title="Estudiantes", gridcolor="#E2E8F0"),
            yaxis2=dict(
                title="% Acumulado",
                overlaying="y",
                side="right",
                range=[0, 105],
                showgrid=False,
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_pareto, use_container_width=True)

with tab_institucional:
    c_i1, c_i2 = st.columns(2)

    with c_i1:
        st.subheader("Instituciones con Mayor Cobertura Estudiantil")
        df_inst_rank = (
            df_filtrado.groupby("institucion", as_index=False)
            .agg(
                matricula=("total_matriculas", "sum"),
                programas=("programa", "nunique"),
                departamentos=("departamento", "nunique"),
            )
            .sort_values("matricula", ascending=False)
            .head(15)
            .sort_values("matricula", ascending=True)
        )
        fig_inst = px.bar(
            df_inst_rank,
            x="matricula",
            y="institucion",
            orientation="h",
            text_auto=".2s",
            color="matricula",
            color_continuous_scale=["#475569", "#1E4E8C", "#0B1F3A"],
            hover_data={"programas": True, "departamentos": True, "matricula": ":,"},
            labels={
                "matricula": "Estudiantes Matriculados",
                "institucion": "Institucion",
                "programas": "Programas",
                "departamentos": "Departamentos",
            },
        )
        fig_inst.update_layout(
            height=470,
            coloraxis_showscale=False,
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            margin=dict(l=10, r=25, t=15, b=20),
            xaxis=dict(gridcolor="#E2E8F0"),
        )
        st.plotly_chart(fig_inst, use_container_width=True)

    with c_i2:
        st.subheader("Programas Academicos de Mayor Demanda")
        df_prog_rank = (
            df_filtrado.groupby("programa", as_index=False)
            .agg(
                matricula=("total_matriculas", "sum"),
                instituciones=("institucion", "nunique"),
            )
            .sort_values("matricula", ascending=False)
            .head(15)
            .sort_values("matricula", ascending=True)
        )
        fig_prog = px.bar(
            df_prog_rank,
            x="matricula",
            y="programa",
            orientation="h",
            text_auto=".2s",
            color="matricula",
            color_continuous_scale=["#64748B", "#0D9488", "#0F766E"],
            hover_data={"instituciones": True, "matricula": ":,"},
            labels={
                "matricula": "Estudiantes Matriculados",
                "programa": "Programa Academico",
                "instituciones": "IES que lo ofertan",
            },
        )
        fig_prog.update_layout(
            height=470,
            coloraxis_showscale=False,
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            margin=dict(l=10, r=25, t=15, b=20),
            xaxis=dict(gridcolor="#E2E8F0"),
        )
        st.plotly_chart(fig_prog, use_container_width=True)

    st.subheader("Segmentacion de Oferta por Tamano de Matricula")
    df_seg = (
        df_filtrado.groupby("segmento_matricula", as_index=False)
        .agg(
            cantidad_programas_ies=("total_matriculas", "count"),
            estudiantes_totales=("total_matriculas", "sum"),
        )
    )
    fig_seg = px.bar(
        df_seg,
        x="segmento_matricula",
        y=["cantidad_programas_ies", "estudiantes_totales"],
        barmode="group",
        color_discrete_sequence=["#1E4E8C", "#0D9488"],
        labels={
            "segmento_matricula": "Segmento de Escala",
            "value": "Cantidad",
            "variable": "Indicador",
        },
    )
    fig_seg.update_layout(
        height=310,
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=10, r=10, t=15, b=20),
        yaxis=dict(gridcolor="#E2E8F0"),
    )
    st.plotly_chart(fig_seg, use_container_width=True)

with tab_comparador:
    st.subheader("Benchmarking Directo entre Instituciones")
    st.caption("Seleccione entre 2 y 5 instituciones para comparar su alcance territorial, portafolio academico y volumen de estudiantes.")

    top_defaults = (
        df_filtrado.groupby("institucion")["total_matriculas"]
        .sum()
        .sort_values(ascending=False)
        .head(3)
        .index.tolist()
    )
    todas_ies = sorted(df_filtrado["institucion"].unique().tolist())

    ies_comparar = st.multiselect(
        "Instituciones seleccionadas para comparacion",
        options=todas_ies,
        default=top_defaults if len(top_defaults) >= 2 else todas_ies[:2],
        max_selections=5,
    )

    if len(ies_comparar) >= 2:
        df_comp = df_filtrado[df_filtrado["institucion"].isin(ies_comparar)]
        resumen_comp = (
            df_comp.groupby("institucion", as_index=False)
            .agg(
                matricula_total=("total_matriculas", "sum"),
                programas_activos=("programa", "nunique"),
                departamentos_presencia=("departamento", "nunique"),
                tasa_ref_regional=("tasa_ref_departamental", "mean"),
            )
            .sort_values("matricula_total", ascending=False)
        )
        resumen_comp["estudiantes_por_programa"] = (
            resumen_comp["matricula_total"] / resumen_comp["programas_activos"].replace(0, 1)
        ).round(1)

        st.dataframe(
            resumen_comp,
            use_container_width=True,
            column_config={
                "institucion": st.column_config.TextColumn("Institucion"),
                "matricula_total": st.column_config.NumberColumn("Matricula Total", format="%d"),
                "programas_activos": st.column_config.NumberColumn("Programas", format="%d"),
                "departamentos_presencia": st.column_config.NumberColumn("Departamentos", format="%d"),
                "tasa_ref_regional": st.column_config.NumberColumn("Tasa Ref. Regional (%)", format="%.2f%%"),
                "estudiantes_por_programa": st.column_config.NumberColumn("Estudiantes / Programa", format="%.1f"),
            },
        )

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            fig_b1 = px.bar(
                resumen_comp,
                x="institucion",
                y="matricula_total",
                color="institucion",
                text_auto=".2s",
                color_discrete_sequence=PALETA_AZULES,
                title="Comparacion de Poblacion Estudiantil",
                labels={"institucion": "Institucion", "matricula_total": "Estudiantes"},
            )
            fig_b1.update_layout(
                height=360,
                showlegend=False,
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
                yaxis=dict(gridcolor="#E2E8F0"),
            )
            st.plotly_chart(fig_b1, use_container_width=True)

        with col_b2:
            fig_b2 = px.bar(
                resumen_comp,
                x="institucion",
                y=["programas_activos", "departamentos_presencia"],
                barmode="group",
                color_discrete_sequence=["#0B1F3A", "#0D9488"],
                title="Oferta de Programas y Cobertura Geografica",
                labels={"institucion": "Institucion", "value": "Cantidad", "variable": "Dimension"},
            )
            fig_b2.update_layout(
                height=360,
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
                yaxis=dict(gridcolor="#E2E8F0"),
            )
            st.plotly_chart(fig_b2, use_container_width=True)
    else:
        st.info("Seleccione al menos 2 instituciones en el selector superior para activar el comparativo.")

with tab_simulador:
    col_s1, col_s2 = st.columns([2, 3])

    with col_s1:
        st.subheader("Tasa de Desercion por Departamento (SPADIES)")
        df_dep_tasa = (
            df_filtrado.groupby("departamento", as_index=False)
            .agg(
                tasa_ref=("tasa_ref_departamental", "mean"),
                matricula=("total_matriculas", "sum"),
            )
            .dropna(subset=["tasa_ref"])
            .sort_values("tasa_ref", ascending=False)
            .head(12)
            .sort_values("tasa_ref", ascending=True)
        )
        if not df_dep_tasa.empty:
            fig_tasa_dep = px.bar(
                df_dep_tasa,
                x="tasa_ref",
                y="departamento",
                orientation="h",
                text_auto=".1f",
                color="tasa_ref",
                color_continuous_scale=["#0D9488", "#D97706", "#B91C1C"],
                labels={
                    "tasa_ref": "Tasa Referencia (%)",
                    "departamento": "Departamento",
                },
            )
            fig_tasa_dep.update_layout(
                height=380,
                coloraxis_showscale=False,
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
                margin=dict(l=10, r=20, t=15, b=20),
                xaxis=dict(gridcolor="#E2E8F0"),
            )
            st.plotly_chart(fig_tasa_dep, use_container_width=True)
        else:
            st.info("No hay tasas referenciales disponibles para el filtro actual.")

    with col_s2:
        st.subheader("Simulador de Impacto de Estrategias de Retencion")
        st.caption(
            "Proyecte cuantos estudiantes permanecerian activos y el ahorro institucional al reducir la desercion en el segmento seleccionado."
        )

        if len(tasas_propias) > 0:
            tasa_base_sim = float(tasas_propias.mean())
            etiqueta_tasa = f"Tasa propia observada: {tasa_base_sim:.2f}%"
        elif len(tasas_ref_dep) > 0:
            tasa_base_sim = float(tasas_ref_dep.mean())
            etiqueta_tasa = f"Tasa departamental de referencia SPADIES: {tasa_base_sim:.2f}%"
        else:
            tasa_base_sim = 10.5
            etiqueta_tasa = "Tasa referencia nacional estimada: 10.50%"

        st.info(etiqueta_tasa)

        sim_c1, sim_c2 = st.columns(2)
        with sim_c1:
            reduccion_pct = st.slider(
                "Meta de reduccion de desercion (%)",
                min_value=5,
                max_value=50,
                value=15,
                step=5,
            )
        with sim_c2:
            valor_semestre_cop = st.number_input(
                "Valor promedio matricula semestral (COP)",
                min_value=500000,
                max_value=30000000,
                value=3500000,
                step=500000,
            )

        desertores_estimados = int(total_estudiantes * (tasa_base_sim / 100.0))
        estudiantes_retenidos = int(desertores_estimados * (reduccion_pct / 100.0))
        ingreso_protegido_cop = estudiantes_retenidos * valor_semestre_cop

        m_sim1, m_sim2, m_sim3 = st.columns(3)
        m_sim1.metric("Desercion proyectada actual", f"{desertores_estimados:,} est.")
        m_sim2.metric("Estudiantes retenidos (Meta)", f"+{estudiantes_retenidos:,} est.")
        m_sim3.metric("Matricula protegida (COP)", f"${ingreso_protegido_cop:,.0f}")

        st.markdown(
            """
            **Nota metodologica:** La clasificacion de riesgo institucional solo se asigna cuando existe medicion propia de la entidad academica, evitando imputar promedios departamentales sobre universidades individuales.
            """
        )

with tab_explorador:
    st.subheader("Buscador Detallado y Descarga de Datos Consolidados")

    col_e1, col_e2, col_e3 = st.columns([2, 1, 1])
    with col_e1:
        busqueda_tabla = st.text_input(
            "Filtrar registros en esta vista",
            placeholder="Escriba nombre de universidad, programa o departamento...",
            key="input_tabla_explorador",
        ).strip()
    with col_e2:
        col_orden = st.selectbox(
            "Ordenar por",
            options=["total_matriculas", "institucion", "departamento", "programa"],
            index=0,
        )
    with col_e3:
        es_ascendente = st.selectbox("Orden", options=["Descendente", "Ascendente"], index=0) == "Ascendente"

    df_tabla = df_filtrado.copy()
    if busqueda_tabla:
        termino_t = _normalizar_busqueda(busqueda_tabla)
        df_tabla = df_tabla[
            df_tabla["_indice_busqueda"].str.contains(termino_t, regex=False, na=False)
        ]

    df_tabla = df_tabla.sort_values(by=col_orden, ascending=es_ascendente)

    columnas_finales = [
        "institucion",
        "programa",
        "departamento",
        "total_matriculas",
        "tasa_ref_departamental",
        "segmento_matricula",
    ]

    st.caption(f"Mostrando {len(df_tabla):,} registros consolidados.")
    st.dataframe(
        df_tabla[columnas_finales],
        use_container_width=True,
        height=450,
        column_config={
            "institucion": st.column_config.TextColumn("Institucion de Educacion Superior", width="large"),
            "programa": st.column_config.TextColumn("Programa Academico", width="large"),
            "departamento": st.column_config.TextColumn("Departamento", width="medium"),
            "total_matriculas": st.column_config.NumberColumn("Matricula", format="%d"),
            "tasa_ref_departamental": st.column_config.NumberColumn("Tasa Ref. Depto (%)", format="%.2f%%"),
            "segmento_matricula": st.column_config.TextColumn("Escala", width="medium"),
        },
    )

    csv_bytes = df_tabla[columnas_finales].to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="Descargar reporte filtrado en formato CSV",
        data=csv_bytes,
        file_name="reporte_desercion_educacion_superior.csv",
        mime="text/csv",
        type="primary",
    )