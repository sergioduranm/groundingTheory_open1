#!/usr/bin/env python3
"""
Módulo de Preprocesamiento de Datos
===================================

Este módulo se encarga de convertir archivos Excel a formato JSONL
para su posterior procesamiento por el sistema de agentes.
"""

import json
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Any

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_jsonl_from_excel(input_path: str, output_path: str) -> bool:
    """
    Convierte un archivo Excel a formato JSONL.
    
    Esta función lee un archivo Excel con columnas 'ID' e 'InsightText'
    y lo convierte al formato JSONL requerido por el sistema de agentes.
    
    Args:
        input_path (str): Ruta al archivo Excel de entrada
        output_path (str): Ruta donde se guardará el archivo JSONL
        
    Returns:
        bool: True si la conversión fue exitosa, False en caso contrario
        
    Raises:
        FileNotFoundError: Si el archivo de entrada no existe
        ValueError: Si el archivo de entrada no es un Excel válido
    """
    try:
        logger.info(f"Procesando archivo Excel: {input_path}")
        logger.info(f"Archivo de salida: {output_path}")
        
        # Leer el archivo Excel
        df = pd.read_excel(input_path)
        
        # Verificar que las columnas requeridas existan
        required_columns = ['ID', 'InsightText']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Columnas faltantes en el archivo Excel: {missing_columns}")
        
        # Crear el directorio de salida si no existe
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Convertir DataFrame a formato JSONL
        with open(output_path, 'w', encoding='utf-8') as jsonl_file:
            for _, row in df.iterrows():
                # Crear objeto JSON para cada fila
                json_obj = {
                    'id': str(row['ID']),  # Convertir a string para asegurar compatibilidad
                    'text': str(row['InsightText'])  # Convertir a string para asegurar compatibilidad
                }
                
                # Escribir línea JSON al archivo
                jsonl_file.write(json.dumps(json_obj, ensure_ascii=False) + '\n')
        
        logger.info(f"Conversión completada exitosamente. {len(df)} registros procesados.")
        return True
        
    except FileNotFoundError:
        logger.error(f"Error: El archivo '{input_path}' no fue encontrado.")
        print(f"Error: El archivo '{input_path}' no fue encontrado.")
        return False
        
    except ValueError as e:
        logger.error(f"Error de validación: {e}")
        print(f"Error de validación: {e}")
        return False
        
    except Exception as e:
        logger.error(f"Error inesperado durante el procesamiento: {e}")
        print(f"Error inesperado durante el procesamiento: {e}")
        return False


def validate_excel_file(file_path: str) -> bool:
    """
    Valida que el archivo Excel sea válido y accesible.
    
    Args:
        file_path (str): Ruta al archivo Excel
        
    Returns:
        bool: True si el archivo es válido, False en caso contrario
    """
    try:
        # Verificar que el archivo existe
        if not Path(file_path).exists():
            logger.error(f"El archivo '{file_path}' no existe.")
            return False
        
        # Intentar leer el archivo Excel
        df = pd.read_excel(file_path)
        
        # Verificar que tiene las columnas requeridas
        required_columns = ['ID', 'InsightText']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.error(f"Columnas faltantes: {missing_columns}")
            return False
        
        # Verificar que no esté vacío
        if df.empty:
            logger.error("El archivo Excel está vacío.")
            return False
        
        logger.info(f"Archivo Excel válido: {len(df)} filas encontradas.")
        return True
        
    except Exception as e:
        logger.error(f"Error al validar el archivo Excel: {e}")
        return False


def main() -> None:
    """
    Función principal que ejecuta el preprocesamiento.
    """
    # Definir rutas de archivos
    input_file = "data/insights.xlsx"
    output_file = "data/data.jsonl"
    
    print("Iniciando preprocesamiento de datos...")
    
    # Validar archivo de entrada
    if not validate_excel_file(input_file):
        print("Error: El archivo de entrada no es válido.")
        return
    
    # Procesar archivo Excel
    success = create_jsonl_from_excel(input_file, output_file)
    
    if success:
        print("¡Preprocesamiento completado exitosamente!")
        print(f"Archivo generado: {output_file}")
    else:
        print("Error durante el preprocesamiento.")


if __name__ == "__main__":
    main()
