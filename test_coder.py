import os
import google.generativeai as genai
import json
import time
from dotenv import load_dotenv
from agents.coder_agent import CoderAgent

def main():
    """
    Script principal para probar el CoderAgent y generar un archivo
    de resultados que servirá como entrada para otros tests.
    """
    # 1. Cargar las variables de entorno
    load_dotenv()
    print("✅ Archivo .env cargado.")

    # 2. Configurar el SDK de Google
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ Error: La variable de entorno GOOGLE_API_KEY no fue encontrada.")
        return

    genai.configure(api_key=api_key)
    print("✅ SDK de Google AI configurado.")

    # 3. Crear una instancia de nuestro CoderAgent
    coder = CoderAgent()

    # 4. Definir rutas y procesar insights
    data_file_path = os.path.join("data", "data.jsonl")
    output_file_path = os.path.join("data", "generated_codes.jsonl")
    
    print(f"\n📄 Cargando insights desde '{data_file_path}'...")
    print(f"📝 Los resultados se guardarán en '{output_file_path}'")

    # Usamos un bloque with para asegurar que el archivo de salida se cierre correctamente
    with open(output_file_path, 'w', encoding='utf-8') as outfile:
        try:
            with open(data_file_path, 'r', encoding='utf-8') as f:
                insights = f.readlines()
                total_insights = len(insights)
                for i, line in enumerate(insights):
                    insight = json.loads(line)
                    
                    print(f"\n🚀 Procesando insight {i+1}/{total_insights}: {insight['id']}")

                    result = coder.generate_codes(insight)

                    print("🎉 Respuesta recibida del CoderAgent:")
                    print(json.dumps(result, indent=2, ensure_ascii=False))

                    if "error" in result or not result.get("codigos_abiertos"):
                        print(f"-> ⚠️  No se generaron códigos o hubo un error para {insight['id']}. No se guardará.")
                    else:
                        # Escribir el resultado JSON en una nueva línea del archivo de salida
                        outfile.write(json.dumps(result, ensure_ascii=False) + '\n')
                        print(f"-> ✅ ¡Éxito! Códigos para {insight['id']} guardados.")

                    # Pausa crucial para no exceder el límite de la API (ej. 15 llamadas/min)
                    if i < total_insights - 1:
                        print("...pausando por 4 segundos para evitar rate-limit...")
                        time.sleep(4)

        except FileNotFoundError:
            print(f"❌ Error: El archivo de entrada '{data_file_path}' no fue encontrado.")
            return
        except json.JSONDecodeError:
            print(f"❌ Error: Problema al decodificar JSON en '{data_file_path}'.")
            return

    print(f"\n\n✅ Proceso completado. Los códigos generados se encuentran en '{output_file_path}'.")


if __name__ == "__main__":
    main()

