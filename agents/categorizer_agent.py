# agents/categorizer_agent.py

import json
import os
import logging
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv
from pydantic import ValidationError

from utils.file_utils import load_json_file, save_json_file
from models.data_models import Codebook, Category, CategorizationResult

class CategorizerAgent:
    """
    Agente encargado de agrupar códigos abiertos en categorías conceptuales
    utilizando un LLM y directrices estratégicas.
    
    Este agente implementa la primera fase de la codificación axial en Grounded Theory,
    adoptando un enfoque híbrido que combina la guía estratégica del investigador
    con las capacidades de comparación constante del LLM.
    """

    def __init__(self, 
                 config_path: str = 'config_proyecto.json',
                 codebook_path: str = 'data/codebook.json',
                 prompt_template_path: str = 'prompts/categorize_code.md',
                 output_path: str = 'data/categorias.json',
                 model_name: str = "models/gemini-2.5-flash-lite-preview-06-17",
                 batch_size: int = 30):
        """
        Inicializa el agente con dependencias inyectadas y configuración flexible.
        
        Args:
            config_path: Ruta al archivo de configuración del proyecto
            codebook_path: Ruta al codebook con códigos unificados
            prompt_template_path: Ruta al template de prompt
            output_path: Ruta donde guardar las categorías resultantes
            model_name: Nombre del modelo de Google Generative AI
            batch_size: Tamaño de los lotes de códigos a procesar
        """
        # Configurar logging
        self.logger = logging.getLogger(__name__)
        
        # Configurar API de Google
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("No se encontró la GOOGLE_API_KEY en el archivo .env")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
        # Configurar rutas de archivos
        self.config_path = config_path
        self.codebook_path = codebook_path
        self.prompt_template_path = prompt_template_path
        self.output_path = output_path
        self.batch_size = batch_size
        
        self._prompt_template_cache: Optional[str] = None
        self.logger.info("CategorizerAgent inicializado correctamente.")

    def _load_prompt_template(self) -> str:
        """
        Carga la plantilla de prompt desde el archivo .md, usando caché.
        """
        if self._prompt_template_cache is None:
            try:
                with open(self.prompt_template_path, 'r', encoding='utf-8') as f:
                    self._prompt_template_cache = f.read()
            except FileNotFoundError:
                self.logger.error(f"Template de prompt no encontrado: {self.prompt_template_path}")
                raise
        return self._prompt_template_cache

    def _prepare_prompt(self, codes_to_categorize: List[Dict[str, Any]], known_categories: List[Category]) -> str:
        """
        Prepara el prompt final inyectando un "mapa de significados" optimizado
        y las categorías ya conocidas para mantener la consistencia.
        """
        self.logger.info("Preparando prompt optimizado...")
        
        # Cargar datos necesarios usando las utilidades y validando con Pydantic
        config_data = load_json_file(self.config_path)
        codebook_data = load_json_file(self.codebook_path)
        prompt_template = self._load_prompt_template()

        try:
            codebook = Codebook.model_validate(codebook_data)
        except ValidationError as e:
            self.logger.error(f"El codebook en {self.codebook_path} tiene un formato inválido: {e}")
            raise

        id_to_label_map = {code.id: code.label for code in codebook.codes}
        
        research_questions = config_data.get("research_questions", [])
        
        if known_categories:
            seed_categories_for_prompt = [
                {"category_name": cat.category_name, "description": cat.description or ""}
                for cat in known_categories
            ]
        else:
            seed_categories_for_prompt = config_data.get("seed_categories", [])
        
        research_questions_text = "\n".join(f"- {q}" for q in research_questions)
        seed_categories_json = json.dumps(seed_categories_for_prompt, indent=2, ensure_ascii=False)
        codebook_map_json = json.dumps(id_to_label_map, indent=2, ensure_ascii=False)
        codes_to_categorize_json = json.dumps(codes_to_categorize, indent=2, ensure_ascii=False)
        
        final_prompt = prompt_template.format(
            research_questions=research_questions_text,
            seed_categories_json=seed_categories_json,
            codebook_map_json=codebook_map_json,
            codes_to_categorize_json=codes_to_categorize_json
        )
        
        self.logger.info("Prompt optimizado preparado exitosamente.")
        return final_prompt

    def _invoke_llm(self, prompt: str) -> List[CategorizationResult]:
        """
        Invoca al LLM con el prompt final y utiliza el 'Modo JSON' nativo,
        validando la respuesta con Pydantic para máxima fiabilidad.
        """
        self.logger.info("Invocando LLM para categorización usando Modo JSON...")
        
        try:
            generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
            response = self.model.generate_content(prompt, generation_config=generation_config)
            
            self.logger.debug(f"Respuesta raw del LLM: {repr(response.text[:200])}...")
            
            response_data = json.loads(response.text)
            
            # Validación con Pydantic: potente, declarativa y en una línea.
            validated_results = [CategorizationResult.model_validate(item) for item in response_data]
            
            self.logger.info(f"LLM procesó y validó exitosamente {len(validated_results)} categorías.")
            return validated_results
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Respuesta del LLM no es JSON válido. Error: {e}. Respuesta: {repr(response.text)}")
            raise ValueError(f"Respuesta del LLM no es JSON válido: {e}")
        except ValidationError as e:
            self.logger.error(f"La respuesta del LLM no cumple con el modelo CategorizationResult. Error: {e}. Respuesta: {repr(response.text)}")
            raise ValueError(f"La respuesta del LLM tiene un formato inesperado: {e}")
        except Exception as e:
            self.logger.error(f"Error en invocación del LLM: {e}")
            if 'response' in locals():
                self.logger.error(f"Respuesta que causó el error: {repr(response.text)}")
            raise

    def _update_known_categories(self,
                                 known_categories: List[Category],
                                 new_batch_results: List[CategorizationResult]) -> List[Category]:
        """
        Fusiona inteligentemente los resultados de un nuevo lote con las categorías ya conocidas.
        """
        self.logger.debug(f"Iniciando fusión. {len(known_categories)} categorías conocidas, {len(new_batch_results)} resultados nuevos.")
        
        category_map = {cat.category_name: cat for cat in known_categories}

        for new_cat_result in new_batch_results:
            if new_cat_result.category_name in category_map:
                # La categoría ya existe, añadir nuevos códigos si no están ya
                existing_cat = category_map[new_cat_result.category_name]
                existing_code_ids = {assign.code_id for assign in existing_cat.code_assignments}
                
                for new_assignment in new_cat_result.code_assignments:
                    if new_assignment.code_id not in existing_code_ids:
                        existing_cat.code_assignments.append(new_assignment)
            else:
                # Es una categoría completamente nueva
                # La creamos usando nuestro modelo `Category`
                new_category = Category(
                    category_id=f"cat_{len(category_map) + 1}", # Generar un ID simple
                    category_name=new_cat_result.category_name,
                    description=new_cat_result.description,
                    code_assignments=new_cat_result.code_assignments
                )
                category_map[new_cat_result.category_name] = new_category

        return list(category_map.values())

    def _save_output(self, categorized_data: List[Category]) -> None:
        """
        Guarda la lista final de categorías en un archivo JSON.
        """
        self.logger.info(f"Guardando {len(categorized_data)} categorías en {self.output_path}")
        # Convertimos los objetos Pydantic a una lista de diccionarios para guardarlos
        data_to_save = [cat.model_dump() for cat in categorized_data]
        try:
            save_json_file(self.output_path, data_to_save)
        except Exception as e:
            self.logger.error(f"No se pudo guardar el archivo de salida: {e}")
            raise

    def categorize_codes(self, codes_to_categorize: Optional[List[Dict[str, Any]]] = None) -> List[Category]:
        """
        Orquesta el proceso de categorización de códigos en lotes.
        """
        if codes_to_categorize is None:
            self.logger.info("No se proporcionaron códigos. Cargando desde el codebook...")
            codebook_data = load_json_file(self.codebook_path)
            try:
                codebook = Codebook.model_validate(codebook_data)
                codes_to_categorize = [{"code_id": code.id} for code in codebook.codes]
            except ValidationError as e:
                self.logger.error(f"Formato de codebook inválido: {e}")
                return []
        
        self.logger.info(f"Iniciando la categorización para {len(codes_to_categorize)} códigos en lotes de {self.batch_size}.")
        
        known_categories: List[Category] = []
        
        for i in range(0, len(codes_to_categorize), self.batch_size):
            batch = codes_to_categorize[i:i + self.batch_size]
            self.logger.info(f"Procesando lote {i//self.batch_size + 1}...")
            
            prompt = self._prepare_prompt(batch, known_categories)
            
            try:
                new_batch_results = self._invoke_llm(prompt)
                known_categories = self._update_known_categories(known_categories, new_batch_results)
            except Exception as e:
                self.logger.error(f"Fallo al procesar el lote. Saltando al siguiente. Error: {e}")
                continue # Opcional: decidir si parar o continuar
        
        self.logger.info("Todos los lotes han sido procesados.")
        return known_categories

    def run(self, codes_to_categorize: Optional[List[Dict[str, Any]]] = None) -> None:
        """Punto de entrada principal para ejecutar el agente."""
        self.logger.info("--- Iniciando CategorizerAgent ---")
        try:
            final_categories = self.categorize_codes(codes_to_categorize)
            if final_categories:
                self._save_output(final_categories)
                self.logger.info(f"--- Proceso completado. {len(final_categories)} categorías guardadas. ---")
            else:
                self.logger.warning("--- Proceso completado, pero no se generaron categorías. ---")
        except Exception as e:
            self.logger.error(f"El agente falló de forma inesperada. Error: {e}", exc_info=True)
            raise


if __name__ == '__main__':
    """
    Permite ejecutar el agente directamente desde la terminal para pruebas y desarrollo.
    """
    import logging
    
    # Configurar logging para ejecución standalone
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        agent = CategorizerAgent()
        agent.run()
    except Exception as e:
        print(f"❌ Error: {e}")