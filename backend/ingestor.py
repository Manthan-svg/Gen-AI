from datetime import datetime
from json import load
import os
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



    def ingestion_documents(self, filePath: str, user_dept: str = "general"):
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
                
                print(total_text)
                
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
                    print(final_docs)
            elif ext in ['.txt', '.md']:
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

            chunks = self.spliters.split_documents(final_docs)

            for chunk in chunks:
                chunk.metadata["source_name"] = file_name
                chunk.metadata["file_path"] = filePath
                chunk.metadata["ingested_at"] = upload_time
                chunk.metadata["status"] = "pending"
                chunk.metadata["department"] = user_dept
                chunk.metadata["version"] = 1.0
                

            return chunks   

        except Exception as e:
            print("Exception Occurs while ingestion documents:", e)
            return []
