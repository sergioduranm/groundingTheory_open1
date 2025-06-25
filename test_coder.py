import os
import google.generativeai as genai
import json
from dotenv import load_dotenv
from agents.coder_agent import CoderAgent

def main():
    """
    Script principal para probar el CoderAgent de forma aislada.
    """
    # 1. Cargar las variables de entorno desde el archivo .env
    #    Esto buscará un archivo .env y cargará sus variables en el entorno del sistema.
    load_dotenv()
    print("✅ Archivo .env cargado.")

    # 2. Obtener la API Key y configurar el SDK de Google
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ Error: La variable de entorno GOOGLE_API_KEY no fue encontrada.")
        print("Asegúrate de que tu archivo .env está configurado correctamente.")
        return

    genai.configure(api_key=api_key)
    print("✅ SDK de Google AI configurado.")

    # 3. Crear una instancia de nuestro CoderAgent
    coder = CoderAgent()

    # 4. Definir un insight de prueba para enviar al agente
    sample_insight = {
        "id": "insight_test_001",
        "text": "Siento que mi trabajo no es valorado por la empresa."
    }
    print(f"\n🚀 Enviando insight de prueba al agente:\n{json.dumps(sample_insight, indent=2)}")

    # 5. Llamar al método del agente y obtener el resultado
    result = coder.generate_codes(sample_insight)

    # 6. Imprimir el resultado de forma legible
    print("\n🎉 Respuesta recibida del CoderAgent:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if "error" in result:
        print("\n⚠️ El agente reportó un error durante el procesamiento.")
    elif result.get("codigos_abiertos"):
        print("\n✅ ¡Prueba exitosa! El agente generó códigos.")
    else:
        print("\n🤔 La prueba se completó pero no se generaron códigos.")


if __name__ == "__main__":
    main()

