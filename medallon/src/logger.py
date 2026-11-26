import logging
import os

def get_logger(name="ETL_Pipeline"):
    """
    Configura y retorna el logger del proyecto.
    Guarda los registros en logs/etl_execution.log y los muestra en consola.
    """
    
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    log_dir = os.path.join(root_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Ruta exacta del archivo de historial
    log_file = os.path.join(log_dir, "etl_execution.log")

    # Crear el objeto logger
    logger = logging.getLogger(name)
    
    # Evitar que los mensajes se dupliquen si la función se llama varias veces
    if not logger.handlers:
        logger.setLevel(logging.INFO)

        
        formato = logging.Formatter('%(asctime)s | %(levelname)s | %(module)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formato)

     
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formato)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger