import os
import logging
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any

logger = logging.getLogger(__name__)

# Default configurations
DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_DIMENSION = 384

_embedder_instance = None

class SentenceTransformerEmbedder:
    """
    Singleton wrapper for sentence-transformers model execution.
    Handles lazy initialization, vector generation, dimension validation, and graceful exception handling.
    """
    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL_NAME", DEFAULT_MODEL_NAME)
        self.expected_dimension = int(os.getenv("EMBEDDING_DIMENSION", str(DEFAULT_DIMENSION)))
        self.device = device or os.getenv("EMBEDDING_DEVICE", "cpu")
        self.model = None
        self._load_error = None

    def _load_model(self):
        if self.model is None and self._load_error is None:
            try:
                logger.info(f"Loading SentenceTransformer model: {self.model_name} on device: {self.device}")
                from sentence_transformers import SentenceTransformer
                cache_folder = os.getenv("TRANSFORMERS_CACHE", None)
                self.model = SentenceTransformer(self.model_name, device=self.device, cache_folder=cache_folder)
                logger.info(f"Successfully loaded model {self.model_name}")
            except Exception as e:
                self._load_error = str(e)
                logger.error(f"Failed to load SentenceTransformer model '{self.model_name}': {e}", exc_info=True)

    def generate_embedding(self, text: str) -> Tuple[Optional[List[float]], Dict[str, Any]]:
        """
        Generates a 384-dimensional vector embedding for the input text.

        Returns:
            Tuple[Optional[List[float]], Dict[str, Any]]:
                (vector, metadata_dict)
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        char_count = len(text) if text else 0

        metadata = {
            "model_name": self.model_name,
            "dimension": self.expected_dimension,
            "status": "failed",
            "char_count": char_count,
            "error_message": None,
            "generated_at": now_iso
        }

        if not text or not text.strip():
            metadata["error_message"] = "Embedding text is empty."
            logger.warning("Skipping vector generation: input text is empty.")
            return None, metadata

        self._load_model()

        if self._load_error:
            metadata["error_message"] = f"Model load error: {self._load_error}"
            return None, metadata

        try:
            vector_np = self.model.encode(text, convert_to_numpy=True, show_progress_bar=False)
            vector = vector_np.tolist()

            if len(vector) != self.expected_dimension:
                err_msg = f"Vector dimension mismatch: expected {self.expected_dimension}, got {len(vector)}"
                logger.critical(err_msg)
                metadata["error_message"] = err_msg
                return None, metadata

            metadata["status"] = "success"
            return vector, metadata

        except Exception as e:
            logger.error(f"Vector inference failed for input text: {e}", exc_info=True)
            metadata["error_message"] = f"Inference exception: {str(e)}"
            return None, metadata


def get_embedder() -> SentenceTransformerEmbedder:
    """
    Returns the singleton instance of SentenceTransformerEmbedder.
    """
    global _embedder_instance
    if _embedder_instance is None:
        _embedder_instance = SentenceTransformerEmbedder()
    return _embedder_instance


def generate_embedding(text: str) -> Tuple[Optional[List[float]], Dict[str, Any]]:
    """
    Convenience function for embedding generation.
    """
    embedder = get_embedder()
    return embedder.generate_embedding(text)
