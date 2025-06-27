import google.generativeai as genai
import json
from typing import Dict, Any, List, Union
from pydantic import ValidationError

from models.data_models import CodingResult
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

    def __init__(self, model_name: str = "models/gemini-2.5-flash-lite-preview-06-17"):
        """
        Inicializa el CoderAgent.
        - Configura el modelo generativo de Google.
        - Se asume que la API Key está configurada en el entorno (p.ej. con `genai.configure(api_key="...")`).
        """
        self.model = genai.GenerativeModel(model_name)
        print("🤖 CoderAgent inicializado con el modelo:", model_name)

    def generate_codes(self, insight: Dict[str, Any]) -> CodingResult:
        """
        Genera códigos para un único insight y devuelve un objeto validado.

        Args:
            insight: Un diccionario que representa un insight, debe contener 'id' y 'text'.

        Returns:
            Un objeto CodingResult validado, que incluye el resultado o un mensaje de error.
        """
        # 1. Preparar el JSON de entrada que espera la plantilla del prompt.
        input_data_for_prompt = {
            "id_fragmento": insight.get("id"),
            "fragmento_original": insight.get("text"),
            "codigos_abiertos": []
        }
        
        json_input_str = json.dumps(input_data_for_prompt, indent=2, ensure_ascii=False)

        # 2. Rellenar la plantilla principal con el string JSON que acabamos de crear.
        final_prompt = self.PROMPT_TEMPLATE.format(json_input=json_input_str)
        
        try:
            # 3. Llamar a la API del modelo generativo.
            response = self.model.generate_content(final_prompt)
            
            # 4. Usar nuestra utilidad experta para extraer y parsear el JSON de la respuesta.
            parsed_output = extract_json_from_text(response.text)

            if not parsed_output:
                raise json.JSONDecodeError("La utilidad no pudo extraer un JSON válido de la respuesta.", response.text, 0)
            
            # 5. Validar la salida con Pydantic para asegurar la integridad de la estructura.
            validated_output = CodingResult.model_validate(parsed_output)
            return validated_output

        except (ValidationError, json.JSONDecodeError) as e:
            print(f"Error de validación o parseo para el insight {insight.get('id')}: {e}")
            return CodingResult(
                id_fragmento=insight.get("id"),
                fragmento_original=insight.get("text"),
                codigos_abiertos=[],
                error=f"Fallo de validación/parseo: {e}"
            )
        except Exception as e:
            print(f"Error genérico al procesar el insight {insight.get('id')}: {e}")
            return CodingResult(
                id_fragmento=insight.get("id"),
                fragmento_original=insight.get("text"),
                codigos_abiertos=[],
                error=str(e)
            )
