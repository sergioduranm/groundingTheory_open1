import google.generativeai as genai
import json
from typing import Dict, Any, List, Union, Optional
from pydantic import ValidationError
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

from models.data_models import CodingResult
from services.llm_service import LLMService
from utils.file_utils import extract_json_from_text

class CoderAgent:
    """
    Un agente de IA especializado en la codificación abierta de la Teoría Fundamentada.
    Este agente recibe un insight, lo formatea dentro de un prompt muy específico,
    y utiliza un modelo generativo para generar códigos conceptuales.
    """

    # PLANTILLA CORREGIDA:
    # Se han duplicado todas las llaves de los ejemplos JSON ( {{ y }} )
    # para que el método .format() de Python las ignore. La única llave
    # simple es la de nuestro marcador de posición {json_input}.
    PROMPT_TEMPLATE = """
# PROMPT DE CODI-ACCION: CODIFICACIÓN ABIERTA

<persona_y_mision>
Tu única función es ser un Analista de Datos Cualitativos. Tu especialidad es la Codificación Abierta de la Teoría Fundamentada.
Tu misión es identificar y nombrar las ACCIONES o PROCESOS en un fragmento de texto.
NO resumas. NO interpretes. SOLO codifica la acción, evitando repetir códigos muy similares.
</persona_y_mision>

<reglas_de_codificacion_inquebrantables>
### 1. Formato del Código: ¡OBLIGATORIO!
- **ESTRUCTURA EXACTA:** Cada código DEBE empezar con un verbo en gerundio (-ando, -endo, -iendo).
- **EJEMPLO:** `Buscando reconocimiento`, `Reduciendo la fricción`.
- **IMPORTANTE:** Si un código no empieza con gerundio, la respuesta es INCORRECTA.

### 2. Errores Críticos que DEBES Evitar:
- **🚫 NO uses temas o categorías:** Incorrecto: "salario bajo". Correcto: "Percibiendo inequidad salarial".
- **🚫 NO uses sentimientos aislados:** Incorrecto: "tristeza". Correcto: "Experimentando desmotivación".

### 3. Códigos "In Vivo":
- Si el texto contiene una frase literal muy potente, úsala.
- **Formato:** `[in vivo] "frase literal exacta"`.
- **ATENCIÓN AL ESCAPE:** Si la frase literal contiene comillas dobles ("), es OBLIGATORIO escaparlas con una doble barra invertida (`\\"`).
- **Ejemplo con escape:** `"[in vivo] \\"la frase textual con comillas va aquí\\""`.
</reglas_de_codificacion_inquebrantables>

<tarea_especifica_json>
Tu tarea es completar un objeto JSON. Te proporcionaré un JSON con las claves "id_fragmento" y "fragmento_original" ya rellenadas.
Tú NO DEBES modificar esos valores. Tu único trabajo es generar la lista de strings para la clave "codigos_abiertos", siguiendo las reglas de codificación.
</tarea_especifica_json>

<ejemplo_maestro>
<input_del_usuario>
```json
{{
  "id_fragmento": "ejemplo_01",
  "fragmento_original": "Mi jefa es de esas personas que te dice 'hazlo como creas', pero después, si no es como ella lo tenía en la cabeza, te cae la bronca. Al final, uno termina 'adivinando el futuro' para no meter la pata.",
  "codigos_abiertos": []
}}
```
</input_del_usuario>
<output_del_modelo>
```json
{{
  "id_fragmento": "ejemplo_01",
  "fragmento_original": "Mi jefa es de esas personas que te dice 'hazlo como creas', pero después, si no es como ella lo tenía en la cabeza, te cae la bronca. Al final, uno termina 'adivinando el futuro' para no meter la pata.",
  "codigos_abiertos": [
    "Navegando expectativas no declaradas",
    "Intentando prevenir críticas futuras",
    "[in vivo] \"adivinando el futuro\""
  ]
}}
```
</output_del_modelo>

<verificacion_final_interna>
VERIFICAR GERUNDIO: ¿Todos los códigos que he generado empiezan con un verbo en gerundio (o son [in vivo])?
VERIFICAR DATOS DE ENTRADA: ¿He copiado id_fragmento y fragmento_original exactamente sin modificarlos?
VERIFICAR FORMATO FINAL: ¿La salida que voy a producir es un único objeto JSON válido y completo?
</verificacion_final_interna>

<input_del_usuario>
```json
{json_input}
```
</input_del_usuario>
<output_del_modelo>
"""

    def __init__(self, llm_service: LLMService, prompt_template_path: str = 'prompts/open_coding.md'):
        """
        Inicializa el CoderAgent con sus dependencias.

        Args:
            llm_service: Una instancia de un servicio para interactuar con el LLM.
            prompt_template_path: La ruta al archivo de plantilla del prompt.
        """
        self.logger = logging.getLogger(__name__)
        self.llm_service = llm_service
        self.prompt_template_path = prompt_template_path
        self._prompt_template: Optional[str] = None # Para carga perezosa (lazy loading)

    def _load_prompt_template(self) -> str:
        """
        Carga la plantilla de prompt desde el archivo .md, usando un sistema de caché simple.
        """
        if self._prompt_template is None:
            try:
                with open(self.prompt_template_path, 'r', encoding='utf-8') as f:
                    self._prompt_template = f.read()
            except FileNotFoundError:
                self.logger.error(f"Archivo de plantilla de prompt no encontrado en: {self.prompt_template_path}")
                raise
        return self._prompt_template

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate_codes(self, insight: Dict[str, Any]) -> CodingResult:
        """
        Genera códigos para un único insight y devuelve un objeto validado.

        Args:
            insight: Un diccionario que representa un insight, debe contener 'id' y 'text'.

        Returns:
            Un objeto CodingResult validado.
        """
        # 1. Transformar el insight al formato esperado por el prompt.
        # El prompt espera 'id_fragmento' y 'fragmento_original'.
        insight_for_prompt = {
            "id_fragmento": insight.get("id"),
            "fragmento_original": insight.get("text"),
            "codigos_abiertos": []
        }
        json_input_str = json.dumps(insight_for_prompt, indent=2, ensure_ascii=False)

        # 2. Cargar la plantilla y rellenarla con el string JSON.
        prompt_template = self._load_prompt_template()
        final_prompt = prompt_template.format(json_input=json_input_str)
        
        try:
            # 3. Llamar a la API a través del servicio centralizado.
            llm_response_text = self.llm_service.invoke_llm(final_prompt)
            
            # 4. Usar nuestra utilidad experta para extraer y parsear el JSON de la respuesta.
            if not llm_response_text:
                raise ValueError("La respuesta del LLM estaba vacía.")

            json_output = extract_json_from_text(llm_response_text)
            
            if not json_output:
                # Si la extracción falla, usamos print() para una depuración a prueba de fallos.
                print("\n" + "="*80)
                print(f"DEBUG: REPORTE DE FALLO DE PARSEO PARA INSIGHT ID: {insight.get('id')}")
                print("="*80)
                print("\n[PROMPT ENVIADO AL MODELO]\n")
                print(final_prompt)
                print("\n" + "-"*80 + "\n")
                print("[RESPUESTA CRUDA RECIBIDA DEL MODELO]\n")
                print(llm_response_text)
                print("\n" + "="*80)
                print("FIN DEL REPORTE DE DEPURACIÓN")
                print("="*80 + "\n")
                raise ValueError("No se pudo extraer un JSON válido de la respuesta del LLM.")

            # 5. Validar la estructura del JSON con Pydantic.
            # El LLM debería devolver el objeto completo, incluyendo id_fragmento y fragmento_original.
            validated_output = CodingResult.model_validate(json_output)
            return validated_output

        except (ValueError, ValidationError) as e:
            self.logger.error(f"Error fatal de validación/parseo para el insight {insight.get('id')}: {e}.")
            # Relanzamos la excepción para detener la ejecución (lógica Fail-Fast).
            # El reporte de depuración con print() ya se mostró antes de este punto.
            raise e
            
        except Exception as e:
            self.logger.error(f"Error inesperado al procesar el insight {insight.get('id')}: {e}")
            raise e
