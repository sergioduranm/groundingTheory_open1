# utils/file_utils.py
import json
import logging
import re
from typing import List, Dict, Any, Iterator, Optional, Union

logger = logging.getLogger(__name__)

def extract_json_from_text(text: str) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
    """
    Busca y extrae el primer bloque JSON válido de un string de texto usando una expresión regular.
    Es más robusto que buscar simplemente llaves, ya que maneja JSON anidado y texto circundante.
    """
    # Expresión regular para encontrar un bloque de código JSON (objeto o array)
    # que puede estar encerrado en ```json ... ```
    json_pattern = re.compile(r'```json\s*(\{.*\}|\[.*\])\s*```|(\{.*\}|\[.*\])', re.DOTALL)
    
    match = json_pattern.search(text)
    
    if not match:
        logger.warning("No se encontró ningún bloque de código JSON en el texto.")
        return None

    # El patrón tiene grupos de captura. El primer grupo que no sea None contiene el JSON.
    json_str = next((group for group in match.groups() if group is not None), None)

    if not json_str:
         logger.warning("La expresión regular encontró un patrón pero no pudo extraer el contenido JSON.")
         return None

    try:
        # Limpiar por si acaso el string tiene espacios extra al principio/final
        return json.loads(json_str.strip())
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

def write_text_file(file_path: str, content: str):
    """
    Escribe contenido de texto a un archivo, sobrescribiéndolo si existe.
    
    Args:
        file_path (str): Ruta del archivo a escribir
        content (str): Contenido a escribir
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Archivo de texto escrito exitosamente: {file_path}")
    except IOError as e:
        logger.error(f"Error escribiendo el archivo de texto {file_path}: {e}")
        raise

def load_prompt_template(file_path: str) -> str:
    """
    Carga una plantilla de prompt desde un archivo de texto.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Archivo de plantilla de prompt no encontrado: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado al cargar la plantilla de prompt {file_path}: {e}")
        raise 