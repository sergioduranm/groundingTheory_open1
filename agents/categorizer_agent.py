# agents/categorizer_agent.py

import json
import os
import logging
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv

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
                 batch_size: int = 5):
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
        
        self.logger.info("CategorizerAgent inicializado correctamente.")

    def _load_json_file(self, file_path: str) -> Dict[str, Any]:
        """
        Carga un archivo JSON de forma segura con manejo de errores.
        
        Args:
            file_path: Ruta al archivo JSON
            
        Returns:
            Contenido del archivo como diccionario
            
        Raises:
            FileNotFoundError: Si el archivo no existe
            json.JSONDecodeError: Si el archivo no es JSON válido
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Archivo no encontrado: {file_path}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Error al parsear JSON en {file_path}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error inesperado al cargar {file_path}: {e}")
            raise

    def _load_prompt_template(self) -> str:
        """
        Carga la plantilla de prompt desde el archivo .md.
        
        Returns:
            Contenido del template como string
            
        Raises:
            FileNotFoundError: Si el archivo template no existe
        """
        try:
            with open(self.prompt_template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            self.logger.error(f"Template de prompt no encontrado: {self.prompt_template_path}")
            raise
        except Exception as e:
            self.logger.error(f"Error al cargar template: {e}")
            raise

    def _prepare_prompt(self, codes_to_categorize: List[Dict[str, Any]], known_categories: List[Dict[str, Any]]) -> str:
        """
        Prepara el prompt final inyectando un "mapa de significados" optimizado
        y las categorías ya conocidas para mantener la consistencia.
        
        Args:
            codes_to_categorize: Lista de códigos a categorizar para el lote actual
            known_categories: Lista de categorías ya identificadas en lotes anteriores
            
        Returns:
            Prompt final listo para enviar al LLM
        """
        self.logger.info("Preparando prompt optimizado...")
        
        # Cargar datos necesarios
        config_data = self._load_json_file(self.config_path)
        full_codebook_data = self._load_json_file(self.codebook_path)
        prompt_template = self._load_prompt_template()

        # --- OPTIMIZACIÓN CLAVE ---
        # Crear un mapa de significados (id -> label) en lugar de usar el codebook completo
        # Esto reduce drásticamente el tamaño del prompt eliminando embeddings y metadatos innecesarios
        codes_list = full_codebook_data.get("codes", [])
        id_to_label_map = {code['id']: code['label'] for code in codes_list}
        
        # Extraer datos específicos del config
        research_questions = config_data.get("research_questions", [])
        
        # Usar las categorías conocidas (memoria) si existen, sino, las iniciales del config
        if known_categories:
            # Formatear para el prompt, solo se necesita nombre y descripción
            seed_categories_for_prompt = [
                {"category_name": cat["category_name"], "description": cat.get("description", "")}
                for cat in known_categories
            ]
        else:
            seed_categories_for_prompt = config_data.get("seed_categories", [])
        
        # Formatear datos para el prompt
        research_questions_text = "\n".join(f"- {q}" for q in research_questions)
        seed_categories_json = json.dumps(seed_categories_for_prompt, indent=2, ensure_ascii=False)
        # Inyectamos el mapa optimizado, no el codebook completo
        codebook_map_json = json.dumps(id_to_label_map, indent=2, ensure_ascii=False)
        codes_to_categorize_json = json.dumps(codes_to_categorize, indent=2, ensure_ascii=False)
        
        # Inyectar variables en el template
        final_prompt = prompt_template.format(
            research_questions=research_questions_text,
            seed_categories_json=seed_categories_json,
            codebook_map_json=codebook_map_json,
            codes_to_categorize_json=codes_to_categorize_json
        )
        
        self.logger.info("Prompt optimizado preparado exitosamente.")
        return final_prompt

    def _invoke_llm(self, prompt: str) -> List[Dict[str, Any]]:
        """
        Invoca al LLM con el prompt final y utiliza el 'Modo JSON' nativo de la API 
        para garantizar una salida fiable y directamente parseable.
        
        Args:
            prompt: Prompt completo para enviar al LLM
            
        Returns:
            Lista de categorías con códigos asignados
            
        Raises:
            Exception: Si falla la invocación del LLM o la respuesta no es JSON válido
        """
        self.logger.info("Invocando LLM para categorización usando Modo JSON...")
        
        try:
            # Configura la llamada para que la respuesta sea obligatoriamente JSON
            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
            
            # Realiza la llamada al modelo
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Debugging: log la respuesta raw para diagnosticar problemas
            self.logger.debug(f"Respuesta raw del LLM: {repr(response.text[:200])}...")
            
            # Con el modo JSON, response.text debería ser directamente un string JSON válido
            response_text = response.text.strip()
            
            # Si aún viene con bloques de código, limpiarlos como fallback
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
            
            categorized_result = json.loads(response_text)
            
            # Validar la estructura de más alto nivel
            if not isinstance(categorized_result, list):
                raise ValueError("La respuesta del LLM, aunque es JSON, no es una lista como se esperaba.")
            
            # Validar que cada elemento de la lista tenga la estructura esperada
            for i, category in enumerate(categorized_result):
                if not isinstance(category, dict):
                    raise ValueError(f"El elemento {i} no es un diccionario: {type(category)}")
                
                # La respuesta del LLM debe tener 'code_assignments'.
                # Nos aseguramos que exista, aunque sea una lista vacía.
                category.setdefault('code_assignments', [])

                required_fields = ["category_name", "is_new", "description", "code_assignments"]
                missing_fields = [field for field in required_fields if field not in category]

                if missing_fields:
                    raise ValueError(f"El elemento {i} no tiene los campos requeridos: {', '.join(missing_fields)}")

            self.logger.info(f"LLM procesó exitosamente {len(categorized_result)} categorías.")
            return categorized_result
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Error al parsear JSON. Error: {e}")
            self.logger.error(f"Respuesta completa del LLM: {repr(response.text)}")
            raise ValueError(f"Respuesta del LLM no es JSON válido: {e}")
        except Exception as e:
            self.logger.error(f"Error en invocación del LLM: {e}")
            if 'response' in locals():
                self.logger.error(f"Respuesta que causó el error: {repr(response.text)}")
            raise

    def _update_known_categories(self,
                                 known_categories: List[Dict[str, Any]],
                                 new_batch_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fusiona inteligentemente los resultados de un nuevo lote con las categorías ya conocidas.
        Evita duplicados y agrupa asignaciones de códigos bajo la misma categoría.

        Args:
            known_categories: La lista actual de categorías (la "memoria" del agente).
            new_batch_results: La lista de categorías generada por el LLM para el lote actual.

        Returns:
            Una nueva lista de categorías, actualizada y sin duplicados.
        """
        self.logger.debug(f"Iniciando fusión. {len(known_categories)} categorías conocidas, {len(new_batch_results)} resultados nuevos.")

        known_map = {cat['category_name']: cat for cat in known_categories}

        for new_cat in new_batch_results:
            cat_name = new_cat.get('category_name')
            if not cat_name:
                self.logger.warning(f"Omitiendo resultado de lote sin 'category_name': {new_cat}")
                continue

            if cat_name in known_map:
                # CASO A: La categoría ya existe. FUSIONAR.
                self.logger.debug(f"Categoría existente encontrada: '{cat_name}'. Fusionando códigos.")
                existing_cat = known_map[cat_name]

                # Fusionar 'code_assignments' evitando duplicados por 'code_id'
                existing_code_ids = {assign.get('code_id') for assign in existing_cat.get('code_assignments', [])}
                
                new_assignments = new_cat.get('code_assignments', [])
                for new_assign in new_assignments:
                    if new_assign.get('code_id') not in existing_code_ids:
                        existing_cat['code_assignments'].append(new_assign)
                        existing_code_ids.add(new_assign.get('code_id'))

                # Actualizar descripción con la versión más reciente del LLM
                existing_cat['description'] = new_cat.get('description', existing_cat['description'])
            else:
                # CASO B: Es una categoría nueva. AÑADIR.
                self.logger.debug(f"Nueva categoría emergente: '{cat_name}'. Añadiendo a la memoria.")
                # Asegurarse de que el campo code_assignments existe
                new_cat.setdefault('code_assignments', [])
                known_map[cat_name] = new_cat

        return list(known_map.values())

    def _save_output(self, categorized_data: List[Dict[str, Any]]) -> None:
        """
        Guarda las categorías resultantes en el archivo de salida.
        
        Args:
            categorized_data: Datos categorizados para guardar
        """
        try:
            # Crear directorio si no existe
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(categorized_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Categorías guardadas exitosamente en {self.output_path}")
            
        except Exception as e:
            self.logger.error(f"Error al guardar categorías: {e}")
            raise

    def categorize_codes(self, codes_to_categorize: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Categoriza códigos en lotes y fusiona los resultados de forma inteligente.
        
        Args:
            codes_to_categorize: Lista de códigos a categorizar. Si es None,
                               se extraen todos los códigos del codebook.
                               
        Returns:
            Lista de categorías con códigos asignados
        """
        if codes_to_categorize is None:
            codebook_data = self._load_json_file(self.codebook_path)
            codes_to_categorize = codebook_data.get("codes", [])
            
        if not codes_to_categorize:
            self.logger.warning("No hay códigos para categorizar.")
            return []

        self.logger.info(f"Iniciando categorización de {len(codes_to_categorize)} códigos en lotes de {self.batch_size}.")

        # Cargar categorías semilla iniciales y normalizar su estructura
        config_data = self._load_json_file(self.config_path)
        seed_categories_raw = config_data.get("seed_categories", [])
        
        final_categories = []
        for seed in seed_categories_raw:
            final_categories.append({
                "category_name": seed.get("category_name", "Sin Nombre"),
                "description": seed.get("description", ""),
                "is_new": False,
                "code_assignments": []
            })
        
        total_batches = (len(codes_to_categorize) + self.batch_size - 1) // self.batch_size
        
        for i in range(0, len(codes_to_categorize), self.batch_size):
            batch_codes = codes_to_categorize[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            self.logger.info(f"Procesando lote {batch_num}/{total_batches}...")
            
            # Preparar prompt e invocar LLM para el lote actual
            # Se le pasan las categorías finales acumuladas como "memoria"
            final_prompt = self._prepare_prompt(batch_codes, final_categories)
            batch_result = self._invoke_llm(final_prompt)
            
            # Fusionar los resultados del lote con las categorías maestras
            final_categories = self._update_known_categories(final_categories, batch_result)
        
        self.logger.info(f"Categorización por lotes completada. Total de {len(final_categories)} categorías finales.")
        return final_categories

    def run(self, codes_to_categorize: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        Orquesta todo el proceso de categorización y guarda el resultado.
        
        Args:
            codes_to_categorize: Lista opcional de códigos específicos a categorizar
        """
        self.logger.info("Iniciando la ejecución del CategorizerAgent...")
        
        try:
            # Ejecutar categorización
            categorized_result = self.categorize_codes(codes_to_categorize)
            
            # Guardar resultado
            self._save_output(categorized_result)
            
            self.logger.info(f"✅ Proceso completado. Resultado guardado en {self.output_path}")
            
        except Exception as e:
            self.logger.error(f"❌ Error durante la ejecución: {e}")
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