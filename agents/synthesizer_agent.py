# agents/synthesizer_agent.py

import uuid
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from agents.embedding_client import EmbeddingClient
from agents.codebook_repository import CodebookRepository

# Usamos el mismo logger configurado en el cliente para consistencia
logger = logging.getLogger(__name__)

class SynthesizerAgent:
    """
    Agente Sintetizador-Auditor simplificado.
    Detecta duplicados, actualiza el codebook y devuelve un mapa de traducción.
    """
    def __init__(self, repository: CodebookRepository, client: EmbeddingClient, similarity_threshold: float = 0.90):
        logger.info("🚀 Inicializando SynthesizerAgent...")
        self.repository = repository
        self.client = client
        self.similarity_threshold = similarity_threshold
        
        self.codebook = self.repository.load()
        # Asumiendo que el modelo de embedding de Google usa 768 dimensiones.
        self.embedding_dim = self.codebook.get('metadata', {}).get('embedding_dim', 768) 
        
        self._ensure_metadata_structure()
        self._rebuild_internal_caches()
        logger.info("✅ SynthesizerAgent listo.")

    def _ensure_metadata_structure(self):
        """Asegura que la estructura de metadata exista en el codebook."""
        if 'metadata' not in self.codebook:
            self.codebook['metadata'] = {}
        
        if 'embedding_dim' not in self.codebook['metadata']:
            self.codebook['metadata']['embedding_dim'] = self.embedding_dim
            
        logger.info(f"📊 Metadata inicializada: embedding_dim={self.codebook['metadata']['embedding_dim']}")

    def _rebuild_internal_caches(self):
        """Construye cachés en memoria para un rendimiento O(1) y O(N) rápido."""
        logger.info("⚡️ Construyendo cachés internos para acceso rápido...")
        self.codes_by_id: Dict[str, Dict] = {c['id']: c for c in self.codebook.get('codes', [])}
        self.label_to_id: Dict[str, str] = {c['label']: c['id'] for c in self.codebook.get('codes', [])}
        
        codes_with_embeddings = [c for c in self.codebook.get('codes', []) if 'embedding' in c and isinstance(c['embedding'], list) and len(c['embedding']) > 0]
        
        if codes_with_embeddings:
            self.ordered_code_ids = [c['id'] for c in codes_with_embeddings]
            self.embedding_matrix = np.array([c['embedding'] for c in codes_with_embeddings])
        else:
            self.ordered_code_ids = []
            self.embedding_matrix = np.empty((0, self.embedding_dim))
        logger.info(f"⚡️ Cachés construidos. Matriz de embeddings tiene {self.embedding_matrix.shape[0]} vectores.")

    def process_batch(self, new_code_labels: List[str]) -> Dict[str, str]:
        """Procesa un lote de nuevas etiquetas de código y devuelve un mapa de traducción."""
        
        # Inicializamos el mapa que será nuestro valor de retorno.
        translation_map: Dict[str, str] = {}
        
        unique_labels = {label.strip() for label in new_code_labels if isinstance(label, str) and label.strip()}
        
        codes_to_create = []
        
        for label in unique_labels:
            if label in self.label_to_id:
                unified_id = self.label_to_id[label]
                self._update_code_count(unified_id)
                # Poblamos el mapa para los duplicados exactos.
                translation_map[label] = unified_id
            else:
                codes_to_create.append(label)
        
        if codes_to_create:
            # Pasamos el mapa para que sea poblado por el método secuencial.
            self._process_new_codes_sequentially(codes_to_create, translation_map)

        self.repository.save(self.codebook)
        logger.info(f"✅ Lote procesado. Codebook tiene ahora {len(self.codebook['codes'])} códigos únicos.")
        
        # Devolvemos el mapa de traducción completo.
        return translation_map

    def _process_new_codes_sequentially(self, labels: List[str], translation_map: Dict[str, str]):
        """
        Procesa nuevos códigos uno por uno, poblando el mapa de traducción.
        """
        logger.info(f"🧠 Procesando secuencialmente {len(labels)} nuevos códigos candidatos...")
        
        if not labels:
            return

        all_embeddings = self.client.get_embeddings(labels)

        for label, embedding_list in zip(labels, all_embeddings):
            if not embedding_list:
                logger.warning(f"Se omitió el código '{label}' porque no se pudo generar su embedding.")
                continue

            embedding = np.array(embedding_list)
            existing_id = self._find_semantic_duplicate(embedding)
            
            if existing_id:
                self._update_code_count(existing_id)
                # Se encontró un duplicado semántico. Registramos la traducción.
                translation_map[label] = existing_id
            else:
                new_id = f"code_{uuid.uuid4()}"
                new_code_obj = {"id": new_id, "label": label, "count": 1, "embedding": embedding_list}
                self._add_single_code_to_cache(new_code_obj, embedding)
                # Se creó un código nuevo. Registramos la traducción.
                translation_map[label] = new_id
                
    def _add_single_code_to_cache(self, code: Dict, embedding: np.ndarray):
        """Añade un único código nuevo a todos los cachés en memoria."""
        logger.info(f"➕ Añadiendo nuevo código único al codebook: '{code['label']}'")
        self.codebook['codes'].append(code)
        self.codes_by_id[code['id']] = code
        self.label_to_id[code['label']] = code['id']
        self.ordered_code_ids.append(code['id'])
        
        if self.embedding_matrix.shape[0] == 0:
            self.embedding_matrix = embedding.reshape(1, -1)
        else:
            self.embedding_matrix = np.vstack([self.embedding_matrix, embedding])

    def _find_semantic_duplicate(self, new_embedding: np.ndarray) -> Optional[str]:
        """Encuentra duplicados semánticos usando la matriz de embeddings actual."""
        if self.embedding_matrix.shape[0] == 0:
            return None
        
        similarities = cosine_similarity(new_embedding.reshape(1, -1), self.embedding_matrix)[0]
        max_similarity_idx = np.argmax(similarities)
        
        if similarities[max_similarity_idx] >= self.similarity_threshold:
            return self.ordered_code_ids[max_similarity_idx]
        return None

    def _update_code_count(self, code_id: str):
        """Incrementa el contador de un código existente."""
        if code_id in self.codes_by_id:
            logger.info(f"🔄 Código duplicado ('{self.codes_by_id[code_id]['label']}') encontrado. Incrementando contador para ID: {code_id}")
            self.codes_by_id[code_id]['count'] += 1
        else:
            logger.warning(f"Advertencia de integridad: Se intentó actualizar el ID '{code_id}' no encontrado en caché.")
