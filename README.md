# Análisis de Deserción Estudiantil en Educación Superior — Pipeline ETL Medallón

Proyecto de Ingeniería de Datos para la ingesta, limpieza, integración, modelado analítico, consulta y visualización de indicadores de deserción y matrícula en educación superior en Colombia, estructurado bajo una **Arquitectura Medallón** (`Bronze` $\rightarrow$ `Silver` $\rightarrow$ `Gold`), cargado en un **Data Warehouse SQLite**, expuesto mediante una **API REST en FastAPI**, visualizado en un **tablero interactivo en Streamlit** y orquestado con **Apache Airflow**.

## Autores

* **Gabriela Perea**
* **Sahara Narvaez**
* **Juan Pablo Paredes**

---

## Arquitectura del Proyecto

```text
ETLproyecto/
├── api/                        # Servicio REST con FastAPI
├── dags/                       # DAG de orquestación con Apache Airflow (etl_pipeline.py)
├── data/
│   ├── bronze/                 # Ingesta cruda (JSON de API y CSV extraídos de SPADIES/Excel)
│   ├── silver/                 # Datos limpios, normalizados e integrados (silver_dataset_integrado.csv)
│   ├── gold/                   # Tablas analíticas (gold_final.csv y gold_referencia_departamental.csv)
│   └── warehouse/              # Base de datos SQLite (etl_warehouse.db)
├── docker/                     # Dockerfile y docker-compose.yml 
├── medallon/
│   ├── notebooks/              # Análisis exploratorio de datos (eda.ipynb)
│   └── src/                    # Módulos de transformación (Silver/Gold) y carga al Data Warehouse
├── streamlit_app/              # Aplicación analítica multipestaña en Streamlit
├── tests/                      # Suite de pruebas automatizadas con pytest
└── requirements.txt            # Dependencias unificadas del entorno
