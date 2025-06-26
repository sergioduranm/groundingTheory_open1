#!/usr/bin/env python3
"""
Sistema de Agentes para Análisis Cualitativo
============================================

Este módulo implementa un sistema de agentes de IA para análisis cualitativo
utilizando el ADK de Google Generative AI.
"""

import logging
from typing import Optional
from orchestrator import Orchestrator

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """
    Punto de entrada principal para ejecutar el pipeline de procesamiento de insights.
    """
    try:
        # 1. Crear una instancia del orquestador
        #    La inicialización se encarga de cargar dependencias y configuración.
        pipeline_orchestrator = Orchestrator()

        # 2. Ejecutar el pipeline completo
        pipeline_orchestrator.run_pipeline()

    except Exception as e:
        print(f"❌ Ocurrió un error fatal durante la ejecución del pipeline: {e}")


if __name__ == "__main__":
    main()
