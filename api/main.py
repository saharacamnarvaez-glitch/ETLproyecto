import sys
import os
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

ROOT_DIR = Path(__file__).resolve().parents[1]
for p in [str(ROOT_DIR), str(ROOT_DIR / "medallon")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from src.transform.transform_silver import ejecutar_transformacion_silver
from src.transform.transform_gold import ejecutar_transformacion_gold
from src.load.load_datawarehouse import ejecutar_carga_completa

app = FastAPI(title="ETL Deserción Estudiantil", version="2.0")


@app.get("/health")
def health():
    return {"status": "ok", "message": "Servicio ETL activo"}


@app.get("/info")
def info():
    return {
        "project": "ETL Deserción en Educación Superior",
        "version": "2.0",
        "architecture": "Medallion (Bronze/Silver/Gold/Warehouse)",
        "sources": ["API Datos Abiertos (SNIES)", "Excel SPADIES (MEN)"],
    }


@app.post("/run")
def run_pipeline():
    try:
        if not ejecutar_transformacion_silver():
            raise HTTPException(status_code=500, detail="Error en capa Silver")
        if not ejecutar_transformacion_gold():
            raise HTTPException(status_code=500, detail="Error en capa Gold")
        if not ejecutar_carga_completa():
            raise HTTPException(status_code=500, detail="Error en carga al Data Warehouse")
        return {"message": "Pipeline Medallón y Data Warehouse completados exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/silver")
def get_silver():
    ruta = ROOT_DIR / "data" / "silver" / "silver_dataset_integrado.csv"
    if not ruta.exists():
        raise HTTPException(status_code=404, detail="Silver no generado")
    return FileResponse(str(ruta), media_type="text/csv", filename="silver.csv")


@app.get("/gold")
def get_gold():
    ruta = ROOT_DIR / "data" / "gold" / "gold_final.csv"
    if not ruta.exists():
        raise HTTPException(status_code=404, detail="Gold no generado")
    return FileResponse(str(ruta), media_type="text/csv", filename="gold.csv")


@app.get("/gold/departamental")
def get_gold_departamental():
    ruta = ROOT_DIR / "data" / "gold" / "gold_referencia_departamental.csv"
    if not ruta.exists():
        raise HTTPException(status_code=404, detail="Gold departamental no generado")
    return FileResponse(str(ruta), media_type="text/csv", filename="gold_referencia_departamental.csv")


@app.get("/quality/metrics")
def quality_metrics():
    metrics = {"silver": {}, "gold": {}, "gold_departamental": {}}

    silver_path = ROOT_DIR / "data" / "silver" / "silver_dataset_integrado.csv"
    gold_path = ROOT_DIR / "data" / "gold" / "gold_final.csv"
    gold_dept_path = ROOT_DIR / "data" / "gold" / "gold_referencia_departamental.csv"

    if silver_path.exists():
        df_s = pd.read_csv(silver_path, low_memory=False)
        metrics["silver"] = {
            "registros": len(df_s),
            "columnas": len(df_s.columns),
            "nulos": int(df_s.isna().sum().sum()),
        }

    if gold_path.exists():
        df_g = pd.read_csv(gold_path, low_memory=False)
        metrics["gold"] = {
            "registros": len(df_g),
            "columnas": len(df_g.columns),
            "granularidad": "entidad",
            "niveles_riesgo": df_g["nivel_riesgo"].value_counts().to_dict() if "nivel_riesgo" in df_g.columns else {},
        }

    if gold_dept_path.exists():
        df_gd = pd.read_csv(gold_dept_path, low_memory=False)
        metrics["gold_departamental"] = {
            "registros": len(df_gd),
            "granularidad": "departamento",
            "tasa_promedio_nacional": round(float(df_gd["tasa_desercion_departamental"].mean()), 4),
        }

    return metrics


@app.get("/dataset/sample")
def dataset_sample(rows: int = 5):
    gold_path = ROOT_DIR / "data" / "gold" / "gold_final.csv"
    silver_path = ROOT_DIR / "data" / "silver" / "silver_dataset_integrado.csv"

    if gold_path.exists():
        df = pd.read_csv(gold_path, low_memory=False)
        return df.head(rows).to_dict(orient="records")
    elif silver_path.exists():
        df = pd.read_csv(silver_path, low_memory=False)
        return df.head(rows).to_dict(orient="records")
    else:
        raise HTTPException(status_code=404, detail="No hay datos disponibles")