# backend/diagram_utils.py

import zlib
from typing import Literal

def _encode6bit(b):
    if b < 10: return chr(48 + b)
    b -= 10
    if b < 26: return chr(65 + b)
    b -= 26
    if b < 26: return chr(97 + b)
    b -= 26
    if b == 0: return '-'
    if b == 1: return '_'
    return '?'

def _append3bytes(b1, b2, b3):
    return (
        _encode6bit((b1 >> 2) & 0x3F) +
        _encode6bit(((b1 & 0x3) << 4 | b2 >> 4) & 0x3F) +
        _encode6bit(((b2 & 0xF) << 2 | b3 >> 6) & 0x3F) +
        _encode6bit(b3 & 0x3F)
    )

def encode_plantuml(uml_text: str) -> str:
    data = zlib.compress(uml_text.encode("utf-8"))[2:-4]
    result = ""
    for i in range(0, len(data), 3):
        b1 = data[i]
        b2 = data[i+1] if i+1 < len(data) else 0
        b3 = data[i+2] if i+2 < len(data) else 0
        result += _append3bytes(b1, b2, b3)
    return result

def plantuml_image_url(code: str) -> str:
    return f"https://www.plantuml.com/plantuml/png/{encode_plantuml(code)}"

def extract_diagrams_from_docs(docs: list) -> list:
    """
    Pull diagram_code out of chunk metadata.
    The code lives in metadata, NOT page_content — that's the key fix.
    """
    diagrams = []
    seen = set()

    for doc in docs:
        meta = getattr(doc, "metadata", {}) or {}
        content_type = meta.get("content_type", "")
        diagram_code = meta.get("diagram_code", "")
        source = meta.get("source_name", "")
        title = meta.get("diagram_title", source)

        diagram_index = meta.get("diagram_index")
        diagram_key = (
            source,
            content_type,
            diagram_index,
            diagram_code[:80],
        )

        if not diagram_code or diagram_key in seen:
            continue

        if content_type == "plantuml":
            diagrams.append({
                "type": "plantuml",
                "code": diagram_code,
                "title": title,
                "diagramIndex": diagram_index,
                "imageUrl": plantuml_image_url(diagram_code),
                "sourceName": source,
            })
            seen.add(diagram_key)

        elif content_type == "mermaid":
            diagrams.append({
                "type": "mermaid",
                "code": diagram_code,
                "title": title,
                "diagramIndex": diagram_index,
                "sourceName": source,
            })
            seen.add(diagram_key)

    return diagrams

DiagramRequestType = Literal["mermaid", "plantuml", "all", None]

_GENERIC_DIAGRAM_KEYWORDS = {
    "diagram", "flowchart", "sequence diagram", "architecture diagram",
    "visual", "draw", "show the flow", "show the diagram",
    "show architecture", "show sequence", "show process flow",
    "flow diagram",
}


def detect_diagram_request_type(question: str) -> DiagramRequestType:
    lowered = str(question or "").lower()
    if not lowered.strip():
        return None

    if "mermaid" in lowered:
        return "mermaid"

    if "plantuml" in lowered or "puml" in lowered:
        return "plantuml"

    if "uml" in lowered:
        return "plantuml"

    if any(keyword in lowered for keyword in _GENERIC_DIAGRAM_KEYWORDS):
        return "all"

    return None
