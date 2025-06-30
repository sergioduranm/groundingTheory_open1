# Sistema de Agentes para Análisis Cualitativo con IA

Este proyecto implementa un sistema de múltiples agentes de IA diseñado para automatizar y escalar el análisis cualitativo de texto, inspirado en la metodología de Teoría Fundamentada. El sistema procesa insights desde un archivo Excel, y ejecuta un pipeline de varias fases que incluye codificación abierta, unificación de códigos, categorización conceptual y análisis axial.

## Características Principales

- **Preprocesamiento Avanzado:** Convierte archivos `.xlsx` a formato `.jsonl` y extrae metadatos de trazabilidad.
- **Codificación Abierta:** Un `CoderAgent` lee los insights y propone códigos conceptuales iniciales.
- **Síntesis y Unificación Semántica:** Un `SynthesizerAgent` utiliza embeddings vectoriales para consolidar códigos semánticamente similares, creando un libro de códigos (`codebook.json`) maestro.
- **Categorización Conceptual:** Un `CategorizerAgent` agrupa los códigos unificados en categorías temáticas de alto nivel.
- **Análisis Axial:** Un `AxialAnalystAgent` realiza un análisis más profundo para explorar las relaciones entre las categorías generadas.
- **Orquestación Automatizada:** Un `Orchestrator` gestiona el flujo completo del pipeline de análisis con un solo comando.
- **Trazabilidad Completa:** Los resultados finales mantienen un vínculo claro entre cada insight original y sus códigos, categorías y metadatos correspondientes.

## Estructura del Proyecto

```
/
├── agents/             # Lógica de los agentes (Coder, Synthesizer, Categorizer, AxialAnalyst)
├── data/               # Datos de entrada, intermedios y de salida
├── models/             # Modelos de datos Pydantic para validación y estructura
├── prompts/            # Prompts utilizados por los agentes de LLM
├── services/           # Servicios compartidos (LLM, Embeddings)
├── utils/              # Funciones de utilidad
├── main.py             # Punto de entrada para ejecutar el pipeline completo
├── orchestrator.py     # Orquesta el flujo de trabajo entre los agentes
├── preprocessor.py     # Script para convertir y preparar datos de entrada
├── requirements.txt    # Dependencias del proyecto
└── .env                # Archivo para variables de entorno (API Keys)
```

## Instalación

Sigue estos pasos para configurar tu entorno de desarrollo.

1.  **Clona el repositorio (si aplica):**

    ```bash
    git clone <url-del-repositorio>
    cd <nombre-del-repositorio>
    ```

2.  **Crea y activa un entorno virtual:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    ```

3.  **Instala las dependencias:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configura tu clave de API:**
    - Crea un archivo llamado `.env` en la raíz del proyecto.
    - Añade tu clave de API de Google al archivo:
      ```
      GOOGLE_API_KEY="tu_clave_aqui"
      ```

## Flujo de Trabajo y Uso

El sistema opera en un flujo de dos pasos principales.

### Paso 1: Preprocesar los Datos

Este paso convierte tu archivo Excel de entrada al formato que el sistema necesita. Solo necesitas ejecutarlo cuando tus datos de origen cambien.

1.  **Prepara tu archivo de entrada:**

    - Coloca tu archivo de datos en la carpeta `data/`. El nombre por defecto es `insights.xlsx`.
    - La hoja de cálculo debe contener las siguientes columnas **obligatorias**:
      - `ID`: Un identificador único para cada fragmento de texto.
      - `InsightText`: El texto cualitativo a analizar.
    - Opcionalmente, puedes incluir estas columnas para mejorar la trazabilidad:
      - `Method`: Método de recolección del dato (e.g., "Entrevista", "Encuesta").
      - `Source`: Origen del dato (e.g., "Cliente A", "Usuario B").

2.  **Ejecuta el script de preprocesamiento:**
    ```bash
    python preprocessor.py
    ```
    - Esto generará `data/data.jsonl`, que es la entrada para el pipeline de análisis.
    - Si las columnas opcionales existen, también creará `data/metadata.json` con la información de trazabilidad.

### Paso 2: Ejecutar el Pipeline de Análisis Completo

Este comando ejecuta todo el sistema de agentes para procesar los datos, desde la codificación hasta el análisis final.

1.  **Ejecuta el script principal:**

    ```bash
    python main.py
    ```

2.  **Salidas Generadas:**
    - `data/codebook.json`: El libro de códigos maestro, que contiene todos los códigos únicos, sus contadores y embeddings. Se actualiza en cada ejecución.
    - `data/categories.json`: Un archivo con las categorías conceptuales generadas y los códigos que agrupan.
    - `data/analysis_results.jsonl`: El resultado principal. Cada línea es un insight original enriquecido con una lista de los IDs de sus códigos unificados.
    - `data/axial_analysis_report.json`: El informe final del `AxialAnalystAgent`, que detalla las relaciones encontradas entre las categorías.

---

_Este `README.md` ha sido actualizado para reflejar la arquitectura y el flujo de trabajo actuales del proyecto._
