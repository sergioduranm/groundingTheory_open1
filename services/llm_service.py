# services/llm_service.py
import os
import logging
import litellm
from openai import APIError

class LLMService:
    """
    Gestiona las interacciones con APIs de LLM a través de liteLLM.
    Permite cambiar de proveedor (Google, OpenAI, Anthropic, etc.) de forma transparente.
    """
    def __init__(self, model: str = "gpt-4.1-nano-2025-04-14", temperature: float = 0.4):
        """
        Configura el servicio de LLM.

        Args:
            model: El nombre del modelo a utilizar (ej. "gemini/gemini-1.5-pro-latest", "gpt-4o").
                   liteLLM usará la variable de entorno correspondiente (ej. GOOGLE_API_KEY).
            temperature: La temperatura para la generación, controla la aleatoriedad.
        """
        self.logger = logging.getLogger(__name__)
        self.model = model
        self.temperature = temperature
        # No es necesaria la configuración de API key aquí, liteLLM la maneja automáticamente.
        self.logger.info(f"LLMService inicializado con el modelo: {model} a través de liteLLM")

    def invoke_llm(self, prompt: str) -> str | None:
        """
        Envía un prompt a un LLM a través de liteLLM y devuelve la respuesta.

        Args:
            prompt: El prompt para enviar al modelo.

        Returns:
            El contenido de texto de la respuesta del LLM, o None si ocurre un error.
        """
        self.logger.debug(f"Invocando al modelo {self.model} vía liteLLM...")
        try:
            messages = [{"role": "user", "content": prompt}]
            
            response = litellm.completion(
                model=self.model,
                messages=messages,
                temperature=self.temperature
            )
            
            # Comprobación de la razón de finalización para mantener la seguridad y la robustez.
            # liteLLM estandariza esta parte de la respuesta.
            if not response.choices:
                self.logger.warning("La respuesta del LLM no contiene 'choices'. La respuesta puede estar vacía o bloqueada.")
                return None

            choice = response.choices[0]
            if choice.finish_reason != "stop":
                self.logger.warning(
                    f"La generación del LLM no finalizó normally. Razón: {choice.finish_reason}. "
                    "Esto puede indicar que el contenido fue bloqueado por seguridad o por otras razones."
                )
                return None

            self.logger.debug("Respuesta recibida de liteLLM exitosamente.")
            return choice.message.content
            
        except APIError as e:
            self.logger.error(f"Error de API con el proveedor de LLM: {e}")
        except Exception as e:
            self.logger.error(f"Un error inesperado ocurrió al invocar el LLM: {e}")
            
        return None 