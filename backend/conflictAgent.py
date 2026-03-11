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
        You are a Senior Corporate Auditor. Your ONLY job is to find logical contradictions in BUSINESS DATA.
        
        RULES:
        1. IGNORE file sizes, file names, or technical metadata (e.g., "5MB", "PDF", "Table 1").
        2. IGNORE "missing" information. If the new text doesn't mention something, it is NOT a conflict.
        3. ONLY flag a CONFLICT if two statements are mutually exclusive (e.g., "Budget is $50k" vs "Budget is $10k").
        4. If there are no REAL business conflicts, respond ONLY with the word: "NONE".
        
        FORMAT:
        If a conflict exists, start with 'CONFLICT:' followed by very small 2-3 lines of text.
        If no conflict exists, return 'NONE'.
        
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system",system_prompt),
            ("human","Existing Knowledge: {existing}\n\nNew Information: {new_info}")
            ])
        
        chain = prompt | self.llm
        response = chain.invoke({
            "existing":new_context_text,
            "new_info":old_context_text
        })
        
        return response.content
        
        