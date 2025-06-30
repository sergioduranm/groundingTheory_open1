# orchestrator.py

import os
import json
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

from services.llm_service import LLMService
from agents.coder_agent import CoderAgent
from agents.synthesizer_agent import SynthesizerAgent
from agents.categorizer_agent import CategorizerAgent
from agents.axial_analyst_agent import AxialAnalystAgent
from agents.embedding_client import EmbeddingClient
from agents.codebook_repository import CodebookRepository

class Orchestrator:
    """
    Orquesta el pipeline completo de principio a fin:
    1. Carga datos crudos.
    2. Usa el CoderAgent para generar códigos abiertos.
    3. Usa el SynthesizerAgent para unificar códigos y obtener un mapa de traducción.
    4. Usa el CategorizerAgent para categorizar códigos en grupos conceptuales.
    5. Usa el mapa para enriquecer los datos con los IDs unificados.
    6. Guarda el resultado final.
    """
    def __init__(self):
        load_dotenv()
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise ValueError("La variable de entorno GOOGLE_API_KEY no está configurada.")

        # --- Inyección de dependencias para los agentes ---
        # 1. Crear una única instancia de los servicios compartidos
        self.llm_service = LLMService()
        self.codebook_repo = CodebookRepository(codebook_path="data/codebook.json")
        self.embedding_client = EmbeddingClient(api_key=google_api_key)
        
        # 2. Inyectar los servicios en los agentes que los necesitan
        self.coder = CoderAgent(llm_service=self.llm_service) 
        
        self.synthesizer = SynthesizerAgent(
            repository=self.codebook_repo, 
            client=self.embedding_client,
            similarity_threshold=0.90
        )
        
        self.categorizer = CategorizerAgent(llm_service=self.llm_service)
        
        self.axial_analyst = AxialAnalystAgent(llm_service=self.llm_service)

        # NUEVO: Definimos la ruta para los datos de entrada crudos
        self.raw_data_path = "data/data.jsonl"
        self.output_path = "data/analysis_results.jsonl" # Renombrado para reflejar el resultado final

    def _enrich_insights_with_unified_codes(
        self,
        coded_insights: List[Dict[str, Any]],
        translation_map: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Toma una lista de insights codificados y un mapa de traducción,
        y devuelve una nueva lista de insights enriquecidos con los IDs de códigos unificados.
        (Este método no necesita cambios, ya es perfecto)
        """
        logging.info("Enriqueciendo insights con IDs de códigos unificados...")
        enriched_insights = []
        for insight in coded_insights:
            original_code_labels = insight.get("codigos_abiertos", [])
            
            unified_ids = []
            for label in original_code_labels:
                unified_id = translation_map.get(label)
                if unified_id:
                    unified_ids.append(unified_id)
                else:
                    logging.warning(
                        f"No se encontró mapeo para la etiqueta '{label}' en el insight "
                        f"'{insight.get('id_fragmento', 'ID_DESCONOCIDO')}'. "
                        "Será omitida del resultado final."
                    )
            
            # Usando dictionary unpacking para una actualización limpia y segura
            new_insight = {**insight, "unified_code_ids": unified_ids}
            enriched_insights.append(new_insight)
        
        logging.info(f"✅ {len(enriched_insights)} insights han sido enriquecidos.")
        return enriched_insights

    def run_pipeline(self):
        """
        Ejecuta el pipeline completo de orquestación de forma automática.
        """
        logging.info("🚀 Iniciando el pipeline de orquestación end-to-end...")

        # --- FASE 1: Carga y Codificación de Datos Crudos ---
        # MODIFICADO: Esta fase ahora es activa. Carga datos crudos y ejecuta el CoderAgent.
        logging.info(f"Cargando datos crudos desde {self.raw_data_path}...")
        try:
            with open(self.raw_data_path, 'r', encoding='utf-8') as f:
                raw_insights = [json.loads(line) for line in f]
            logging.info(f"Se cargaron {len(raw_insights)} insights crudos.")
        except FileNotFoundError:
            logging.error(f"FATAL: El archivo de entrada de datos crudos '{self.raw_data_path}' no existe.")
            return

        logging.info("Ejecutando CoderAgent para generar códigos abiertos...")
        coded_insights = []
        all_code_labels = []

        # --- LIMITADOR DE DEBUG ---
        # Procesamos solo los primeros 5 insights para una prueba de validación.
        num_insights_to_process = 5
        insights_to_process = raw_insights[:num_insights_to_process]
        logging.warning(f"MODO DE PRUEBA: Procesando solo los primeros {len(insights_to_process)} de {len(raw_insights)} insights.")

        for i, insight in enumerate(insights_to_process, 1):
            logging.info(f"Procesando insight {i}/{len(insights_to_process)} (ID: {insight.get('id', 'N/A')})...")
            # El CoderAgent ahora devuelve un objeto Pydantic validado.
            coding_result = self.coder.generate_codes(insight)
            
            # Verificamos si hubo un error durante la codificación.
            if coding_result.error:
                logging.warning(f"Error al codificar insight {coding_result.id_fragmento}: {coding_result.error}. Se omitirá del resultado.")
                # Creamos una entrada parcial para mantener la trazabilidad y la consistencia del esquema.
                coded_insight = {
                    "id_fragmento": coding_result.id_fragmento,
                    "fragmento_original": coding_result.fragmento_original,
                    "codigos_abiertos": [],
                    "error": coding_result.error
                }
            else:
                # Si no hay error, convertimos el resultado a un diccionario para fusionarlo.
                generated_codes_dict = coding_result.model_dump()
                # Combinamos el insight original con los códigos generados.
                coded_insight = {**insight, **generated_codes_dict}

            coded_insights.append(coded_insight)
            all_code_labels.extend(coded_insight.get("codigos_abiertos", []))

        logging.info(f"✅ CoderAgent finalizado. Se generaron un total de {len(all_code_labels)} etiquetas.")

        # --- FASE 2: Síntesis de Códigos ---
        # (Esta fase no cambia, recibe los datos de la fase anterior)
        logging.info("Iniciando la fase de síntesis para generar el mapa de traducción...")
        translation_map = self.synthesizer.process_batch(all_code_labels)
        logging.info("✅ Mapa de traducción generado exitosamente. El codebook.json ha sido actualizado.")

        # --- FASE 3: Categorización de Códigos ---
        logging.info("Iniciando la fase de categorización para agrupar códigos conceptualmente...")
        try:
            categorized_result = self.categorizer.categorize_codes()
            self.categorizer._save_output(categorized_result)
            logging.info("✅ Categorización completada. Las categorías han sido guardadas.")
        except Exception as e:
            logging.warning(f"Error en categorización (continuando pipeline): {e}")

        # --- FASE 4: Enriquecimiento de Datos ---
        # (Esta fase no cambia, recibe los datos de las fases anteriores)
        enriched_data = self._enrich_insights_with_unified_codes(
            coded_insights=coded_insights,
            translation_map=translation_map
        )

        # --- FASE 5: Guardado de Resultados ---
        logging.info(f"Guardando los datos enriquecidos en '{self.output_path}'...")
        with open(self.output_path, 'w', encoding='utf-8') as f:
            for item in enriched_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        # --- FASE 6: ANÁLISIS AXIAL ---
        logging.info("Iniciando la fase final de Análisis Axial...")
        try:
            self.axial_analyst.run()
            logging.info("✅ Análisis Axial completado exitosamente.")
        except Exception as e:
            logging.error(f"❌ El Análisis Axial falló, pero el pipeline principal tuvo éxito. Error: {e}", exc_info=True)

        logging.info(f"🎉 ¡Pipeline completado! El archivo de resultados '{self.output_path}' está listo.")
    
    def run_categorization_only(self, codes_to_categorize: List[Dict[str, Any]] = None):
        """
        Ejecuta únicamente la fase de categorización, útil para análisis axial
        independiente del pipeline principal.
        
        Args:
            codes_to_categorize: Lista opcional de códigos específicos a categorizar.
                               Si es None, se utilizan todos los códigos del codebook.
        """
        logging.info("🔍 Iniciando pipeline de categorización únicamente...")
        
        try:
            categorized_result = self.categorizer.categorize_codes(codes_to_categorize)
            self.categorizer._save_output(categorized_result)
            logging.info("✅ Categorización completada exitosamente.")
            return categorized_result
        except Exception as e:
            logging.error(f"❌ Error en el pipeline de categorización: {e}")
            raise