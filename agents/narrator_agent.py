import os
import json
from typing import Dict, Any, List

from services.llm_service import LLMService
from utils.file_utils import load_jsonl_file, append_to_jsonl_file, extract_json_from_text

# A reasonable heuristic: 1 token ~= 4 characters. 
# Let's set a conservative limit for the evidence part of the prompt.
# E.g., for a 128k context model, keeping evidence under 100k chars is safe.
EVIDENCE_CHAR_LIMIT = 100000 

class NarratorAgent:
    """
    An agent responsible for converting structured axial analysis data for each category
    into a rich, dense narrative.
    """

    def __init__(self, llm_service: LLMService):
        """
        Initializes the NarratorAgent.

        Args:
            llm_service: An instance of LLMService to interact with the language model.
        """
        self.llm_service = llm_service
        self.narrative_prompt_template = self._load_prompt("prompts/narrate_category.md")
        self.insights_source_path = "data/data.jsonl"
        self.axial_analysis_path = "data/analisis_axial.jsonl"
        self.output_path = "data/narrativas_por_categoria.jsonl"
        self.all_insights_map = self._get_all_insights_map()

    def _load_prompt(self, filepath: str) -> str:
        """Loads a prompt template from a file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Error: Prompt file not found at {filepath}")
            return ""

    def _get_all_insights_map(self) -> Dict[str, str]:
        """
        Loads the raw insights from the .jsonl source file and creates a mapping 
        from insight ID to its text for quick lookup.
        """
        insights_map = {}
        try:
            for insight in load_jsonl_file(self.insights_source_path):
                if "id" in insight and "text" in insight:
                    insights_map[insight["id"]] = insight["text"]
            return insights_map
        except Exception as e:
            print(f"Error reading insights source file at {self.insights_source_path}: {e}")
            return {}

    def run(self):
        """
        Executes the narrative generation process for all categories.
        It reads the axial analysis, prepares a prompt for each category,
        generates the narrative using the LLM, and saves the results.
        """
        print("Starting narrative generation process...")
        
        try:
            axial_data = list(load_jsonl_file(self.axial_analysis_path))
        except Exception as e:
            print(f"Error: Could not read axial analysis file from {self.axial_analysis_path}: {e}")
            return

        narratives = []
        failed_categories = []
        
        # Clear the output file before starting
        with open(self.output_path, 'w') as f:
            f.write('')

        for i, category_data in enumerate(axial_data):
            category_name = category_data.get("category_name", "N/A")
            category_id = category_data.get("category_id")
            print(f"Processing category {i+1}/{len(axial_data)}: {category_name}")

            try:
                evidence_map = self._get_evidence_for_category(category_data)
                prompt = self._prepare_narrative_prompt(category_data, evidence_map)
                
                # 1. Llamar a la API a través del servicio centralizado.
                llm_response_text = self.llm_service.invoke_llm(prompt)

                if not llm_response_text:
                    raise ValueError("La respuesta del LLM estaba vacía.")

                # 2. Usar nuestra utilidad experta para extraer y parsear el JSON de la respuesta.
                structured_response = extract_json_from_text(llm_response_text)
                
                if not structured_response:
                    print(f"DEBUG: Fallo de parseo de JSON para la categoría: {category_name}")
                    raise ValueError("No se pudo extraer un JSON válido de la respuesta del LLM.")

                if "narrative_blocks" in structured_response:
                    narrative_output = {
                        "category_id": category_id,
                        "category_name": category_name,
                        "narrative_blocks": structured_response["narrative_blocks"]
                    }
                    append_to_jsonl_file(self.output_path, narrative_output)
                    narratives.append(narrative_output)
                else:
                    print(f"  [Warning] 'narrative_blocks' not found in LLM response for {category_name}.")
                    failed_categories.append(f"{category_name} (ID: {category_id}) - Malformed response")

            except Exception as e:
                print(f"  [Error] Failed to process category {category_name}: {e}")
                failed_categories.append(f"{category_name} (ID: {category_id}) - {e}")

        print("\n--- Narrative Generation Summary ---")
        print(f"Successfully generated narratives for {len(narratives)} categories.")
        if failed_categories:
            print(f"Failed to generate narratives for {len(failed_categories)} categories:")
            for failed in failed_categories:
                print(f"  - {failed}")
        print(f"Results saved to {self.output_path}")
        print("------------------------------------")

    def _get_evidence_for_category(self, category_analysis: Dict[str, Any]) -> Dict[str, str]:
        """
        Gathers all unique insight verbatim texts for a given category's analysis.
        """
        referenced_ids = set()
        analysis = category_analysis.get("analysis", {})

        # Extract from paradigm model
        paradigm_model = analysis.get("paradigm_model", {})
        if paradigm_model:
            for component in paradigm_model.values():
                if isinstance(component, list):
                    for item in component:
                        if isinstance(item, dict):
                            for insight_id in item.get("evidence_insight_ids", []):
                                referenced_ids.add(insight_id)

        # Extract from properties and dimensions
        properties = analysis.get("properties_and_dimensions", [])
        if properties:
            for prop in properties:
                if isinstance(prop, dict):
                    for insight_id in prop.get("evidence_insight_ids", []):
                        referenced_ids.add(insight_id)
        
        evidence_map = {}
        for insight_id in referenced_ids:
            evidence_text = self.all_insights_map.get(insight_id)
            if evidence_text:
                evidence_map[insight_id] = evidence_text
            else:
                evidence_map[insight_id] = f"Referenced insight text not found for ID: {insight_id}"
        
        return evidence_map

    def _prepare_narrative_prompt(self, category_data: Dict[str, Any], evidence_map: Dict[str, str]) -> str:
        """
        Prepares the final prompt for the LLM by filling the template with
        the specific data for a category.
        """
        analysis = category_data.get("analysis", {})
        paradigm_model = analysis.get("paradigm_model", {})
        properties = analysis.get("properties_and_dimensions", [])

        # The prompt expects these as JSON strings
        paradigm_model_json = json.dumps(paradigm_model, indent=4, ensure_ascii=False)
        properties_json = json.dumps(properties, indent=4, ensure_ascii=False)
        evidence_json = json.dumps(evidence_map, indent=4, ensure_ascii=False)

        # A better heuristic might be to find a specific property or a description field.
        # For now, let's take the first property's description as a stand-in.
        # category_description = properties[0].get("property_description", category_description)
        # UPDATED LOGIC: The prompt will be changed to not require a description.
        # The LLM will infer it from the context.
        category_description = "No central phenomenon description found." # This will be removed from format call


        prompt = self.narrative_prompt_template.format(
            category_name=category_data.get("category_name", "N/A"),
            paradigm_model_json=paradigm_model_json,
            properties_json=properties_json,
            evidence_json=evidence_json
        )
        return prompt

    def _get_summarized_evidence_json(self, category_data: Dict[str, Any], all_insights_map: Dict[str, Any]) -> str:
        """
        Gets all evidence for a category. If it's too large, it asks the LLM
        to summarize it before returning it as a JSON string.
        """
        evidence_map = self._get_evidence_for_category(category_data)
        evidence_json_str = json.dumps(evidence_map, indent=2, ensure_ascii=False)
        
        if len(evidence_json_str) > EVIDENCE_CHAR_LIMIT:
            print(f"  [Info] Evidence for '{category_data['category_name']}' is too large ({len(evidence_json_str)} chars). Summarizing...")
            summarization_prompt = (
                "The following is a JSON object containing raw text excerpts used as evidence in a qualitative study. "
                "Please synthesize the key themes, patterns, and core ideas from this evidence into a concise summary. "
                "Focus on the main points that emerge from the data as a whole.\n\n"
                f"Evidence to summarize:\n{evidence_json_str}"
            )
            
            summary_text = self.llm_service.generate_response(summarization_prompt)
            
            # Return a structured summary instead of the full evidence
            return json.dumps({
                "summary_note": "The original evidence was too large for the context window and has been summarized below.",
                "evidence_summary": summary_text
            }, indent=2, ensure_ascii=False)

        return evidence_json_str