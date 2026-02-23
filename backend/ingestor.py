import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader,TextLoader,UnstructuredMarkdownLoader


class DataIngestor:
    def __init__(self):
        self.spliters = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        
    
    def ingestion_documents(self,filePath:str):
        
        fileName = os.path.splitext(filePath)[1].lower()
        
        try:
            if fileName == '.pdf':
                loader = PyPDFLoader(filePath)  
            elif fileName == '.txt':
                loader = TextLoader(filePath)
            elif fileName == '.md':
                loader = UnstructuredMarkdownLoader(filePath)
                
            raw_docs = loader.load()
            chunks = self.spliters.split_documents(raw_docs)
            
            for chunk in chunks:
                chunk.metadata["source_name"] = os.path.basename(filePath)
                chunk.metadata["file_path"] = filePath
                
            return chunks
                
        except Exception as e:
            print("Exception Occurs while ingestion documents: " , e)
            return []
        
    
        
            
        
        
        
        
        