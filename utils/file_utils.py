# utils/file_utils.py
import json
import logging
import re
from typing import List, Dict, Any, Iterator, Optional, Union

logger = logging.getLogger(__name__)

def extract_json_from_text(text: str) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
    """
    Busca y extrae el primer bloque JSON válido de un string de texto, ya sea un objeto o una lista.
    Ideal para limpiar respuestas de LLMs que envuelven el JSON con texto explicativo.
    """
    # Buscar el inicio del JSON (puede ser un objeto o una lista)
    first_char_pos = -1
    first_brace = text.find('{')
    first_bracket = text.find('[')

    if first_brace != -1 and first_bracket != -1:
        first_char_pos = min(first_brace, first_bracket)
    elif first_brace != -1:
        first_char_pos = first_brace
    else:
        first_char_pos = first_bracket

    if first_char_pos == -1:
        logger.warning("No se encontró ningún carácter de inicio de JSON ('{' o '[') en el texto.")
        return None

    # Determinar el carácter de cierre correspondiente
    start_char = text[first_char_pos]
    end_char = '}' if start_char == '{' else ']'

    # Buscar el último carácter de cierre
    last_char_pos = text.rfind(end_char)

    if last_char_pos == -1 or last_char_pos < first_char_pos:
        logger.warning(f"Se encontró un '{start_char}' de inicio pero no un '{end_char}' de cierre válido.")
        return None

    # Extraer el substring que potencialmente es un JSON
    json_str = text[first_char_pos:last_char_pos + 1]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"Se encontró un bloque JSON-like pero no se pudo parsear: {e}")
        logger.debug(f"Bloque JSON problemático: {json_str}")
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

def save_insights_metadata(registry: Any, file_path: str):
    """
    Guarda el registro de metadatos de insights en un archivo JSON.
    El objeto 'registry' debe ser un modelo de Pydantic o tener un método 'dict()'.
    """
    try:
        if hasattr(registry, 'model_dump'):
            # Pydantic v2
            data_to_save = registry.model_dump()
        elif hasattr(registry, 'dict'):
            # Pydantic v1
            data_to_save = registry.dict()
        else:
            # Asumir que es un dict-like object
            data_to_save = registry
            
        save_json_file(file_path, data_to_save)
        logger.info(f"Metadatos de insights guardados exitosamente en {file_path}")
    except Exception as e:
        logger.error(f"Error al guardar los metadatos de insights en {file_path}: {e}")
        raise 