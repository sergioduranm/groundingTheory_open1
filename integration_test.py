# integration_test.py

import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv

# Importamos todos los componentes necesarios
from agents.coder_agent import CoderAgent
from agents.synthesizer_agent import SynthesizerAgent
from agents.codebook_repository import CodebookRepository
from agents.embedding_client import EmbeddingClient

# Configuración básica de logging para ver qué está pasando
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_integration_test():
    """
    Ejecuta una prueba de integración que conecta el CoderAgent con el SynthesizerAgent.
    """
    logger.info("--- INICIANDO PRUEBA DE INTEGRACIÓN ---")

    # --- 1. CONFIGURACIÓN ---
    load_dotenv()
    gemini_api_key = os.getenv("GOOGLE_API_KEY")
    if not gemini_api_key:
        raise ValueError("La variable de entorno GOOGLE_API_KEY no está configurada.")

    # --- 2. INSTANCIACIÓN DE COMPONENTES ---
    # Creamos instancias de todos nuestros componentes de producción
    
    # Configurar el SDK de Google AI
    genai.configure(api_key=gemini_api_key)
    
    # El CoderAgent que genera los códigos
    coder = CoderAgent()
    
    # Los componentes para el SynthesizerAgent
    # Usaremos un codebook de prueba para no sobreescribir datos reales
    test_repo = CodebookRepository(codebook_path="data/codebook.INTEGRATION-TEST.json")
    embedding_client = EmbeddingClient(api_key=gemini_api_key)
    synthesizer = SynthesizerAgent(repository=test_repo, client=embedding_client, similarity_threshold=0.95)

    logger.info("✅ Todos los agentes y componentes han sido inicializados.")

    # --- 3. SIMULACIÓN DEL FLUJO ---
    
    # Definimos un insight cualitativo como punto de partida
    insight_de_prueba = {
        "id": "integration_test_001",
        "text": "No importa cuánto me esfuerce, parece que nunca es suficiente para obtener un ascenso. Siento que mi trabajo es invisible."
    }
    
    logger.info(f"Procesando insight: '{insight_de_prueba}'")
    
    # Paso A: El CoderAgent genera los códigos
    generated_codes = coder.generate_codes(insight_de_prueba)
    
    if not generated_codes:
        logger.error("El CoderAgent no pudo generar códigos. Abortando prueba.")
        return
        
    logger.info(f"🧠 CoderAgent generó {len(generated_codes)} códigos: {generated_codes}")
    
    # Extraer solo los códigos del resultado del CoderAgent
    codigos_para_sintetizar = generated_codes.get("codigos_abiertos", [])
    
    if not codigos_para_sintetizar:
        logger.error("No se encontraron códigos para sintetizar. Abortando prueba.")
        return
    
    logger.info(f"📝 Códigos extraídos para sintetizar: {codigos_para_sintetizar}")
    
    # Paso B: El SynthesizerAgent recibe los códigos generados
    logger.info("🤝 Pasando la posta al SynthesizerAgent...")
    translation_map = synthesizer.process_batch(codigos_para_sintetizar)
    
    # Mostrar el mapa de traducción
    logger.info(f"📋 Mapa de traducción generado: {translation_map}")
    
    # Mostrar resumen de unificación
    unique_codes = set(translation_map.values())
    logger.info(f"📊 Resumen: {len(codigos_para_sintetizar)} códigos originales → {len(unique_codes)} códigos únicos")
    logger.info(f"🔄 Reducción: {len(codigos_para_sintetizar) - len(unique_codes)} códigos unificados")
    
    logger.info("--- PRUEBA DE INTEGRACIÓN FINALIZADA ---")
    logger.info("Revisa el archivo 'data/codebook.INTEGRATION-TEST.json' para validar el resultado.")
    logger.info("Deberías ver un nuevo codebook con los conceptos extraídos del insight, ya consolidados.")
    logger.info(f"El translation map está listo para ser usado en la unificación de resultados finales.")

if __name__ == "__main__":
    run_integration_test()
