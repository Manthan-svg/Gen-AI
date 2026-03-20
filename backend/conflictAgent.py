from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import os


class ConflictAgent:
    def __init__(self):
        self.llm = ChatGroq(
            temperature=0,
            model_name= "llama-3.1-8b-instant"
        )
    
    def check_conflict_agent(self,new_context_text:str,old_context_text:str):
        system_prompt = """
        You are a ruthless, highly precise Senior Corporate Auditor. Your ONLY job is to find direct, mutually exclusive logical contradictions between Existing Knowledge and New Information.
        
        CRITICAL RULES:
        1. MUTUALLY EXCLUSIVE ONLY: A conflict only exists if both texts describe the exact same process, metric, or system, but provide different, incompatible facts (e.g., "Processed by Switch" vs "Processed by Portal").
        2. PERMISSIONS ARE NOT CONFLICTS: Different roles having access to different features (e.g., Role A can view, but Role B can upload) is standard business logic. DO NOT flag this as a conflict.
        3. IGNORE OMISSIONS: If the new text simply leaves out a detail that was in the old text, it is NOT a conflict.
        4. IGNORE METADATA: Ignore file sizes, names, or formatting.
        
        ANALYSIS PROCESS (Internal):
        - Scan the texts for identical sections.
        - Look for state changes, architectural differences, or numerical mismatches for the same item.
        - Verify if the difference is a direct contradiction or just a business rule.
        
        OUTPUT FORMAT:
        - If a real contradiction exists, output EXACTLY: "CONFLICT: [Explain the exact contradiction briefly]"
        - If no real contradiction exists, output EXACTLY: "NONE"
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system",system_prompt),
            ("human","Existing Knowledge: {existing}\n\nNew Information: {new_info}")
            ])
        
        chain = prompt | self.llm
        response = chain.invoke({
            "new_info":new_context_text,
            "existing":old_context_text
        })
        
        return response.content
        
        