from app.knowledge.chunking import TextChunker

def test_chunking_creates_chunks():
    text = "This is a sample document. " * 200
    chunks = TextChunker(chunk_size=200, overlap=20).chunk_text("DOC_TEST", text)
    assert len(chunks) > 1
    assert chunks[0].document_id == "DOC_TEST"
