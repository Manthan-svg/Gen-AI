import os
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate



class MeetingAgent:
    def __init__(self):
        self.llm = ChatGroq(
            temperature=0,
            model="llama-3.3-70b-versatile",
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        
    def analyze_transcript_text(self,transcript_text:str):
        system_prompt = '''
            You are a Senior Executive Assistant. Analyze this meeting transcript.
        
        TASKS:
        1. SUMMARY: Provide a 3-sentence summary.
        2. DECISIONS: List every final decision made. If no decision was made, state 'No decisions reached'.
        3. ACTION ITEMS: List tasks in format: @Person: Task.
        4. FATIGUE WARNING: Flag if the team discussed the same topic multiple times without a conclusion.
        
        FORMAT: Return as a clean Markdown report.
        '''
        
        user_prompt = f"TRANSCRIPT:\n{transcript_text}"
        
        response = self.llm.invoke(
            [
                ("system",system_prompt),
                ("human",user_prompt)
            ]
        )
        
        return response.content
        
        
        