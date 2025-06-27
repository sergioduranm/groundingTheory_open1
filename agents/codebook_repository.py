import logging
from pathlib import Path
from pydantic import ValidationError

from models.data_models import Codebook
from utils.file_utils import load_json_file, save_json_file

# Usamos el mismo logger configurado para consistencia
logger = logging.getLogger(__name__)

class CodebookRepository:
    """
    Repositorio robusto para manejar la persistencia del codebook.
    Utiliza Pydantic para la validación de datos y centraliza la I/O.
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
    
    def load(self) -> Codebook:
        """
        Carga y valida el codebook desde el archivo JSON.
        Si el archivo no existe o está corrupto, retorna un codebook vacío.
        """
        if not self.codebook_path.exists():
            logger.info(f"📝 Archivo de codebook no existe, creando estructura vacía: {self.codebook_path}")
            return Codebook(codes=[])
        
        try:
            logger.info(f"📖 Cargando codebook desde: {self.codebook_path}")
            data = load_json_file(str(self.codebook_path))
            codebook = Codebook.model_validate(data)
            logger.info(f"✅ Codebook cargado y validado exitosamente con {len(codebook.codes)} códigos")
            return codebook
        except (ValidationError, Exception) as e:
            logger.error(f"❌ Error al cargar o validar el codebook: {e}. Se creará un codebook nuevo.")
            return Codebook(codes=[])
    
    def save(self, codebook: Codebook) -> None:
        """
        Guarda un objeto Codebook validado en el archivo JSON.
        
        Args:
            codebook: El objeto Codebook a guardar.
        """
        try:
            logger.info(f"💾 Guardando codebook en: {self.codebook_path}")
            # Convertimos el modelo Pydantic a un diccionario antes de guardarlo.
            data_to_save = codebook.model_dump(mode='json')
            save_json_file(str(self.codebook_path), data_to_save)
            logger.info(f"✅ Codebook guardado exitosamente con {len(codebook.codes)} códigos")
        except Exception as e:
            logger.error(f"❌ Error al guardar codebook: {e}")
            raise 