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
    1. PARTICIPANTS: List every person mentioned by name and their role (e.g., Lisa - Design Lead).
    2. SUMMARY: Provide a 3-sentence summary of what was discussed.
    3. DECISIONS: List every final decision made. If none, state "No decisions reached".
    4. ACTION ITEMS: List tasks in format: @Person: Task (with deadline if mentioned).
    5. FATIGUE WARNING: Flag if the team discussed the same topic multiple times without a conclusion.

    FORMAT: Return as a clean Markdown report with clear section headers.
    IMPORTANT: Do NOT omit participants. Always list everyone present, even if they spoke briefly.
'''
        
        user_prompt = f"TRANSCRIPT:\n{transcript_text}"
        
        response = self.llm.invoke(
            [
                ("system",system_prompt),
                ("human",user_prompt)
            ]
        )
        
        return response.content
        
        
        