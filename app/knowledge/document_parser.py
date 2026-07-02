from __future__ import annotations

from pathlib import Path


class DocumentParser:
    SUPPORTED_TEXT_SUFFIXES = {".txt", ".md", ".csv", ".json", ".html"}

    def parse(self, path: str | Path) -> str:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        suffix = file_path.suffix.lower()
        if suffix in self.SUPPORTED_TEXT_SUFFIXES:
            return file_path.read_text(encoding="utf-8", errors="ignore")

        if suffix == ".pdf":
            return f"[PDF placeholder extraction for {file_path.name}]\nInstall a PDF parser later."

        if suffix in {".docx", ".pptx"}:
            return f"[Office placeholder extraction for {file_path.name}]\nInstall DOCX/PPTX parsing later."

        raise ValueError(f"Unsupported document suffix: {suffix}")
