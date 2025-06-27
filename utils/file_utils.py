# utils/file_utils.py
import json
import logging
import re
from typing import List, Dict, Any, Iterator, Optional

logger = logging.getLogger(__name__)

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Busca y extrae el primer bloque JSON válido de un string de texto.
    Ideal para limpiar respuestas de LLMs que envuelven el JSON con texto explicativo.
    """
    # Expresión regular para encontrar contenido entre el primer { y el último }
    # El modificador re.DOTALL (o re.S) permite que '.' coincida con saltos de línea.
    match = re.search(r'\{.*\}', text, re.DOTALL)
    
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Se encontró un bloque JSON-like pero no se pudo parsear: {e}")
            logger.debug(f"Bloque JSON problemático: {json_str}")
            return None
    else:
        logger.warning("No se encontró ningún bloque JSON en el texto.")
        return None

def load_json_file(file_path: str) -> Any:
    """Carga un archivo JSON completo en memoria."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"El archivo no fue encontrado: {file_path}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Error al decodificar JSON del archivo: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Ocurrió un error inesperado al leer {file_path}: {e}")
        raise

def save_json_file(file_path: str, data: Any):
    """Guarda los datos en un archivo JSON."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Ocurrió un error inesperado al guardar en {file_path}: {e}")
        raise

def load_jsonl_file(file_path: str) -> Iterator[Dict[str, Any]]:
    """
    Carga un archivo JSONL (JSON Lines) de forma perezosa, línea por línea.
    Esto es eficiente en memoria para archivos grandes.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)
    except FileNotFoundError:
        logger.error(f"El archivo no fue encontrado: {file_path}")
        # Devolvemos un iterador vacío si el archivo no existe,
        # lo cual puede ser un caso de uso válido (p.ej. al iniciar un proceso).
        return iter([])
    except Exception as e:
        logger.error(f"Ocurrió un error inesperado al leer {file_path}: {e}")
        raise

def append_to_jsonl_file(file_path: str, data: Dict[str, Any]):
    """
    Añade un único registro (diccionario) a un archivo JSONL.
    Perfecto para guardado incremental.
    """
    try:
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
    except Exception as e:
        logger.error(f"Ocurrió un error inesperado al añadir a {file_path}: {e}")
        raise 