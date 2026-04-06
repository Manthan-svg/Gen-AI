from datetime import datetime
import os
import re
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pdf2image import convert_from_path
from langchain.schema import Document
from io import BytesIO
import base64
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from PIL import Image


load_dotenv()

class DataIngestor:
    def __init__(self):
        self.spliters = RecursiveCharacterTextSplitter(chunk_size=3000, chunk_overlap=250)
        self.llm =ChatGroq( 
            temperature=0,
            model_name="meta-llama/llama-4-scout-17b-16e-instruct",
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        
    def _convert_to_base64_(self,pil_image):
        buffered = BytesIO()
        
        pil_image.save(buffered,format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

    def _clean_doc_text(self, text: str) -> str:
        if not text:
            return ""
        # Remove embedded nulls from PDF extraction (breaks embeddings/LLM)
        return text.replace("\x00", "")
    
    def audit_image(self, base64img):
        # We define the content as a single list of dictionaries
        human_content = [
            {
                "type": "text",
                "text": (
                    "This is a business document image. Extract the content in a retrieval-friendly format. "
                    "Preserve exact wording where visible."
                )
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64img}" 
                }
            }
        ]

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are performing OCR for enterprise document retrieval.\n"
             "Return plain text only.\n"
             "Rules:\n"
             "1. Extract all visible text as faithfully as possible.\n"
             "2. Keep names, IDs, dates, amounts, headings, and labels exactly when readable.\n"
             "3. If the image contains a table, rewrite it as lines with column labels.\n"
             "4. If the image contains signatures or stamps, mention them in one short line.\n"
             "5. Do not add commentary like 'this image appears to show'.\n"
             "6. If some text is unreadable, write '[unreadable]'."),
            ("human", human_content) # This is now a 2-tuple: (role, list_content)
        ])
        
        chain = prompt | self.llm
        
        # Note: We don't need to pass image_data in invoke because it's already 
        # inside the human_content variable above.
        response = chain.invoke({})
        
        return response.content
    
    def _extract_plantuml_blocks(self, text: str) -> list[str]:
        return [
            match.group(1).strip()
            for match in re.finditer(r"(@startuml[\s\S]*?@enduml)", text, re.IGNORECASE)
        ]

    def _extract_mermaid_blocks(self, text: str) -> list[str]:
        return [
            match.group(1).strip()
            for match in re.finditer(r"```mermaid\s*([\s\S]*?)```", text, re.IGNORECASE)
        ]

    def _looks_like_raw_mermaid(self, text: str) -> bool:
        stripped = str(text or "").strip()
        if not stripped:
            return False
        mermaid_starters = (
            "graph ",
            "flowchart ",
            "sequenceDiagram",
            "classDiagram",
            "stateDiagram",
            "erDiagram",
            "journey",
            "gantt",
            "pie ",
            "mindmap",
            "timeline",
            "gitGraph",
            "requirementDiagram",
            "c4Context",
            "c4Container",
            "c4Component",
            "c4Dynamic",
            "c4Deployment",
        )
        return stripped.startswith(mermaid_starters)

    def _strip_diagram_blocks(self, text: str) -> str:
        without_puml = re.sub(r"@startuml[\s\S]*?@enduml", " ", text, flags=re.IGNORECASE)
        without_mermaid = re.sub(r"```mermaid\s*[\s\S]*?```", " ", without_puml, flags=re.IGNORECASE)
        return re.sub(r"\n{3,}", "\n\n", without_mermaid).strip()

    def _sanitize_metadata(self, metadata: dict) -> dict:
        return {key: value for key, value in metadata.items() if value is not None}

    def _build_diagram_docs(self, docs: list[Document], file_name: str, ext: str, upload_time: str) -> list[Document]:
        diagram_docs = []

        for source_doc in docs:
            page = (getattr(source_doc, "metadata", {}) or {}).get("page")
            raw_text = self._clean_doc_text(source_doc.page_content)

            plantuml_blocks = self._extract_plantuml_blocks(raw_text)
            mermaid_blocks = self._extract_mermaid_blocks(raw_text)

            if ext in {".mmd", ".mermaid"} and self._looks_like_raw_mermaid(raw_text):
                mermaid_blocks = mermaid_blocks or [raw_text.strip()]

            for idx, code in enumerate(plantuml_blocks, start=1):
                title = self._extract_puml_title(code)
                diagram_docs.append(Document(
                    page_content=(
                        f"Diagram title: {title}\n"
                        f"Diagram type: PlantUML\n"
                        f"Source file: {file_name}\n"
                        f"{code}"
                    ),
                    metadata=self._sanitize_metadata({
                        "page": page,
                        "content_type": "plantuml",
                        "diagram_code": code,
                        "diagram_title": title,
                        "diagram_index": idx,
                        "source_name": file_name,
                        "file_path": "",
                        "ingested_at": upload_time,
                        "status": "pending",
                        "version": 1.0,
                    })
                ))

            for idx, code in enumerate(mermaid_blocks, start=1):
                title = f"{file_name} Mermaid {idx}" if len(mermaid_blocks) > 1 else file_name
                diagram_docs.append(Document(
                    page_content=(
                        f"Diagram title: {title}\n"
                        f"Diagram type: Mermaid\n"
                        f"Source file: {file_name}\n"
                        f"{code}"
                    ),
                    metadata=self._sanitize_metadata({
                        "page": page,
                        "content_type": "mermaid",
                        "diagram_code": code,
                        "diagram_title": title,
                        "diagram_index": idx,
                        "source_name": file_name,
                        "file_path": "",
                        "ingested_at": upload_time,
                        "status": "pending",
                        "version": 1.0,
                    })
                ))

            cleaned_text = self._strip_diagram_blocks(raw_text)
            source_doc.page_content = cleaned_text or raw_text

        return diagram_docs
    
    def _extract_puml_title(self, code: str) -> str:
        match = re.search(r"title\s+(.+)", code)
        return match.group(1).strip() if match else "Untitled diagram"
            

    def ingestion_documents(self, filePath: str):
        ext = os.path.splitext(filePath)[1].lower()      
        file_name = os.path.basename(filePath)           

        upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        final_docs = []

        try:
            if ext in ['.jpg', '.jpeg', '.png']:
                img = Image.open(filePath)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                extracted_text = self.audit_image(self._convert_to_base64_(img))
                final_docs.append(Document(
                    page_content=f"Document OCR extraction from image file {file_name}:\n{extracted_text}",
                    metadata={"page": 1, "content_type": "image"}
                ))
                img.close()

            elif ext == '.pdf':   
                loader = PyPDFLoader(filePath)   
                raw_docs = loader.load()   
                total_text = "".join([doc.page_content for doc in raw_docs]).strip()
                
                if len(total_text) < 50:
                    print(f"⚠️ Scanned PDF detected. Processing pages sequentially to save RAM...")
                    
                    images = convert_from_path(filePath, dpi=150) 
                    
                    for i, image in enumerate(images):
                        print(f"🔍 Vision processing page {i+1}...")
                        data = self._convert_to_base64_(image)
                        descri = self.audit_image(data)
                        
                        final_docs.append(Document(
                            page_content=descri,
                            metadata={"page": i + 1}
                        ))
                        image.close() 
                else:
                    print(f"📄 Text-based PDF detected. Using fast extraction.")
                    final_docs = raw_docs
            elif ext in ['.txt', '.md', '.puml', '.mmd', '.mermaid']:
                try:
                    loader = TextLoader(filePath,encoding="utf-8")
                    final_docs = loader.load()
                    
                except UnicodeDecodeError:
                    loader = TextLoader(filePath, encoding="latin-1")
                    final_docs = loader.load()
                        
            else:
                raise ValueError(f"Unsupported file type: {ext}")

            # Clean extracted text before chunking to avoid garbage tokens
            for doc in final_docs:
                doc.page_content = self._clean_doc_text(doc.page_content)

            diagram_docs = self._build_diagram_docs(final_docs, file_name, ext, upload_time)
            chunks = self.spliters.split_documents(final_docs)

            for chunk in chunks:
                chunk.metadata["source_name"] = file_name
                chunk.metadata["file_path"] = filePath
                chunk.metadata["ingested_at"] = upload_time
                chunk.metadata["status"] = "pending"
                chunk.metadata["version"] = 1.0
                chunk.metadata = self._sanitize_metadata(chunk.metadata)

            for diagram_doc in diagram_docs:
                diagram_doc.metadata["file_path"] = filePath
                diagram_doc.metadata = self._sanitize_metadata(diagram_doc.metadata)

            return chunks + diagram_docs

        except Exception as e:
            print("Exception Occurs while ingestion documents:", e)
            return []
