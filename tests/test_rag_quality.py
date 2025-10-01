import pytest
from guage_kit.metrics.rag_quality import calculate_faithfulness, calculate_answer_relevancy

def test_calculate_faithfulness():
    # Example input for faithfulness calculation
    context = "The capital of France is Paris."
    generated_answer = "Paris is the capital of France."
    
    result = calculate_faithfulness(context, generated_answer)
    
    # Assert that the faithfulness score is as expected
    assert result >= 0.0  # Assuming the score is non-negative
    assert result <= 1.0  # Assuming the score is between 0 and 1

def test_calculate_answer_relevancy():
    # Example input for answer relevancy calculation
    query = "What is the capital of France?"
    answer = "Paris"
    
    result = calculate_answer_relevancy(query, answer)
    
    # Assert that the answer relevancy score is as expected
    assert result >= 0.0  # Assuming the score is non-negative
    assert result <= 1.0  # Assuming the score is between 0 and 1

# Add more tests as needed for additional functionality in rag_quality.py