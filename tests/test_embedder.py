import pytest
from unittest import mock
import numpy as np
from src.embedding.embedder import generate_embedding, SentenceTransformerEmbedder

def test_generate_embedding_empty_text():
    vector, metadata = generate_embedding("")
    assert vector is None
    assert metadata["status"] == "failed"
    assert "empty" in metadata["error_message"].lower()

@mock.patch("sentence_transformers.SentenceTransformer")
def test_generate_embedding_success(mock_st_class):
    # Mock model encode method to return 384 dummy float array
    mock_model_instance = mock.MagicMock()
    mock_model_instance.encode.return_value = np.zeros(384, dtype=np.float32)
    mock_st_class.return_value = mock_model_instance

    embedder = SentenceTransformerEmbedder(model_name="dummy-model")
    embedder.model = mock_model_instance

    vector, metadata = embedder.generate_embedding("Skills: Python, FastAPI")

    assert vector is not None
    assert len(vector) == 384
    assert metadata["status"] == "success"
    assert metadata["dimension"] == 384
    assert metadata["model_name"] == "dummy-model"

def test_generate_embedding_model_load_failure():
    embedder = SentenceTransformerEmbedder(model_name="nonexistent-model-xyz")
    embedder._load_error = "Model download failed"

    vector, metadata = embedder.generate_embedding("Skills: Python")
    assert vector is None
    assert metadata["status"] == "failed"
    assert "Model download failed" in metadata["error_message"]
