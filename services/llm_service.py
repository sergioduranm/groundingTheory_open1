# services/llm_service.py
import os
import logging
import google.generativeai as genai
from google.api_core.exceptions import GoogleAPIError

class LLMService:
    """
    Gestiona las interacciones con la API de Google Gemini.
    Carga la clave de API desde variables de entorno y maneja la comunicación.
    """
    def __init__(self, model: str = "gemini-1.5-pro-latest", temperature: float = 0.1):
        """
        Configura el SDK de Google Gemini.

        Args:
            model: El nombre del modelo a utilizar (ej. "gemini-1.5-pro-latest").
            temperature: La temperatura para la generación, controla la aleatoriedad.
        
        Raises:
            ValueError: Si la variable de entorno GOOGLE_API_KEY no está configurada.
        """
        self.logger = logging.getLogger(__name__)
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            self.logger.error("La variable de entorno GOOGLE_API_KEY no está configurada.")
            raise ValueError("Debes configurar la variable de entorno GOOGLE_API_KEY.")
            
        genai.configure(api_key=api_key)
        
        self.generation_config = genai.GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json",
        )
        self.model = genai.GenerativeModel(
            model_name=model,
            generation_config=self.generation_config
        )
        self.logger.info(f"LLMService inicializado con el modelo de Google: {model}")

    def invoke_llm(self, prompt: str) -> str | None:
        """
        Envía un prompt a la API de Gemini y devuelve la respuesta.

        Args:
            prompt: El prompt para enviar al modelo.

        Returns:
            El contenido de texto de la respuesta del LLM, o None si ocurre un error.
        """
        self.logger.debug(f"Invocando al modelo {self.model.model_name}...")
        try:
            response = self.model.generate_content(prompt)
            self.logger.debug("Respuesta recibida de Gemini exitosamente.")
            return response.text
            
        except GoogleAPIError as e:
            self.logger.error(f"Error de API con Google: {e}")
        except Exception as e:
            self.logger.error(f"Un error inesperado ocurrió al invocar el LLM de Google: {e}")
            
        return None 