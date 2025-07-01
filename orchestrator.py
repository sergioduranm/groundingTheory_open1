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
from agents.narrator_agent import NarratorAgent

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
        # NUEVO: Ruta para los resultados de codificación (checkpointing)
        self.coded_data_path = "data/coded_insights.jsonl"
        # NUEVO: Ruta para los insights que fallaron
        self.failed_data_path = "data/failed_insights.jsonl"
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
                        f"'{insight.get('id', insight.get('id_fragmento', 'ID_DESCONOCIDO'))}'. "
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
        logging.info(f"Cargando datos crudos desde {self.raw_data_path}...")
        try:
            with open(self.raw_data_path, 'r', encoding='utf-8') as f:
                raw_insights = [json.loads(line) for line in f]
            logging.info(f"Se cargaron {len(raw_insights)} insights crudos.")
        except FileNotFoundError:
            logging.error(f"FATAL: El archivo de entrada de datos crudos '{self.raw_data_path}' no existe.")
            return

        # NUEVO: Lógica de Checkpointing y Reanudación
        coded_insights = []
        processed_ids = set()
        if os.path.exists(self.coded_data_path):
            logging.info(f"Encontrado archivo de checkpoint en {self.coded_data_path}. Reanudando...")
            with open(self.coded_data_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        coded_insight = json.loads(line)
                    except json.JSONDecodeError:
                        logging.error("Línea corrupta en checkpoint; se omitirá para evitar bloqueo de reanudación.")
                        continue
                    coded_insights.append(coded_insight)
                    # Fallback a 'id_fragmento' para checkpoints antiguos
                    processed_ids.add(coded_insight.get("id") or coded_insight.get("id_fragmento"))
            logging.info(f"Reanudando. Se cargaron {len(coded_insights)} insights ya procesados.")

        insights_to_process = [
            insight for insight in raw_insights if insight.get("id") not in processed_ids
        ]
        
        if not insights_to_process:
            logging.info("No hay nuevos insights para procesar. Pasando a la siguiente fase.")
        else:
            logging.info(f"Ejecutando CoderAgent para {len(insights_to_process)} nuevos insights...")
            
            # Abre el archivo de checkpoint en modo 'append' para guardar incrementalmente
            with open(self.coded_data_path, 'a', encoding='utf-8') as checkpoint_f:
                for i, insight in enumerate(insights_to_process, 1):
                    logging.info(f"Procesando insight {i}/{len(insights_to_process)} (ID: {insight.get('id', 'N/A')})...")
                    try:
                        coding_result = self.coder.generate_codes(insight)
                        
                        if coding_result.error:
                            logging.warning(f"Error al codificar insight {coding_result.id_fragmento}: {coding_result.error}. Se omitirá.")
                            coded_insight = {
                                **insight,  # Preservar datos originales incluyendo 'id'
                                "id_fragmento": coding_result.id_fragmento,
                                "fragmento_original": coding_result.fragmento_original,
                                "codigos_abiertos": [],
                                "error": coding_result.error
                            }
                        else:
                            generated_codes_dict = coding_result.model_dump()
                            coded_insight = {**insight, **generated_codes_dict}
                        
                        # Guardado incremental
                        checkpoint_f.write(json.dumps(coded_insight, ensure_ascii=False) + '\n')
                        checkpoint_f.flush(); os.fsync(checkpoint_f.fileno())
                        coded_insights.append(coded_insight)

                    except Exception as e:
                        logging.error(f"Fallo CRÍTICO al procesar insight {insight.get('id', 'N/A')}: {e}", exc_info=True)
                        # Guardar el insight fallido para análisis posterior
                        with open(self.failed_data_path, 'a', encoding='utf-8') as failed_f:
                            failed_data = {
                                "id": insight.get("id"),  # Mantener consistencia con la key original
                                "insight_original": insight,
                                "error": str(e)
                            }
                            failed_f.write(json.dumps(failed_data, ensure_ascii=False) + '\n')
                        continue # Continuar con el siguiente insight

        # Recolectar todas las etiquetas de los insights codificados (ya sean de checkpoint o nuevos)
        all_code_labels = []
        for insight in coded_insights:
            all_code_labels.extend(insight.get("codigos_abiertos", []))

        # ✅ Deduplicar para evitar etiquetas repetidas
        all_code_labels = list({label for label in all_code_labels})

        logging.info(f"✅ Codificación finalizada. Se procesaron/cargaron {len(coded_insights)} insights. Total de {len(all_code_labels)} etiquetas generadas.")

        # --- FASE 2: Síntesis de Códigos ---
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
    
    def run_narrator(self):
        """
        Runs the narrative generation stage independently.
        """
        logging.info("Orchestrating the Narrator Agent...")
        try:
            narrator = NarratorAgent(llm_service=self.llm_service)
            narrator.run()
            logging.info("✅ Narrator Agent finished successfully.")
        except Exception as e:
            logging.error(f"❌ Narrator Agent failed: {e}", exc_info=True)

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