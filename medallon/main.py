import os
import sys
import yaml

# Asegurar que Python encuentre los modulos dentro de la carpeta src
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Importar el logger
from src.logger import get_logger

# Importar las funciones
from src.extraction.extraction_api import extraer_api
from src.extraction.extraction_excel import extraer_excel 
from src.transform.transform_silver import ejecutar_transformacion_silver
from src.transform.transform_gold import ejecutar_transformacion_gold

# Inicializar el logger
logger = get_logger("Orquestador")

def cargar_configuracion():
    ruta_config = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
    try:
        with open(ruta_config, 'r', encoding='utf-8') as archivo:
            return yaml.safe_load(archivo)
    except Exception as e:
        logger.error(f"Error al leer config.yaml en la ruta {ruta_config}: {e}")
        return None

def main():
    config = cargar_configuracion()
    if not config:
        return

    nombre_proyecto = config['project']['name']
    version = config['project']['version']

    logger.info("=" * 60)
    logger.info(f"INICIANDO PIPELINE: {nombre_proyecto.upper()} (v{version})")
    logger.info("=" * 60)
    
    # 1. CAPA BRONZE (Extraccion)
    logger.info("[1/3] CAPA BRONZE: Iniciando extraccion de datos crudos")
    exito_bronze = True
    try:
        logger.info("Ejecutando extracción de API...")
        extraer_api()
        
        logger.info("Ejecutando extracción de Excel...")
        extraer_excel()
        logger.info("Extracción Bronze finalizada correctamente.")
    except Exception as e:
        logger.error(f"Fallo crítico en la Capa Bronze: {e}")
        exito_bronze = False

    # 2. CAPA SILVER (Limpieza e Integracion)
    exito_silver = False
    if exito_bronze:
        logger.info("[2/3] CAPA SILVER: Iniciando limpieza y cruzamiento de fuentes (JOIN)")
        try:
            exito_silver = ejecutar_transformacion_silver()
        except Exception as e:
            logger.error(f"Fallo crítico en la Capa Silver: {e}")
    else:
        logger.warning("Proceso detenido. La Capa Silver no se ejecutara porque Bronze fallo.")

    # 3. CAPA GOLD (Reportes de Negocio)
    if exito_silver:
        logger.info("[3/3] CAPA GOLD: Generacion de KPIs e indicadores")
        try:
            exito_gold = ejecutar_transformacion_gold()
            if exito_gold:
                logger.info("PIPELINE FINALIZADO CON EXITO.")
            else:
                logger.warning("La Capa Gold se ejecutó pero no se completó correctamente.")
        except Exception as e:
            logger.error(f"Fallo crítico en la Capa Gold: {e}")
    else:
        logger.warning("Proceso detenido. La Capa Gold no se ejecutara porque Silver fallo.")

if __name__ == "__main__":
    main()