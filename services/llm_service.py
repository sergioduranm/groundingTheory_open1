# services/llm_service.py
import os
import logging
import litellm
from openai import APIError
from typing import Union, Optional

class LLMService:
    """
    Gestiona las interacciones con APIs de LLM a través de liteLLM.
    Permite cambiar de proveedor (Google, OpenAI, Anthropic, etc.) de forma transparente.
    """
    def __init__(self, model: str = "gemini/gemini-2.5-flash", temperature: float = 0.4):
        """
        Configura el servicio de LLM.

        Args:
            model: El nombre del modelo por defecto a utilizar (ej. "gemini/gemini-2.5-flash").
                   liteLLM usará la variable de entorno correspondiente.
            temperature: La temperatura para la generación, controla la aleatoriedad.
        """
        self.logger = logging.getLogger(__name__)
        self.model = model
        self.temperature = temperature
        self.logger.info(f"LLMService inicializado con el modelo por defecto: {model} a través de liteLLM")

    def invoke_llm(self, prompt: str, model: Optional[str] = None) -> Union[str, None]:
        """
        Envía un prompt a un LLM a través de liteLLM y devuelve la respuesta.
        Puede usar un modelo específico para esta llamada, de lo contrario, utiliza el modelo predeterminado de la instancia.

        Args:
            prompt: El prompt para enviar al modelo.
            model (Optional[str]): Un nombre de modelo específico para usar en esta invocación.

        Returns:
            El contenido de texto de la respuesta del LLM, o None si ocurre un error.
        """
        model_to_use = model or self.model
        self.logger.debug(f"Invocando al modelo {model_to_use} vía liteLLM...")
        try:
            messages = [{"role": "user", "content": prompt}]
            
            # Obtener API key explícitamente para asegurar autenticación
            api_key = os.getenv("GOOGLE_API_KEY")
            
            response = litellm.completion(
                model=model_to_use,
                messages=messages,
                temperature=self.temperature,
                api_key=api_key,
            )
            
            if not response.choices:
                self.logger.warning("La respuesta del LLM no contiene 'choices'. La respuesta puede estar vacía o bloqueada.")
                return None

            choice = response.choices[0]
            if choice.finish_reason != "stop":
                self.logger.warning(
                    f"La generación del LLM no finalizó normalmente. Razón: {choice.finish_reason}. "
                    "Esto puede indicar que el contenido fue bloqueado por seguridad o por otras razones."
                )
                return None

            self.logger.debug("Respuesta recibida de liteLLM exitosamente.")
            return choice.message.content
            
        except APIError as e:
            self.logger.error(f"Error de API con el proveedor de LLM: {e}")
        except Exception as e:
            self.logger.error(f"Un error inesperado ocurrió al invocar el LLM ({model_to_use}): {e}")
            
        return None 