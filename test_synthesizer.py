import os
import json
from agents.synthesizer_agent import SynthesizerAgent

def print_codebook_summary(agent: SynthesizerAgent):
    """Función de ayuda para imprimir un resumen legible del codebook."""
    print(f"  📊 Resumen del Codebook ({len(agent.codebook['codes'])} códigos únicos):")
    if not agent.codebook['codes']:
        print("    -> El codebook está vacío.")
        return
    # Ordenar por label para una visualización consistente
    sorted_codes = sorted(agent.codebook['codes'], key=lambda x: x['label'])
    for code in sorted_codes:
        print(f"    - \"{code['label']}\" (count: {code['count']})")
    print("-" * 30)

def main():
    """
    Script principal para probar el SynthesizerAgent de forma aislada y controlada.
    """
    print("🚀 Iniciando prueba del SynthesizerAgent...")
    
    # --- PREPARACIÓN ---
    # Para una prueba limpia, eliminamos el codebook anterior si existe.
    codebook_file = "data/codebook.json"
    if os.path.exists(codebook_file):
        os.remove(codebook_file)
        print(f"🗑️  Archivo de codebook anterior eliminado para una prueba limpia.")

    # Instanciar el agente. Usaremos un umbral ligeramente más bajo para capturar "UX"
    # como un duplicado de "user experience" y demostrar la funcionalidad.
    agent = SynthesizerAgent(codebook_path=codebook_file, similarity_threshold=0.50)
    print_codebook_summary(agent)

    # --- PRUEBA 1: Primer lote de códigos únicos ---
    print("\n🧪 PRUEBA 1: Procesando un lote inicial de códigos.")
    batch_1 = [
        "Experimentando desvalorización", 
        "Buscando reconocimiento profesional", 
        "Percibiendo falta de oportunidades"
    ]
    print(f"  -> Lote de entrada: {batch_1}")
    agent.process_batch(batch_1)
    print_codebook_summary(agent)
    
    # --- PRUEBA 2: Lote con duplicados exactos y semánticos ---
    print("\n🧪 PRUEBA 2: Procesando lote con duplicados exactos y semánticos.")
    batch_2 = [
        "Sintiendo que no me valoran",          # Duplicado semántico de "Experimentando desvalorización"
        "Buscando reconocimiento profesional",  # Duplicado exacto
        "Identificando un techo de cristal"    # Código nuevo
    ]
    print(f"  -> Lote de entrada: {batch_2}")
    agent.process_batch(batch_2)
    print_codebook_summary(agent)

    # --- PRUEBA 3: Lote con más variantes y códigos nuevos ---
    print("\n🧪 PRUEBA 3: Procesando un lote mixto final.")
    batch_3 = [
        "Sintiendo que mi trabajo es invisible", # Duplicado semántico de "Experimentando desvalorización"
        "Buscando validación de mis superiores", # Duplicado semántico de "Buscando reconocimiento"
        "Proponiendo mejoras al sistema",      # Código nuevo
        "Comunicando frustración al equipo"    # Código nuevo
    ]
    print(f"  -> Lote de entrada: {batch_3}")
    agent.process_batch(batch_3)
    print_codebook_summary(agent)

    print("\n✅ Prueba del SynthesizerAgent completada.")

if __name__ == "__main__":
    main()

