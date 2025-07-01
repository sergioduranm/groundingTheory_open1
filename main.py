#!/usr/bin/env python3
"""
Sistema de Agentes para Análisis Cualitativo
============================================

Este módulo implementa un sistema de agentes de IA para análisis cualitativo
utilizando el ADK de Google Generative AI.
"""

# PRIMERO: Cargar las variables de entorno. Esto es crucial.
# Debe hacerse antes de importar cualquier otro módulo del proyecto que pueda usar esas variables.
from dotenv import load_dotenv
load_dotenv()

# AHORA: Importar el resto de módulos
import logging
import os
from typing import Optional
from orchestrator import Orchestrator
import argparse

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """
    Punto de entrada principal para ejecutar las tareas de orquestación.
    """
    parser = argparse.ArgumentParser(
        description="Corre el pipeline de análisis de Grounded Theory o una de sus partes."
    )
    parser.add_argument(
        'task',
        choices=['pipeline', 'narrate'],
        default='pipeline',
        nargs='?', # El argumento es opcional, 'pipeline' es el default
        help="Especifica la tarea a ejecutar: 'pipeline' para el proceso completo, 'narrate' para generar las narrativas."
    )
    args = parser.parse_args()

    try:
        # 1. Crear una instancia del orquestador
        pipeline_orchestrator = Orchestrator()

        # 2. Ejecutar la tarea seleccionada
        if args.task == 'narrate':
            logging.info("Iniciando la tarea de narración...")
            pipeline_orchestrator.run_narrator()
        else:
            logging.info("Iniciando el pipeline completo...")
            pipeline_orchestrator.run_pipeline()

    except Exception as e:
        logging.error(f"❌ Ocurrió un error fatal durante la ejecución: {e}", exc_info=True)


if __name__ == "__main__":
    main()
