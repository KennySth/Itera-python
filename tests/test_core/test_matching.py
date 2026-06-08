import pytest
from app.core.matching import calculate_cosine_similarity

def test_cosine_similarity_identical_vectors():
    vec_a = [1.0, 2.0, 3.0]
    vec_b = [1.0, 2.0, 3.0]
    # Identical vectors should have a cosine similarity of 1.0 (or very close to it)
    score = calculate_cosine_similarity(vec_a, vec_b)
    assert score == pytest.approx(1.0, 0.001)

def test_cosine_similarity_orthogonal_vectors():
    vec_a = [1.0, 0.0]
    vec_b = [0.0, 1.0]
    # Orthogonal vectors should have a cosine similarity of 0.0
    score = calculate_cosine_similarity(vec_a, vec_b)
    assert score == pytest.approx(0.0, 0.001)

def test_cosine_similarity_opposite_vectors():
    vec_a = [1.0, 1.0]
    vec_b = [-1.0, -1.0]
    # Opposite vectors should have a cosine similarity of -1.0
    score = calculate_cosine_similarity(vec_a, vec_b)
    assert score == pytest.approx(-1.0, 0.001)

def test_cosine_similarity_different_lengths():
    vec_a = [1.0, 2.0, 3.0]
    vec_b = [1.0, 2.0]
    # Different lengths should safely return 0.0 without crashing
    score = calculate_cosine_similarity(vec_a, vec_b)
    assert score == 0.0

def test_cosine_similarity_empty_vectors():
    assert calculate_cosine_similarity([], [1.0]) == 0.0
    assert calculate_cosine_similarity([1.0], []) == 0.0
    assert calculate_cosine_similarity([], []) == 0.0
