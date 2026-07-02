from pathlib import Path

def test_preloaded_chroma_folder_exists():
    assert Path("data/chroma").exists()
    assert Path("data/chroma/preloaded_chroma_manifest.json").exists()
