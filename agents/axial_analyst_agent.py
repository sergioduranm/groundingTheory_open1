# agents/axial_analyst_agent.py

import logging
from typing import List, Dict, Any, Iterator
from pydantic import ValidationError
import json
from dotenv import load_dotenv

# Asumimos que los servicios y utilidades ya existen y son importables.
# Nota: Necesitaremos añadir una función 'load_jsonl_file' y 'save_jsonl_file' a nuestras utilidades.
from services.llm_service import LLMService 
from utils.file_utils import load_json_file, load_jsonl_file, append_to_jsonl_file, extract_json_from_text
from models.data_models import Category, Insight, AxialAnalysisOutput, CodeAssignment

class AxialAnalystAgent:
    """
    Agente encargado de realizar el análisis axial para cada categoría conceptual.
    Toma una categoría, recupera su evidencia textual de forma eficiente usando un
    índice invertido y utiliza un LLM para rellenar un modelo paradigmático.
    """

    def __init__(self,
                 llm_service: LLMService,
                 categories_path: str = 'data/categorias.json',
                 insights_path: str = 'data/analysis_results.jsonl',
                 prompt_template_path: str = 'prompts/perform_axial_analysis.md',
                 output_path: str = 'data/analisis_axial.jsonl'):
        """
        Inicializa el agente con sus dependencias y rutas de archivos.

        Args:
            llm_service: Instancia del servicio para interactuar con el LLM.
            categories_path: Ruta al archivo con las categorías a analizar.
            insights_path: Ruta al archivo que mapea insights con códigos (la evidencia).
            prompt_template_path: Ruta a la plantilla de prompt para el análisis axial.
            output_path: Ruta donde se guardará el análisis axial (formato JSONL).
        """
        self.logger = logging.getLogger(__name__)
        self.llm_service = llm_service
        self.categories_path = categories_path
        self.insights_path = insights_path
        self.prompt_template_path = prompt_template_path
        self.output_path = output_path
        self._prompt_template = None # Para cachear la plantilla de prompt
        self.logger.info("AxialAnalystAgent inicializado correctamente.")

    def _get_evidence_for_category(self, 
                                   category: Category, 
                                   evidence_map: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, str]]:
        """
        Recupera los fragmentos de texto originales (evidencia) para una categoría dada,
        utilizando un índice invertido pre-calculado para máxima eficiencia.

        Args:
            category: El objeto de la categoría (validado con Pydantic) que se está analizando.
            evidence_map: El índice invertido (code_id -> lista de fragmentos de evidencia).

        Returns:
            Una lista de diccionarios de evidencia únicos para esa categoría.
        """
        # Usamos un diccionario para las evidencias para que no se repitan
        # si un mismo fragmento está asociado a múltiples códigos de la categoría.
        unique_evidence_fragments: Dict[str, Dict[str, str]] = {} 
        
        category_code_ids = {assignment.code_id for assignment in category.code_assignments}

        for code_id in category_code_ids:
            # Búsqueda instantánea en el índice
            evidences = evidence_map.get(code_id, [])
            for evidence in evidences:
                # La clave es el ID del fragmento para garantizar la unicidad.
                # El valor es el propio objeto de evidencia.
                unique_evidence_fragments[evidence['id_fragmento']] = evidence
            
        self.logger.debug(f"Recuperados {len(unique_evidence_fragments)} fragmentos de evidencia para '{category.category_name}'.")
        
        # Devolvemos la lista de diccionarios de evidencia
        return list(unique_evidence_fragments.values())

    def _prepare_axial_prompt(self, category: Category, evidence_list: List[Dict[str, str]]) -> str:
        """
        Prepara el prompt para el análisis axial de una categoría, inyectando
        la definición de la categoría y la evidencia textual en formato JSON.
        """
        self.logger.debug(f"Preparando prompt para la categoría '{category.category_name}'...")
        
        # Cachea la plantilla para evitar leer el archivo repetidamente
        if self._prompt_template is None:
            try:
                with open(self.prompt_template_path, 'r', encoding='utf-8') as f:
                    self._prompt_template = f.read()
            except FileNotFoundError:
                self.logger.error(f"No se pudo encontrar el archivo de plantilla de prompt: {self.prompt_template_path}")
                raise
        
        # Serializa la lista de evidencia a un string en formato JSON.
        evidence_json_string = json.dumps(evidence_list, indent=2, ensure_ascii=False)
        
        # Rellena la plantilla
        prompt = self._prompt_template.format(
            category_name=category.category_name,
            category_description=category.description or "No hay descripción disponible.",
            evidence_json=evidence_json_string
        )
        
        return prompt

    def _build_evidence_index(self, insights_iterator: Iterator[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Construye un índice invertido desde códigos a fragmentos de evidencia.
        """
        self.logger.info("Construyendo índice invertido de evidencia para una recuperación eficiente...")
        code_to_evidence_map = {}
        for i, insight_data in enumerate(insights_iterator):
            try:
                insight = Insight.model_validate(insight_data)
            except ValidationError as e:
                self.logger.warning(f"Error de validación en insight #{i+1}, se saltará. Error: {e}")
                continue
            
            for code_id in insight.unified_code_ids:
                if code_id not in code_to_evidence_map:
                    code_to_evidence_map[code_id] = []
                
                # Usamos los nombres de campo correctos del modelo Insight
                code_to_evidence_map[code_id].append({
                    "id_fragmento": insight.id_fragmento,
                    "fragmento_original": insight.fragmento_original
                })
        self.logger.info(f"Índice construido. {len(code_to_evidence_map)} códigos únicos mapeados a evidencia.")
        return code_to_evidence_map

    def _analyze_category(self, category: Category, code_to_evidence_map: Dict[str, List[Dict[str, Any]]]):
        """
        Realiza el análisis axial completo para una única categoría.
        """
        # a. Recuperar evidencia
        evidence_list = self._get_evidence_for_category(category, code_to_evidence_map)
        if not evidence_list:
            self.logger.warning(f"No se encontró evidencia para la categoría '{category.category_name}'. Saltando.")
            return

        # b. Preparar el prompt
        prompt = self._prepare_axial_prompt(category, evidence_list)
        
        # c. Invocar al LLM y extraer JSON
        self.logger.info(f"Invocando LLM para '{category.category_name}'...")
        llm_response_text = self.llm_service.invoke_llm(prompt)
        axial_result_raw = extract_json_from_text(llm_response_text)

        if not axial_result_raw:
            self.logger.error(f"No se pudo extraer un JSON válido de la respuesta del LLM para '{category.category_name}'. Se saltará.")
            return
        
        # Valida la respuesta del LLM con el nuevo modelo
        try:
            axial_result = AxialAnalysisOutput.model_validate(axial_result_raw)
        except ValidationError as e:
            self.logger.error(f"Error de validación en la respuesta del LLM para la categoría '{category.category_name}'. Se saltará. Error: {e}")
            return # Salta a la siguiente categoría

        # d. Guardar el resultado
        analysis_to_save = {
            'category_name': category.category_name,
            'category_id': category.category_id,
            'analysis': axial_result.model_dump()
        }
        append_to_jsonl_file(self.output_path, analysis_to_save)
        self.logger.info(f"Análisis para '{category.category_name}' guardado en {self.output_path}")

    def run(self):
        """
        Orquesta el proceso de análisis axial para TODAS las categorías.
        """
        self.logger.info("Iniciando la ejecución del AxialAnalystAgent...")
        try:
            # --- FASE 1: CARGAR Y UNIFICAR DATOS ---
            raw_categories = load_json_file(self.categories_path)
            
            # Unificar categorías duplicadas para asegurar un análisis completo
            merged_categories: Dict[str, Category] = {}
            for cat_data in raw_categories:
                try:
                    category = Category.model_validate(cat_data)
                    if category.category_id not in merged_categories:
                        merged_categories[category.category_id] = category
                    else:
                        # Fusionar las asignaciones de códigos de la categoría duplicada
                        existing_codes = {assign.code_id for assign in merged_categories[category.category_id].code_assignments}
                        new_codes = {assign.code_id for assign in category.code_assignments}
                        
                        # Añadir solo los códigos que no existían
                        for code_id in new_codes:
                            if code_id not in existing_codes:
                                merged_categories[category.category_id].code_assignments.append(CodeAssignment(code_id=code_id))

                except ValidationError as e:
                    self.logger.warning(f"Error de validación en un objeto de categoría, se saltará. Error: {e}")
                    continue

            categories_to_analyze = list(merged_categories.values())
            self.logger.info(f"{len(raw_categories)} categorías cargadas, unificadas en {len(categories_to_analyze)} categorías únicas para análisis.")

            insights_iterator = load_jsonl_file(self.insights_path)
            code_to_evidence_map = self._build_evidence_index(insights_iterator)
            
            # --- FASE 2: ANÁLISIS ITERATIVO POR CATEGORÍA ---
            self.logger.info(f"Iniciando análisis para {len(categories_to_analyze)} categorías únicas.")
            for i, category in enumerate(categories_to_analyze):
                self.logger.info(f"Procesando categoría {i+1}/{len(categories_to_analyze)}: '{category.category_name}'")
                self._analyze_category(category, code_to_evidence_map)

            # --- FASE 3: COMPLETADO ---
            self.logger.info("Análisis de todas las categorías completado.")
            self.logger.info(f"Proceso completado. Análisis axial guardado en {self.output_path}")

        except Exception as e:
            self.logger.error(f"❌ Error fatal durante la ejecución del AxialAnalystAgent: {e}", exc_info=True)
            raise


if __name__ == '__main__':
    """
    Este bloque permite ejecutar el agente directamente desde la terminal para pruebas y desarrollo.
    """
    import logging

    # Carga las variables de entorno desde un archivo .env en la raíz del proyecto
    load_dotenv()

    # Configurar logging para ejecución standalone
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Creamos una instancia del servicio LLM real.
        # Asegúrate de tener GOOGLE_API_KEY en tu archivo .env
        llm_service = LLMService()
        
        # Creamos una instancia del agente, inyectando el servicio real
        agent = AxialAnalystAgent(llm_service=llm_service)
        
        # Ejecutamos el agente
        agent.run()
        
    except FileNotFoundError as e:
        print(f"\n❌ ERROR DE ARCHIVO: {e}")
        print("Asegúrate de que los archivos de datos de entrada ('categorias.json', 'analysis_results.jsonl') existen.")
    except (ValueError, ImportError) as e:
        # Captura el error si la API key no está o si falta una librería
        print(f"\n❌ ERROR DE CONFIGURACIÓN: {e}")
        print("Asegúrate de tener un archivo .env con tu GOOGLE_API_KEY y de haber instalado los requerimientos.")
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {e}")