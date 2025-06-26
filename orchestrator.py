# orchestrator.py

import os
import json
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

from agents.coder_agent import CoderAgent
from agents.synthesizer_agent import SynthesizerAgent
from agents.embedding_client import EmbeddingClient
from agents.codebook_repository import CodebookRepository

# Configurar un logger básico para recibir los mensajes de advertencia
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Orchestrator:
    """
    Orquesta el pipeline completo:
    1. Carga los datos codificados.
    2. Usa el SynthesizerAgent para unificar códigos y obtener un mapa de traducción.
    3. Usa el mapa para enriquecer los datos originales con los IDs unificados.
    4. Guarda el resultado final.
    """
    def __init__(self):
        load_dotenv()
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise ValueError("La variable de entorno GOOGLE_API_KEY no está configurada.")

        # Inyección de dependencias para los agentes
        # Usamos el codebook principal, ya que esta es la ejecución "real"
        self.codebook_repo = CodebookRepository(codebook_path="data/codebook.json")
        self.embedding_client = EmbeddingClient(api_key=google_api_key)
        self.synthesizer = SynthesizerAgent(
            repository=self.codebook_repo, 
            client=self.embedding_client,
            similarity_threshold=0.90 # Umbral de producción
        )

        self.coded_insights_path = "data/generated_codes.jsonl"
        self.output_path = "data/insights_enriquecidos.jsonl"

    def _enrich_insights_with_unified_codes(
        self,
        coded_insights: List[Dict[str, Any]],
        translation_map: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Toma una lista de insights codificados y un mapa de traducción,
        y devuelve una nueva lista de insights enriquecidos con los IDs de códigos unificados.
        Implementa logging para códigos no encontrados.
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
                    # MEJORA: Log para códigos "perdidos"
                    logging.warning(
                        f"No se encontró mapeo para la etiqueta '{label}' en el insight "
                        f"'{insight.get('id_fragmento', 'ID_DESCONOCIDO')}'. "
                        "Será omitida del resultado final."
                    )
            
            # MEJORA: Copia y adición de la nueva clave
            new_insight = insight.copy()
            new_insight["codigos_unificados_ids"] = unified_ids
            enriched_insights.append(new_insight)
        
        logging.info(f"✅ {len(enriched_insights)} insights han sido enriquecidos.")
        return enriched_insights

    def run_pipeline(self):
        """
        Ejecuta el pipeline completo de orquestación.
        """
        logging.info("🚀 Iniciando el pipeline de orquestación...")

        # --- FASE 1: Carga de Datos Codificados (Simulada) ---
        logging.info(f"Cargando datos pre-codificados desde {self.coded_insights_path}...")
        try:
            with open(self.coded_insights_path, 'r', encoding='utf-8') as f:
                coded_insights = [json.loads(line) for line in f]
            logging.info(f"Se cargaron {len(coded_insights)} insights codificados.")
        except FileNotFoundError:
            logging.error(f"FATAL: El archivo de entrada '{self.coded_insights_path}' no existe. Ejecuta test_coder.py primero.")
            return

        # --- FASE 2: Síntesis de Códigos ---
        logging.info("Iniciando la fase de síntesis para generar el mapa de traducción...")
        all_code_labels = []
        for insight in coded_insights:
            all_code_labels.extend(insight.get("codigos_abiertos", []))
        
        logging.info(f"Se enviarán {len(all_code_labels)} etiquetas de código al SynthesizerAgent.")
        translation_map = self.synthesizer.process_batch(all_code_labels)
        logging.info("✅ Mapa de traducción generado exitosamente.")

        # --- FASE 3: Enriquecimiento de Datos ---
        enriched_data = self._enrich_insights_with_unified_codes(
            coded_insights=coded_insights,
            translation_map=translation_map
        )

        # --- FASE 4: Guardado de Resultados ---
        logging.info(f"Guardando los datos enriquecidos en '{self.output_path}'...")
        with open(self.output_path, 'w', encoding='utf-8') as f:
            for item in enriched_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        logging.info("🎉 ¡Pipeline completado! El archivo de resultados está listo.") 