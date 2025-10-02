"""Basic tests for Guage-Kit core functionality."""

import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_schemas_validation():
    """Test that schemas work properly."""
    from guage_kit.schemas.core import Query, Generation, EvalSample
    
    # Test schema creation
    query = Query(id="q1", prompt="Test prompt", references=["Test reference"])
    generation = Generation(query_id="q1", text="Test response", model="test-model")
    sample = EvalSample(query=query, generation=generation)
    
    # Test data access
    assert sample.query.id == "q1"
    assert sample.generation.text == "Test response"


def test_package_version():
    """Test that package version is accessible."""
    import guage_kit
    assert hasattr(guage_kit, '__version__')
    assert guage_kit.__version__ == "0.1.0"


def test_cli_module_exists():
    """Test that CLI module can be imported."""
    from guage_kit import cli
    assert hasattr(cli, 'main')


def test_package_version():
    """Test that package version is accessible."""
    import guage_kit
    assert hasattr(guage_kit, '__version__')
    assert guage_kit.__version__ == "0.1.0"