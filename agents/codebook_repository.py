import json
import logging
from pathlib import Path
from typing import Dict, Any

# Usamos el mismo logger configurado para consistencia
logger = logging.getLogger(__name__)

class CodebookRepository:
    """
    Repositorio para manejar la persistencia del codebook en formato JSON.
    Permite cargar y guardar el codebook desde/hacia un archivo.
    """
    
    def __init__(self, codebook_path: str = "data/codebook.json"):
        """
        Inicializa el repositorio con la ruta del archivo de codebook.
        
        Args:
            codebook_path: Ruta del archivo JSON donde se almacena el codebook
        """
        self.codebook_path = Path(codebook_path)
        logger.info(f"📁 CodebookRepository inicializado con ruta: {self.codebook_path}")
        
        # Crear el directorio padre si no existe
        self.codebook_path.parent.mkdir(parents=True, exist_ok=True)
    
    def load(self) -> Dict[str, Any]:
        """
        Carga el codebook desde el archivo JSON.
        Si el archivo no existe, retorna una estructura de codebook vacía.
        
        Returns:
            Dict conteniendo la estructura del codebook con la lista de códigos
        """
        try:
            if self.codebook_path.exists():
                logger.info(f"📖 Cargando codebook desde: {self.codebook_path}")
                with open(self.codebook_path, 'r', encoding='utf-8') as f:
                    codebook = json.load(f)
                logger.info(f"✅ Codebook cargado exitosamente con {len(codebook.get('codes', []))} códigos")
                return codebook
            else:
                logger.info(f"📝 Archivo de codebook no existe, creando estructura vacía: {self.codebook_path}")
                return {"codes": []}
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error al decodificar JSON del codebook: {e}")
            logger.info("📝 Retornando estructura de codebook vacía debido al error")
            return {"codes": []}
        except Exception as e:
            logger.error(f"❌ Error inesperado al cargar codebook: {e}")
            logger.info("📝 Retornando estructura de codebook vacía debido al error")
            return {"codes": []}
    
    def save(self, codebook: Dict[str, Any]) -> None:
        """
        Guarda el codebook en el archivo JSON.
        
        Args:
            codebook: Diccionario conteniendo la estructura del codebook
        """
        try:
            logger.info(f"💾 Guardando codebook en: {self.codebook_path}")
            with open(self.codebook_path, 'w', encoding='utf-8') as f:
                json.dump(codebook, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Codebook guardado exitosamente con {len(codebook.get('codes', []))} códigos")
        except Exception as e:
            logger.error(f"❌ Error al guardar codebook: {e}")
            raise 