from app.knowledge.document_parser import DocumentParser

def test_parse_sample_txt():
    text = DocumentParser().parse("data/documents/sample_knowledge/agp_coaching_guide.txt")
    assert "Advisor Growth Program" in text
