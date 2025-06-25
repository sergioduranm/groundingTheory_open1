"""
Synthesizer-Auditor Agent for Grounded Theory Automation.

This agent manages and curates a central knowledge base (codebook.json) by identifying
and merging semantically duplicate codes using vector embeddings. This version is
optimized for performance and scalability.
"""

import json
import os
import uuid
from typing import List, Dict, Any, Optional, Set

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


class SynthesizerAgent:
    """
    Agente Sintetizador-Auditor optimizado para gestionar y curar la base de conocimiento.
    
    Implementa un caché en memoria para búsquedas O(1) y procesamiento por lotes
    para la generación de embeddings, garantizando alta eficiencia y escalabilidad.
    """
    
    def __init__(self, codebook_path: str = "data/codebook.json", similarity_threshold: float = 0.95):
        """
        Inicializa el SynthesizerAgent.
        
        Args:
            codebook_path: Ruta al archivo JSON del codebook.
            similarity_threshold: Umbral para considerar códigos como duplicados semánticos.
        """
        self.codebook_path = codebook_path
        self.similarity_threshold = similarity_threshold
        print("🚀 Inicializando SynthesizerAgent...")
        
        # El modelo de embeddings se carga una sola vez.
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Modelo de embeddings 'all-MiniLM-L6-v2' cargado.")
        
        self.codebook: Dict[str, List[Dict[str, Any]]] = {"codes": [], "categories": [], "memos": []}
        
        # --- OPTIMIZACIÓN: Cachés en memoria para acceso y cálculo rápido ---
        self.codes_by_id: Dict[str, Dict[str, Any]] = {} # Para búsquedas O(1)
        self.embedding_matrix: Optional[np.ndarray] = None # Matriz de embeddings cacheados
        self.ordered_code_ids: List[str] = [] # Lista de IDs en el mismo orden que la matriz

        self._load_codebook()

    def process_batch(self, new_code_labels: List[str]) -> None:
        """
        Procesa un lote de nuevos códigos de forma optimizada.
        
        Args:
            new_code_labels: Lista de etiquetas de nuevos códigos.
        """
        # Filtrar etiquetas vacías y obtener un conjunto de códigos únicos para procesar.
        unique_new_labels = {label.strip() for label in new_code_labels if label.strip()}
        
        # Identificar qué códigos son realmente nuevos (no existen como strings exactos)
        existing_labels = {code['label'] for code in self.codebook['codes']}
        codes_to_embed = list(unique_new_labels - existing_labels)

        if codes_to_embed:
            # --- OPTIMIZACIÓN: Generar embeddings para todos los códigos nuevos en un solo lote ---
            print(f"🧠 Generando embeddings para {len(codes_to_embed)} nuevos códigos...")
            new_embeddings = self.model.encode(codes_to_embed, show_progress_bar=False)
            
            for label, embedding in zip(codes_to_embed, new_embeddings):
                # Comprobar si hay un duplicado semántico
                existing_id = self._find_semantic_duplicate(embedding)
                if existing_id:
                    self._update_code_count(existing_id)
                else:
                    self._add_new_code(label, embedding)
        
        # Actualizar contadores para códigos que ya existían como strings exactos
        for label in unique_new_labels.intersection(existing_labels):
            code_id_to_update = next((code['id'] for code in self.codebook['codes'] if code['label'] == label), None)
            if code_id_to_update:
                self._update_code_count(code_id_to_update)

        self._save_codebook()
        print(f"✅ Lote procesado. Codebook tiene ahora {len(self.codebook['codes'])} códigos únicos.")

    def _load_codebook(self) -> None:
        """Carga el codebook y reconstruye el caché en memoria."""
        if os.path.exists(self.codebook_path):
            try:
                with open(self.codebook_path, 'r', encoding='utf-8') as file:
                    self.codebook = json.load(file)
                print(f"📚 Codebook cargado desde {self.codebook_path}. {len(self.codebook['codes'])} códigos encontrados.")
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️  Error al cargar codebook: {e}. Se usará un codebook vacío.")
                self.codebook = {"codes": [], "categories": [], "memos": []}
        else:
            print("ℹ️  No se encontró codebook, se creará uno nuevo.")
        
        self._rebuild_internal_cache()

    def _rebuild_internal_cache(self) -> None:
        """
        (Re)construye las estructuras de datos en memoria para un rendimiento óptimo.
        Esta función es clave para las optimizaciones.
        """
        # --- OPTIMIZACIÓN #1: Diccionario para búsqueda O(1) ---
        self.codes_by_id = {code['id']: code for code in self.codebook['codes']}
        
        if not self.codebook['codes']:
            return

        # --- OPTIMIZACIÓN #2: Matriz de embeddings cacheados ---
        embeddings = [code['embedding'] for code in self.codebook['codes']]
        self.embedding_matrix = np.array(embeddings)
        self.ordered_code_ids = [code['id'] for code in self.codebook['codes']]
        print("⚡️ Caché interno reconstruido para acceso rápido.")

    def _save_codebook(self) -> None:
        """Guarda el estado actual del codebook en el archivo JSON."""
        try:
            os.makedirs(os.path.dirname(self.codebook_path), exist_ok=True)
            with open(self.codebook_path, 'w', encoding='utf-8') as file:
                json.dump(self.codebook, file, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"❌ Error crítico: no se pudo guardar el codebook en {self.codebook_path}. Error: {e}")

    def _find_semantic_duplicate(self, new_embedding: np.ndarray) -> Optional[str]:
        """
        Encuentra duplicados usando la matriz de embeddings cacheados.
        
        Args:
            new_embedding: El vector del nuevo código a comparar.
            
        Returns:
            El ID del código existente si se encuentra un duplicado, si no None.
        """
        if self.embedding_matrix is None or self.embedding_matrix.shape[0] == 0:
            return None
        
        # Reshape para el cálculo de similitud
        new_embedding = new_embedding.reshape(1, -1)
        
        # Calcular similitud contra toda la matriz cacheadada. Operación muy rápida.
        similarities = cosine_similarity(new_embedding, self.embedding_matrix)[0]
        
        max_similarity_idx = np.argmax(similarities)
        if similarities[max_similarity_idx] >= self.similarity_threshold:
            return self.ordered_code_ids[max_similarity_idx]
        
        return None

    def _add_new_code(self, label: str, embedding: np.ndarray) -> None:
        """
        Añade un nuevo código al codebook y actualiza el caché en memoria.
        
        Args:
            label: La etiqueta del nuevo código.
            embedding: El embedding pre-calculado para el nuevo código.
        """
        new_id = str(uuid.uuid4())
        new_code = {
            "id": new_id,
            "label": label,
            "count": 1,
            "embedding": embedding.tolist()
        }
        
        # Actualizar estructuras principales
        self.codebook['codes'].append(new_code)
        self.codes_by_id[new_id] = new_code
        self.ordered_code_ids.append(new_id)

        # Actualizar la matriz de embeddings cacheados de forma eficiente
        if self.embedding_matrix is None:
            self.embedding_matrix = embedding.reshape(1, -1)
        else:
            self.embedding_matrix = np.vstack([self.embedding_matrix, embedding])
    
    def _update_code_count(self, code_id: str) -> None:
        """
        Incrementa el contador de un código existente usando acceso O(1).
        
        Args:
            code_id: El ID del código a actualizar.
        """
        # --- OPTIMIZACIÓN: Acceso directo por diccionario ---
        if code_id in self.codes_by_id:
            self.codes_by_id[code_id]['count'] += 1
        else:
            print(f"⚠️  Advertencia: Se intentó actualizar el contador para el ID '{code_id}' no encontrado en caché.")
