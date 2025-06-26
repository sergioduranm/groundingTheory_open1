# agents/embedding_client.py

import logging
import time
from typing import List, Optional

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# --- Configuración de Logging Estructurado ---
# Reemplaza los 'print' por un sistema de logging real.
# Esto permite controlar el nivel de detalle (INFO, WARNING, ERROR) y dirigir la salida a archivos.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Definición de Errores para Reintentos ---
# Especificamos qué errores son temporales (de red, de servidor) y merecen un reintento.
RETRYABLE_EXCEPTIONS = (
    google_exceptions.InternalServerError,   # Error 500 del servidor de Google
    google_exceptions.TooManyRequests,       # Error 429 por límite de velocidad
    google_exceptions.ServiceUnavailable,    # Error 503 por mantenimiento o sobrecarga
)

class EmbeddingClient:
    """
    Cliente de embeddings robusto y listo para producción.
    
    Características:
    - Logging estructurado para monitoreo.
    - Lógica de reintentos con backoff exponencial para errores de API.
    - Procesamiento por lotes (batching) para manejar grandes volúmenes de texto.
    - Manejo de errores específico y seguro.
    """
    def __init__(self, api_key: str, model_name: str = 'models/embedding-001', batch_size: int = 100):
        """
        Inicializa y configura el cliente de forma segura.

        Args:
            api_key (str): Tu clave API de Google AI. Se valida que no esté vacía.
            model_name (str): El modelo de embedding a utilizar.
            batch_size (int): El número máximo de textos a enviar en una sola llamada a la API.
        """
        if not isinstance(api_key, str) or len(api_key) < 10:
            logger.error("API Key inválida o ausente. Por favor, proporciona una clave válida.")
            raise ValueError("API Key inválida.")
            
        self.model_name = model_name
        self.batch_size = batch_size
        
        try:
            genai.configure(api_key=api_key)
            logger.info(f"Cliente de Embeddings configurado para el modelo: '{self.model_name}' con lotes de {self.batch_size}.")
        except Exception as e:
            logger.critical(f"Fallo crítico al configurar la API de Google AI: {e}")
            raise

    def get_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Genera embeddings para una lista de textos, manejando lotes y errores.

        Args:
            texts (List[str]): Una lista de strings para generar embeddings.
        
        Returns:
            List[Optional[List[float]]]: Una lista de vectores (embeddings). 
                                          Retorna None para los textos que fallaron.
        """
        # Validación de entrada
        if not texts:
            return []
        
        valid_texts = [text for text in texts if isinstance(text, str) and text.strip()]
        if len(valid_texts) != len(texts):
            logger.warning("Algunos textos de entrada estaban vacíos o no eran strings y fueron omitidos.")

        all_embeddings = []
        # Implementación de Límite de Lote (batch_size)
        for i in range(0, len(valid_texts), self.batch_size):
            batch = valid_texts[i:i + self.batch_size]
            logger.info(f"Procesando lote {i//self.batch_size + 1} con {len(batch)} textos.")
            
            # Llama al método interno que tiene la lógica de reintentos
            batch_embeddings = self._embed_batch_with_retries(batch)
            all_embeddings.extend(batch_embeddings)
            
            # Rate Limiting simple: Pausa breve entre lotes para ser un buen ciudadano de la API
            if len(valid_texts) > self.batch_size:
                time.sleep(1) # Pausa de 1 segundo

        return all_embeddings

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=60), # Espera 2s, 4s, 8s... hasta 60s
        stop=stop_after_attempt(5), # Reintenta un máximo de 5 veces
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS), # Solo reintenta en errores específicos
        before_sleep=lambda retry_state: logger.warning(f"Error de API, reintentando... Intento {retry_state.attempt_number}, esperando {retry_state.next_action.sleep}s.")
    )
    def _embed_batch_with_retries(self, batch: List[str]) -> List[Optional[List[float]]]:
        """
        Método privado que realiza la llamada real a la API y está decorado
        con la lógica de reintentos de Tenacity.
        """
        try:
            # Para cada texto en el lote, hacer una llamada individual
            # Esto es necesario porque la API de Google no soporta lotes múltiples en una sola llamada
            embeddings = []
            for text in batch:
                response = genai.embed_content(
                    model=self.model_name,
                    content=text,
                    task_type="RETRIEVAL_DOCUMENT"
                )
                
                # La respuesta es {'embedding': [valores...]}
                if 'embedding' in response and response['embedding']:
                    embeddings.append(response['embedding'])
                else:
                    logger.warning(f"No se pudo obtener embedding para el texto: '{text[:50]}...'")
                    embeddings.append(None)
                    
            return embeddings
            
        except RETRYABLE_EXCEPTIONS as e:
            logger.error(f"Error reintentable de API en lote: {e}")
            raise # Vuelve a lanzar la excepción para que Tenacity la capture y reintente
        except Exception as e:
            # Manejo de errores específico y seguro. No captura excepciones genéricas.
            logger.critical(f"Error no recuperable en lote de embeddings: {e}. El modelo '{self.model_name}' podría ser inválido.")
            # Devuelve una respuesta consistente en caso de error no recuperable
            return [None] * len(batch)

