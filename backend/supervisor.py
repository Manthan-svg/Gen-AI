import os
import json
from datetime import datetime
from meeting_agent import MeetingAgent
from conflictAgent import ConflictAgent
from ingestor import DataIngestor
from rag_engine import DeepContextEngine

class Supervisor:
    def __init__(self):
        self.engine = DeepContextEngine()
        self.ingest = DataIngestor()
        self.critic = ConflictAgent()
        self.meeting_ai = MeetingAgent() # Initialize once
        
    def supervisor(self, file_path: str, user_dept: str):
        file_name = os.path.basename(file_path).lower()
        vector_db = self.engine.get_vector_db(refresh=True)
        
        # --- BRANCH 1: MEETING FATIGUE LOGIC ---
        if "meeting" in file_name or "transcript" in file_name:
            print(f"🎙️ [MODE: MEETING] Analyzing transcript: {file_name}")
            
            # Use your ingestor to get the full text (not chunks)
            # Assuming ingestion_documents returns a list of LangChain Documents
            docs = self.ingest.ingestion_documents(file_path, user_dept)
            if not docs:
                raise RuntimeError(f"No content extracted from meeting file: {file_name}")
            full_text = " ".join([d.page_content for d in docs])
            
            # Generate the Golden Summary (JSON format is best)
            summary_report = self.meeting_ai.analyze_transcript_text(full_text)
            
            # Store the SUMMARY as a single high-value record
            vector_db.add_texts(
                texts=[summary_report],
                metadatas=[{
                    "department": user_dept, 
                    "type": "meeting_summary", 
                    "source_name": file_name,
                    "ingested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "verified",          # ✅ Add this
                    "conflict_reason": "N/A"       
                }]
            )
            
            self.engine._try_persist()
            print(f"✅ [SUCCESS] Meeting summary saved to ChromaDB.")
            return "Meeting Processed"

        # --- BRANCH 2: STANDARD AUDIT LOGIC (Your existing code) ---
        else:
            print(f"🚀 [MODE: AUDIT] Starting High-Speed Audit: {file_name}")
            new_chunks = self.ingest.ingestion_documents(file_path, user_dept)
            if not new_chunks:
                raise RuntimeError(f"No content extracted from file: {file_name}")

            batch_size = 20  
            processed_chunks = []
            
            for i in range(0, len(new_chunks), batch_size):
                current_batch = new_chunks[i : i + batch_size]
                batch_text = " ".join([c.page_content for c in current_batch])

                # Use similarity search with score to ensure we only check relevant docs
                docs_with_scores = vector_db.similarity_search_with_score(
                    batch_text, k=1, filter={"department": user_dept}
                )
                
                existing_knowledge = ""
                if docs_with_scores and docs_with_scores[0][1] < 0.6:
                    existing_knowledge = docs_with_scores[0][0].page_content

                conflict_status = "verified"
                reason = "Verified against dept knowledge"
                
                if existing_knowledge.strip():
                    assertions = self.critic.check_conflict_agent(batch_text, existing_knowledge)
                    if "CONFLICT" in assertions.upper():
                        conflict_status = "conflict"
                        reason = assertions.strip() 

                for chunk in current_batch:
                    chunk.metadata.update({
                        "department": user_dept,
                        "source_name": file_name,
                        "ingested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "status": conflict_status,
                        "conflict_reason": reason
                    })
                    processed_chunks.append(chunk)

            vector_db.add_documents(processed_chunks)
            self.engine._try_persist()
            return processed_chunks
