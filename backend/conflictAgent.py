from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import os


class ConflictAgent:
    def __init__(self):
        self.llm = ChatGroq(
            temperature=0,
            model_name="llama-3.3-70b-versatile"   # ← upgraded from 8b
        )

    def check_conflict_agent(self, new_context_text: str, old_context_text: str):
        system_prompt = """
You are a precise Senior Corporate Auditor. Your ONLY job is to detect DIRECT, MUTUALLY EXCLUSIVE logical contradictions between Existing Knowledge and New Information.

━━━ STRICT DEFINITION OF A CONFLICT ━━━
A conflict exists ONLY when:
- BOTH texts describe the EXACT SAME process, system, or entity
- AND they state INCOMPATIBLE facts about it
- Example: Text A says "Switch processes cashback" and Text B says "Portal processes cashback" → CONFLICT

━━━ WHAT IS NOT A CONFLICT ━━━

1. DIFFERENT ROLE NAMES ARE NOT CONFLICTS
   - "Checker Reward" and "Checker Disbursement" are TWO DIFFERENT roles
   - Role names must match CHARACTER FOR CHARACTER to be considered the same role
   - "Maker Reward" ≠ "Manage Disbursement" even if both allow uploads
   - Roles controlling different features = standard business design, NOT a conflict

2. DIFFERENT FEATURES USING SIMILAR PATTERNS ARE NOT CONFLICTS
   - Feature A having a Maker/Checker flow AND Feature B having a Maker/Checker flow
     is NOT a conflict — it is normal design
   - Each feature having its own approval role is INTENTIONAL, NOT contradictory

3. OMISSIONS ARE NOT CONFLICTS
   - If new text simply does not mention something from old text → NOT a conflict

4. DIFFERENT TABLES/COLUMNS ARE NOT CONFLICTS
   - Features storing data in separate tables = normal, NOT a conflict

━━━ FEW-SHOT EXAMPLES ━━━

EXAMPLE 1 — REAL CONFLICT:
  Existing: "Cashback transactions are processed by the Switch service."
  New:      "Cashback transactions are processed directly by the Admin Portal."
  → Output: CONFLICT: Both describe cashback processing but disagree on who processes it — Switch vs Admin Portal.

EXAMPLE 2 — NOT A CONFLICT (different roles):
  Existing: "Cashback approval requires Checker Reward permission."
  New:      "Disbursement approval requires Checker Disbursement permission."
  → Output: NONE

EXAMPLE 3 — NOT A CONFLICT (similar pattern, different features):
  Existing: "Load for cashback creates a pending record approved by Checker Reward."
  New:      "Load for disbursement creates a pending record approved by Checker Disbursement."
  → Output: NONE

EXAMPLE 4 — REAL CONFLICT:
  Existing: "CASHBACK_STATUS = C means transaction success."
  New:      "CASHBACK_STATUS = C means transaction failure."
  → Output: CONFLICT: Both texts define CASHBACK_STATUS = C but with opposite meanings — success vs failure.

EXAMPLE 5 — NOT A CONFLICT (omission):
  Existing: "Bulk upload supports CSV and Excel formats."
  New:      "Bulk upload supports CSV format."
  → Output: NONE

━━━ OUTPUT FORMAT ━━━
- If real contradiction: "CONFLICT: [one sentence explaining the exact contradiction]"
- If no contradiction:   "NONE"
- NO other output. NO explanations. NO bullet points.
"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Existing Knowledge:\n{existing}\n\nNew Information:\n{new_info}")
        ])

        chain  = prompt | self.llm
        result = chain.invoke({
            "existing": old_context_text,
            "new_info":  new_context_text
        })

        return result.content.strip()