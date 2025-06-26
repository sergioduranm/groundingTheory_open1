# test_synthesizer.py

import os
from dotenv import load_dotenv
from agents.synthesizer_agent import SynthesizerAgent
from agents.codebook_repository import CodebookRepository
from agents.embedding_client import EmbeddingClient

def run_test():

    print("--- INICIANDO PRUEBA DEL SYNTHESIZER AGENT ---")
    
    # 1. Cargar configuración
    load_dotenv()
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("La variable de entorno google_api_key no está configurada. Asegúrate de tener un archivo .env")

    # 2. Inyección de Dependencias
    # Apuntaremos a un codebook de prueba para no afectar el real
    test_repo = CodebookRepository(codebook_path="data/codebook.TEST.json")
    client = EmbeddingClient(api_key=google_api_key)
    # Usamos un umbral de 0.85 para la prueba, puede ser más estricto (0.90) en producción
    synthesizer = SynthesizerAgent(repository=test_repo, client=client, similarity_threshold=0.85)
    
    # 3. Datos de prueba
    batch_de_nuevos_codigos = [
        "expresando frustración por falta de reconocimiento", 
        "sintiendo que las ideas propias no son valoradas",  # Duplicado semántico del anterior
        "dificultades con la nueva plataforma de software",   # Código nuevo
        "los empleados tienen problemas para usar la herramienta crm", # Duplicado semántico del anterior
        "expresando frustración por falta de reconocimiento",  # Duplicado exacto
        "sensación de no ser apreciado en el equipo"          # Duplicado semántico de los dos primeros
    ]
    print(f"\nProcesando lote de prueba con {len(batch_de_nuevos_codigos)} códigos...")

    # 4. Ejecución
    synthesizer.process_batch(batch_de_nuevos_codigos)
    
    print("\n--- PRUEBA FINALIZADA ---")
    print(f"Revisa el archivo 'data/codebook.TEST.json' para ver el resultado.")
    # Deberías ver solo 2 códigos únicos al final, cada uno con un contador de 3.

if __name__ == "__main__":
    run_test()