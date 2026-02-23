

from backend import DataIngestor, rag_engine


class Run_Engine:
    engine = rag_engine
    ingestion_docs = DataIngestor
    data_folder = "./data"
    
    existing_docs = engine.vector_db
    
    
    
    