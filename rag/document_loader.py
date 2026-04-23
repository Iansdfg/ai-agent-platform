from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class Document:
    content: str
    metadata: Dict[str, Any]


class DocumentLoader:
    SUPPORTED_EXTENSIONS = {".txt", ".md"}

    def load_documents(self, docs_dir: str) -> List[Document]:
        documents: List[Document] = []

        for file_path in Path(docs_dir).glob("*"):
            if file_path.suffix not in self.SUPPORTED_EXTENSIONS:
                continue

            content = file_path.read_text(encoding="utf-8").strip()

            if not content:
                continue

            documents.append(
                Document(
                    content=content,
                    metadata={
                        "source": str(file_path),
                        "file_name": file_path.name,
                        "file_type": file_path.suffix.lstrip("."),
                    },
                )
            )

        return documents