# test_synthesizer.py

import os
import json
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
    
    # 3. Datos de prueba: Leer desde el archivo generado por test_coder.py
    generated_codes_path = os.path.join("data", "generated_codes.jsonl")
    print(f"\n📄 Cargando códigos generados desde '{generated_codes_path}'...")

    try:
        with open(generated_codes_path, 'r', encoding='utf-8') as f:
            # Leer todas las líneas y parsear el JSON de cada una
            all_coded_insights = [json.loads(line) for line in f]
    except FileNotFoundError:
        print(f"❌ ERROR: El archivo '{generated_codes_path}' no fue encontrado.")
        print("➡️  Asegúrate de haber ejecutado 'test_coder.py' primero para generarlo.")
        return
    except json.JSONDecodeError:
        print(f"❌ ERROR: El archivo '{generated_codes_path}' contiene JSON inválido.")
        return

    # Extraer todos los 'codigos_abiertos' en una única lista plana
    batch_de_nuevos_codigos = []
    for insight in all_coded_insights:
        codes = insight.get("codigos_abiertos")
        if codes and isinstance(codes, list):
            batch_de_nuevos_codigos.extend(codes)

    if not batch_de_nuevos_codigos:
        print("⚠️ No se encontraron códigos para procesar en el archivo de entrada. Finalizando prueba.")
        return

    print(f"\n🧠 Procesando lote de prueba con {len(batch_de_nuevos_codigos)} códigos extraídos del archivo.")

    # 4. Ejecución
    translation_map = synthesizer.process_batch(batch_de_nuevos_codigos)
    
    print("\n--- RESULTADO DEL TRANSLATION MAP ---")
    print("Códigos originales → IDs unificados:")
    for original_label, unified_id in translation_map.items():
        print(f"  '{original_label}' → {unified_id}")
    
    print(f"\n--- RESUMEN ---")
    print(f"Códigos originales procesados: {len(batch_de_nuevos_codigos)}")
    print(f"Códigos únicos después de unificación: {len(set(translation_map.values()))}")
    print(f"Reducción: {len(batch_de_nuevos_codigos) - len(set(translation_map.values()))} códigos unificados")
    
    print("\n--- PRUEBA FINALIZADA ---")
    print(f"Revisa el archivo 'data/codebook.TEST.json' para ver el resultado.")
    print(f"El translation map está listo para ser usado en la unificación de resultados finales.")
    # Deberías ver solo 2 códigos únicos al final, cada uno con un contador de 3.

if __name__ == "__main__":
    run_test()