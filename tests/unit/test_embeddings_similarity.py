from app.embeddings.similarity_engine import SimilarityEngine


def test_cosine_similarity():
    score = SimilarityEngine.cosine([1, 0], [1, 0])
    assert round(score, 4) == 1.0
