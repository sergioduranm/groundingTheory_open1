# Sistema de Agentes para Análisis Cualitativo con IA

Este proyecto implementa un sistema de múltiples agentes de IA diseñado para automatizar y escalar la fase de codificación abierta de la metodología de Teoría Fundamentada. El sistema procesa insights cualitativos desde un archivo Excel, genera códigos conceptuales, los unifica semánticamente para crear un libro de códigos maestro, y finalmente produce un archivo de resultados que mapea cada insight a sus códigos unificados correspondientes.

## Características Principales

- **Preprocesamiento de Datos:** Convierte archivos `.xlsx` a formato `.jsonl` listo para el análisis.
- **Generación de Códigos:** Un `CoderAgent` lee los insights y propone códigos abiertos iniciales.
- **Unificación Semántica:** Un `SynthesizerAgent` utiliza embeddings vectoriales para detectar duplicados semánticos, consolidando los códigos en un `codebook.json` maestro.
- **Orquestación Automatizada:** Un `Orchestrator` gestiona el flujo completo del pipeline de análisis con un solo comando.
- **Trazabilidad Completa:** El resultado final (`analysis_results.jsonl`) mantiene un vínculo claro entre cada insight original y sus IDs de códigos finales.

## Estructura del Proyecto

```
/
├── agents/             # Contiene la lógica de todos los agentes
├── data/               # Almacena los datos de entrada, intermedios y salida
├── main.py             # Script principal para ejecutar el pipeline de análisis
├── preprocessor.py     # Script para convertir Excel a JSONL
├── requirements.txt    # Dependencias del proyecto
└── .env                # Archivo para variables de entorno (no versionado)
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

El sistema opera en un flujo de dos pasos claros y deliberados.

### Paso 1: Preprocesar los Datos

Esta acción convierte tu archivo Excel en el formato que el sistema necesita. Solo necesitas ejecutar este paso cuando tus datos de origen cambien.

1.  **Prepara tu archivo de entrada:**
    - Coloca tu archivo de datos en la carpeta `data/`.
    - Asegúrate de que se llame `insights.xlsx`.
    - Confirma que contiene las columnas `ID` e `InsightText`.

2.  **Ejecuta el script de preprocesamiento:**
    ```bash
    python preprocessor.py
    ```
    Esto generará el archivo `data/data.jsonl`, que es la entrada para el pipeline principal.

### Paso 2: Ejecutar el Pipeline de Análisis

Este comando ejecuta el sistema completo de agentes para analizar los datos preprocesados.

1.  **Ejecuta el script principal:**
    ```bash
    python main.py
    ```

2.  **Salidas generadas:**
    - `data/codebook.json`: El libro de códigos maestro, con todos los códigos únicos, sus contadores y embeddings. Se actualiza en cada ejecución.
    - `data/analysis_results.jsonl`: El archivo de resultados final. Cada línea es un insight original enriquecido con una lista de los IDs de sus códigos unificados, listo para ser analizado.