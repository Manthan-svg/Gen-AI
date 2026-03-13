import os
from datetime import datetime
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_neo4j import Neo4jGraph
from dotenv import load_dotenv

load_dotenv()

class ActionGraphBuilder:
    def __init__(self):
        self.llm = ChatGroq(
            temperature=0,
            model_name="llama-3.1-8b-instant",
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        
        # Neo4j connection (add these to your .env)
        self.graph = Neo4jGraph(
            url=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            username=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password"),
            database="neo4j"
        )
        
    def build_action_graph(self, summary_markdown: str, file_name: str, user_dept: str):
        """Extracts @Person: Task + deadlines and stores as graph"""
        
        extract_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Action Item Extractor.
            From the meeting summary, extract EVERY action item in clean JSON format.
            Format: 
            [
                {"person": "Sam", "task": "Finish schema mapping", "deadline": "2026-03-20", "status": "open"}
            ]
            If no deadline, use "TBD". Only return valid JSON, no extra text."""),
            ("human", "SUMMARY:\n{summary}")
        ])
        
        chain = extract_prompt | self.llm
        response = chain.invoke({"summary": summary_markdown})
        
        try:
            actions = eval(response.content.strip())  # Safe eval for JSON list
        except:
            actions = []
        
        # Add to Neo4j Graph
        for action in actions:
            cypher = """
            MERGE (p:Person {name: $person, department: $dept})
            MERGE (t:Task {description: $task, deadline: $deadline, status: $status})
            MERGE (m:Meeting {name: $file_name})
            MERGE (p)-[:ASSIGNED_TO]->(t)
            MERGE (t)-[:BELONGS_TO]->(m)
            MERGE (t)-[:HAS_DEADLINE]->(d:Deadline {date: $deadline})
            """
            self.graph.query(cypher, {
                "person": action.get("person"),
                "task": action.get("task"),
                "deadline": action.get("deadline", "TBD"),
                "status": action.get("status", "open"),
                "file_name": file_name,
                "dept": user_dept
            })
        
        print(f"✅ [GRAPH RAG] {len(actions)} action items added to Neo4j Graph")
        return actions