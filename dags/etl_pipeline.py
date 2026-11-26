import sys
from pathlib import Path
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

ROOT_DIR = Path(__file__).resolve().parents[1]
for p in [str(ROOT_DIR), str(ROOT_DIR / "medallon")]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from medallon.src.transform.transform_silver import ejecutar_transformacion_silver
    from medallon.src.transform.transform_gold import ejecutar_transformacion_gold
    from medallon.src.load.load_datawarehouse import ejecutar_carga_completa
except ImportError:
    from src.transform.transform_silver import ejecutar_transformacion_silver
    from src.transform.transform_gold import ejecutar_transformacion_gold
    from src.load.load_datawarehouse import ejecutar_carga_completa

default_args = {
    "owner": "etl-team",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "etl_pipeline_dag",
    default_args=default_args,
    description="Pipeline ETL de deserción estudiantil en capas Medallion",
    schedule_interval="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["etl", "educacion"],
) as dag:

    t_run_silver = PythonOperator(
        task_id="run_silver",
        python_callable=ejecutar_transformacion_silver,
    )

    t_run_gold = PythonOperator(
        task_id="run_gold",
        python_callable=ejecutar_transformacion_gold,
    )

    t_run_warehouse = PythonOperator(
        task_id="run_warehouse",
        python_callable=ejecutar_carga_completa,
    )

    t_run_silver >> t_run_gold >> t_run_warehouse