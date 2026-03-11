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
from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredMarkdownLoader
from PIL import Image

class DataIngestor:
    def __init__(self):
        self.spliters = RecursiveCharacterTextSplitter(chunk_size=3000, chunk_overlap=250)
        self.llm =ChatGroq( 
            temperature=0,
            model_name="meta-llama/llama-4-scout-17b-16e-instruct"
        )
        
    def _convert_to_base64_(self,pil_image):
        buffered = BytesIO()
        
        pil_image.save(buffered,format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    def audit_image(self, base64img):
        # We define the content as a single list of dictionaries
        human_content = [
            {
                "type": "text",
                "text": "Please analyze this document image and extract all relevant text, tables, and signatures."
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64img}" 
                }
            }
        ]

        prompt = ChatPromptTemplate.from_messages([
            ("system", "Act as a corporate auditor. Read this image. Extract all text. If there are tables or charts, describe them exactly. If there are signatures, note them."),
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
                final_docs.append(Document(page_content=self.audit_image(self._convert_to_base64_(img)), metadata={"page": 1}))

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
            elif ext in ['.txt', '.md']:
                loader = TextLoader(filePath) if ext == '.txt' else UnstructuredMarkdownLoader(filePath)
                final_docs = loader.load()
            else:
                raise ValueError(f"Unsupported file type: {ext}")

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
