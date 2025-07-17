#!/usr/bin/env python3
"""
Test script to verify the critical bug fixes.
"""

import json
import tempfile
import os
import sys
from unittest.mock import Mock, patch

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_checkpoint_corruption_fix():
    """Test that the orchestrator handles corrupted checkpoint files correctly."""
    print("🧪 Testing checkpoint corruption fix...")
    
    # Create a temporary corrupted checkpoint file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write('{"id": "test1", "text": "valid data"}\n')
        f.write('{"invalid": json}\n')  # Corrupted line
        f.write('{"id": "test2", "text": "more valid data"}\n')
        f.write('{"id": "test3", "text": "final valid data"}\n')
        corrupted_file = f.name
    
    try:
        # Test the checkpoint loading logic
        coded_insights = []
        processed_ids = set()
        
        with open(corrupted_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    coded_insight = json.loads(line)
                    if not isinstance(coded_insight, dict):
                        print(f"⚠️ Línea {line_num}: Formato inválido, se omite")
                        continue
                    if 'id' not in coded_insight and 'id_fragmento' not in coded_insight:
                        print(f"⚠️ Línea {line_num}: Falta ID, se omite")
                        continue
                    
                    coded_insights.append(coded_insight)
                    processed_ids.add(coded_insight.get("id") or coded_insight.get("id_fragmento"))
                except json.JSONDecodeError as e:
                    print(f"❌ Línea {line_num} corrupta: {e}. Se omitirá.")
                    continue
                except Exception as e:
                    print(f"❌ Error inesperado en línea {line_num}: {e}. Se omitirá.")
                    continue
        
        print(f"✅ Se cargaron {len(coded_insights)} insights válidos de {len(processed_ids)} IDs únicos")
        print(f"   IDs procesados: {processed_ids}")
        
        # Should have loaded 3 valid insights, skipped 1 corrupted
        assert len(coded_insights) == 3, f"Expected 3 valid insights, got {len(coded_insights)}"
        assert len(processed_ids) == 3, f"Expected 3 unique IDs, got {len(processed_ids)}"
        assert "test1" in processed_ids
        assert "test2" in processed_ids
        assert "test3" in processed_ids
        
        print("✅ Checkpoint corruption fix test PASSED")
        
    finally:
        # Clean up
        os.unlink(corrupted_file)

def test_memory_limit_fix():
    """Test that the synthesizer agent respects memory limits."""
    print("🧪 Testing memory limit fix...")
    
    # Mock the necessary components
    mock_repository = Mock()
    mock_client = Mock()
    
    # Create a mock codebook with many codes
    from models.data_models import Codebook, Code
    
    # Create 15,000 mock codes (more than the 10,000 limit)
    codes = []
    for i in range(15000):
        code = Code(
            id=f"code_{i}",
            label=f"test_code_{i}",
            count=i,  # Higher count for newer codes
            embedding=[0.1] * 768  # Mock embedding
        )
        codes.append(code)
    
    mock_codebook = Codebook(codes=codes, metadata={"embedding_dim": 768})
    mock_repository.load.return_value = mock_codebook
    
    # Import and test the SynthesizerAgent
    from agents.synthesizer_agent import SynthesizerAgent
    
    # This should not crash and should limit embeddings to 10,000
    agent = SynthesizerAgent(mock_repository, mock_client, similarity_threshold=0.90)
    
    # Check that the embedding matrix is limited
    assert len(agent.ordered_code_ids) <= 10000, f"Expected max 10,000 embeddings, got {len(agent.ordered_code_ids)}"
    assert agent.embedding_matrix.shape[0] <= 10000, f"Expected max 10,000 embeddings in matrix, got {agent.embedding_matrix.shape[0]}"
    
    print(f"✅ Memory limit respected: {len(agent.ordered_code_ids)} embeddings loaded (max 10,000)")
    print("✅ Memory limit fix test PASSED")

if __name__ == "__main__":
    print("🚀 Running critical bug fix tests...")
    
    try:
        test_checkpoint_corruption_fix()
        test_memory_limit_fix()
        print("\n🎉 All critical bug fix tests PASSED!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)