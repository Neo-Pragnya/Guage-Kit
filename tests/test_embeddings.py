from guage_kit.metrics.embeddings import STS_Spearman, kNN_accuracy
import pytest

def test_sts_spearman():
    # Sample data for testing STS Spearman metric
    predictions = ["The cat sits on the mat.", "The dog is in the fog."]
    references = ["The cat is on the mat.", "The dog is in the mist."]
    
    score = STS_Spearman(predictions, references)
    
    assert isinstance(score, float), "Score should be a float"
    assert 0 <= score <= 1, "Score should be between 0 and 1"

def test_knn_accuracy():
    # Sample data for testing k-NN accuracy metric
    predicted_labels = [0, 1, 1, 0, 1]
    true_labels = [0, 1, 0, 0, 1]
    
    accuracy = kNN_accuracy(predicted_labels, true_labels)
    
    assert isinstance(accuracy, float), "Accuracy should be a float"
    assert 0 <= accuracy <= 1, "Accuracy should be between 0 and 1"