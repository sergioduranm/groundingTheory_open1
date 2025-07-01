"""
Synthesis Agent para generar reporte de síntesis teórica en Markdown.
Transforma las narrativas por categoría en un modelo teórico integrado.
"""

import json
import logging
from typing import List, Dict, Any

from services.llm_service import LLMService
from utils.file_utils import load_jsonl_file, load_prompt_template, write_text_file


class SynthesisAgent:
    """
    Agente especializado en síntesis teórica que usa el modelo más avanzado disponible.
    Genera un informe estructurado en Markdown optimizado para Notion.
    """
    
    def __init__(self, llm_service: LLMService, config: Dict[str, Any]):
        """
        Inicializa el agente de síntesis.
        
        Args:
            llm_service: Servicio de LLM compartido.
            config: Configuración del proyecto.
        """
        self.llm_service = llm_service
        self.config = config
        
        # Guardar el nombre del modelo avanzado para este agente
        self.advanced_model_name = self.config["llm"]["advanced_model"]
        
        # Cargar templates de prompts
        self.category_prompt = load_prompt_template(self.config["prompts"]["synthesize_category"])
        self.final_report_prompt = load_prompt_template(self.config["prompts"]["synthesize_final_report"])
        
        # Mapeo de nombres de categorías para el clustering
        self.category_mapping = {
            "Formación de hábitos": "individual",
            "Desarrollo de competencias": "individual", 
            "Empoderamiento y Autonomía del Usuario": "individual",
            "Generación de confianza": "sistemic",
            "Acompañamiento": "sistemic",
            "Regulación y Gobernanza del Ecosistema Financiero": "sistemic",
            "Capacidades y Aplicaciones de la IA/Tecnología": "technological",
            "Desafíos y Riesgos de la Interacción con IA/Tecnología": "technological",
            "Obstáculos y Barreras Financieras": "central",
            "Consecución de metas": "central",
            "Gestión integral del bienestar": "central"
        }

    def run(self) -> str:
        """
        Ejecuta el proceso completo de síntesis teórica.
        
        Returns:
            str: Ruta del archivo Markdown generado
        """
        logging.info("=== INICIANDO SYNTHESIS AGENT ===")
        logging.info(f"Usando modelo avanzado: {self.advanced_model_name}")
        
        # Rutas de archivos
        narratives_file_path = self.config["data"]["narrativas_por_categoria"]
        output_file_path = self.config["data"]["reporte_sintesis_teorica"]
        
        # Cargar datos
        logging.info(f"Cargando narrativas desde: {narratives_file_path}")
        narratives_data = list(load_jsonl_file(narratives_file_path))
        logging.info(f"Cargadas {len(narratives_data)} categorías")
        
        # Fase 1: Síntesis Intra-Categoría
        logging.info("=== FASE 1: SÍNTESIS INTRA-CATEGORÍA ===")
        synthesized_narratives = self._synthesize_categories(narratives_data)
        
        # Fase 2: Generación del Informe Final
        logging.info("=== FASE 2: GENERACIÓN DEL INFORME FINAL ===")
        final_report = self._generate_final_report(synthesized_narratives)
        
        # Escribir resultado
        logging.info(f"Escribiendo informe final en: {output_file_path}")
        write_text_file(output_file_path, final_report)
        
        logging.info("=== SYNTHESIS AGENT COMPLETADO ===")
        return output_file_path

    def _synthesize_categories(self, narratives_data: List[Dict]) -> Dict[str, str]:
        """
        Sintetiza cada categoría individualmente preservando su estructura teórica.
        """
        synthesized = {}
        
        for i, category_data in enumerate(narratives_data, 1):
            category_name = category_data.get("category_name")
            logging.info(f"  [{i}/{len(narratives_data)}] Sintetizando: {category_name}")
            
            full_narrative = self._build_full_narrative(category_data.get("narrative_blocks", []))
            
            prompt = self.category_prompt.format(
                category_name=category_name,
                full_narrative=full_narrative
            )
            
            try:
                # Llamada al LLM a través del servicio, especificando el modelo avanzado
                synthesized_text = self.llm_service.invoke_llm(
                    prompt, 
                    model=self.advanced_model_name
                )
                
                if synthesized_text:
                    synthesized[category_name] = synthesized_text
                    logging.info(f"    ✓ Completado ({len(synthesized_text)} caracteres)")
                else:
                    logging.error(f"    ✗ Error: LLM retornó None para {category_name}")
                    synthesized[category_name] = f"Error al procesar la categoría: {full_narrative}"
                
            except Exception as e:
                logging.error(f"    ✗ Error sintetizando {category_name}: {e}")
                synthesized[category_name] = f"Error al procesar la categoría: {full_narrative}"
        
        return synthesized

    def _build_full_narrative(self, narrative_blocks: List[Dict]) -> str:
        """
        Construye la narrativa completa concatenando todos los bloques.
        """
        sections = []
        for block in narrative_blocks:
            title = block.get("title", "")
            text = block.get("text", "")
            if title and text:
                sections.append(f"**{title}**\n\n{text}")
        
        return "\n\n---\n\n".join(sections)

    def _generate_final_report(self, synthesized_narratives: Dict[str, str]) -> str:
        """
        Genera el informe final estructurado por clusters temáticos.
        """
        logging.info("  Estructurando narrativas por clusters...")
        
        all_narratives_text = "\n\n" + "="*80 + "\n\n"
        for category_name, narrative in synthesized_narratives.items():
            all_narratives_text += f"## CATEGORÍA: {category_name}\n\n"
            all_narratives_text += f"{narrative}\n\n"
            all_narratives_text += "="*80 + "\n\n"
        
        prompt = self.final_report_prompt.format(
            synthesized_narratives=all_narratives_text
        )
        
        logging.info("  Generando informe integrado con modelo avanzado...")
        
        try:
            # Llamada al LLM especificando el modelo avanzado
            final_report = self.llm_service.invoke_llm(
                prompt,
                model=self.advanced_model_name
            )
            
            if final_report:
                logging.info("  ✓ Informe final generado exitosamente")
                return final_report
            else:
                logging.error("  ✗ Error: LLM retornó None para el informe final")
                return self._create_fallback_report(synthesized_narratives)
            
        except Exception as e:
            logging.error(f"  ✗ Error generando informe final: {e}")
            return self._create_fallback_report(synthesized_narratives)

    def _create_fallback_report(self, synthesized_narratives: Dict[str, str]) -> str:
        """
        Crea un informe básico en caso de error en la generación con LLM.
        """
        report = "# Modelo Teórico de Bienestar Financiero Digital\n\n"
        report += "## Informe de Síntesis Teórica\n\n"
        
        for category_name, narrative in synthesized_narratives.items():
            report += f"### {category_name}\n\n"
            report += f"{narrative}\n\n"
            report += "---\n\n"
        
        return report 