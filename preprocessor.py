#!/usr/bin/env python3
"""
Módulo de Preprocesamiento de Datos
===================================

Este módulo se encarga de convertir archivos Excel a formato JSONL
para su posterior procesamiento por el sistema de agentes.
Ahora también genera un archivo de metadatos para trazabilidad de fuentes.
"""

import json
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from models.data_models import InsightsMetadataRegistry, InsightMetadata
from utils.file_utils import save_insights_metadata

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_jsonl_and_metadata_from_excel(
    input_path: str, 
    output_jsonl_path: str, 
    output_metadata_path: str,
    required_columns: Optional[list] = None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Convierte un archivo Excel a formato JSONL y genera metadatos de trazabilidad.
    
    Esta función lee un archivo Excel y genera dos archivos:
    1. Un archivo JSONL con los insights (id, text)
    2. Un archivo JSON con metadatos de trazabilidad (method, source)
    
    Args:
        input_path (str): Ruta al archivo Excel de entrada
        output_jsonl_path (str): Ruta donde se guardará el archivo JSONL
        output_metadata_path (str): Ruta donde se guardará el archivo de metadatos
        required_columns (Optional[list]): Columnas requeridas. Por defecto ['ID', 'InsightText']
        
    Returns:
        Tuple[bool, Dict[str, Any]]: (éxito, reporte de procesamiento)
        
    Raises:
        FileNotFoundError: Si el archivo de entrada no existe
        ValueError: Si el archivo de entrada no es un Excel válido
    """
    if required_columns is None:
        required_columns = ['ID', 'InsightText']
    
    report = {
        "success": False,
        "total_insights": 0,
        "processed_insights": 0,
        "errors": [],
        "warnings": [],
        "metadata_generated": False
    }
    
    try:
        logger.info(f"Procesando archivo Excel: {input_path}")
        logger.info(f"Archivo JSONL de salida: {output_jsonl_path}")
        logger.info(f"Archivo de metadatos de salida: {output_metadata_path}")
        
        # Leer el archivo Excel
        df = pd.read_excel(input_path)
        report["total_insights"] = len(df)
        
        # Verificar que las columnas requeridas existan
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            error_msg = f"Columnas faltantes en el archivo Excel: {missing_columns}"
            logger.error(error_msg)
            report["errors"].append(error_msg)
            return False, report
        
        # Verificar columnas opcionales para metadatos
        has_metadata_columns = 'Method' in df.columns and 'Source' in df.columns
        if has_metadata_columns:
            logger.info("Columnas de metadatos detectadas: Method, Source")
        else:
            logger.warning("Columnas de metadatos no encontradas. Se generará JSONL sin metadatos.")
            report["warnings"].append("Columnas de metadatos (Method, Source) no encontradas")
        
        # Crear directorios de salida si no existen
        Path(output_jsonl_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_metadata_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Procesar insights y generar metadatos
        registry = InsightsMetadataRegistry()
        processed_count = 0
        
        with open(output_jsonl_path, 'w', encoding='utf-8') as jsonl_file:
            for index, row in df.iterrows():
                try:
                    # Validar datos requeridos
                    insight_id = str(row['ID']).strip()
                    insight_text = str(row['InsightText']).strip()
                    
                    if not insight_id or not insight_text:
                        warning_msg = f"Fila {index + 1}: ID o texto vacío, se omite"
                        logger.warning(warning_msg)
                        report["warnings"].append(warning_msg)
                        continue
                    
                    # Crear objeto JSON para JSONL
                    json_obj = {
                        'id': insight_id,
                        'text': insight_text
                    }
                    
                    # Escribir línea JSON al archivo
                    jsonl_file.write(json.dumps(json_obj, ensure_ascii=False) + '\n')
                    
                    # Generar metadatos si están disponibles
                    if has_metadata_columns:
                        method = str(row['Method']).strip() if pd.notna(row['Method']) else "unknown"
                        source = str(row['Source']).strip() if pd.notna(row['Source']) else "unknown"
                        
                        metadata = InsightMetadata(
                            method=method,
                            source=source
                        )
                        registry.insights[insight_id] = metadata
                    
                    processed_count += 1
                    
                except Exception as e:
                    error_msg = f"Error procesando fila {index + 1}: {str(e)}"
                    logger.error(error_msg)
                    report["errors"].append(error_msg)
        
        # Guardar metadatos si se generaron
        if has_metadata_columns and registry.insights:
            try:
                save_insights_metadata(registry, output_metadata_path)
                report["metadata_generated"] = True
                logger.info(f"Metadatos guardados: {len(registry.insights)} registros")
            except Exception as e:
                error_msg = f"Error al guardar metadatos: {str(e)}"
                logger.error(error_msg)
                report["errors"].append(error_msg)
        
        report["processed_insights"] = processed_count
        report["success"] = True
        
        logger.info(f"Conversión completada exitosamente. {processed_count} registros procesados.")
        return True, report
        
    except FileNotFoundError:
        error_msg = f"Error: El archivo '{input_path}' no fue encontrado."
        logger.error(error_msg)
        report["errors"].append(error_msg)
        return False, report
        
    except ValueError as e:
        error_msg = f"Error de validación: {e}"
        logger.error(error_msg)
        report["errors"].append(error_msg)
        return False, report
        
    except Exception as e:
        error_msg = f"Error inesperado durante el procesamiento: {e}"
        logger.error(error_msg)
        report["errors"].append(error_msg)
        return False, report


def create_jsonl_from_excel(input_path: str, output_path: str) -> bool:
    """
    Función de compatibilidad hacia atrás.
    Convierte un archivo Excel a formato JSONL (solo).
    
    Args:
        input_path (str): Ruta al archivo Excel de entrada
        output_path (str): Ruta donde se guardará el archivo JSONL
        
    Returns:
        bool: True si la conversión fue exitosa, False en caso contrario
    """
    logger.info("Usando función de compatibilidad hacia atrás")
    success, report = create_jsonl_and_metadata_from_excel(
        input_path=input_path,
        output_jsonl_path=output_path,
        output_metadata_path="",  # No se genera metadatos
        required_columns=['ID', 'InsightText']  # Solo columnas básicas
    )
    
    if not success:
        for error in report["errors"]:
            print(f"Error: {error}")
    
    return success


def validate_excel_file(file_path: str, check_metadata_columns: bool = False) -> bool:
    """
    Valida que el archivo Excel sea válido y accesible.
    
    Args:
        file_path (str): Ruta al archivo Excel
        check_metadata_columns (bool): Si True, también valida columnas de metadatos
        
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
        
        # Verificar columnas requeridas básicas
        required_columns = ['ID', 'InsightText']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.error(f"Columnas faltantes: {missing_columns}")
            return False
        
        # Verificar columnas de metadatos si se solicita
        if check_metadata_columns:
            metadata_columns = ['Method', 'Source']
            missing_metadata = [col for col in metadata_columns if col not in df.columns]
            if missing_metadata:
                logger.warning(f"Columnas de metadatos faltantes: {missing_metadata}")
                logger.info("El archivo será procesado sin metadatos de trazabilidad")
        
        # Verificar que no esté vacío
        if df.empty:
            logger.error("El archivo Excel está vacío.")
            return False
        
        # Validar datos básicos
        invalid_rows = 0
        for index, row in df.iterrows():
            if pd.isna(row['ID']) or pd.isna(row['InsightText']):
                invalid_rows += 1
        
        if invalid_rows > 0:
            logger.warning(f"Se encontraron {invalid_rows} filas con datos inválidos")
        
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
    output_jsonl_file = "data/data.jsonl"
    output_metadata_file = "data/insights_metadata.json"
    
    print("Iniciando preprocesamiento de datos...")
    
    # Validar archivo de entrada (incluyendo columnas de metadatos)
    if not validate_excel_file(input_file, check_metadata_columns=True):
        print("Error: El archivo de entrada no es válido.")
        return
    
    # Procesar archivo Excel
    success, report = create_jsonl_and_metadata_from_excel(
        input_path=input_file,
        output_jsonl_path=output_jsonl_file,
        output_metadata_path=output_metadata_file
    )
    
    if success:
        print("¡Preprocesamiento completado exitosamente!")
        print(f"Archivo JSONL generado: {output_jsonl_file}")
        print(f"Insights procesados: {report['processed_insights']}/{report['total_insights']}")
        
        if report["metadata_generated"]:
            print(f"Archivo de metadatos generado: {output_metadata_file}")
        else:
            print("No se generaron metadatos (columnas Method/Source no encontradas)")
        
        if report["warnings"]:
            print("\nAdvertencias:")
            for warning in report["warnings"]:
                print(f"  - {warning}")
    else:
        print("Error durante el preprocesamiento:")
        for error in report["errors"]:
            print(f"  - {error}")


if __name__ == "__main__":
    main()
