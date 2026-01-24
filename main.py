"""Gradio fitness coach chatbot with SQLite-backed memory and profile.

Single-user demo: uses a fixed session_id so chat + profile persist in ./coach.db.
The bot streams responses, asks for missing profile fields once, and then serves
daily workouts with a fuller rationale paragraph referencing stored profile data.
"""

from __future__ import annotations

import os
import re
import sqlite3
from typing import Dict, Iterable, Optional

import gradio as gr
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_ollama import ChatOllama

# Single-user session id to keep the demo simple.
SESSION_ID = "demo_user"
DB_FOLDER = "data"
DB_NAME = "coach.db"
DB_PATH = os.path.join(DB_FOLDER, DB_NAME)

def init_db(path: str = DB_PATH) -> sqlite3.Connection:
    """Create the profiles table if missing and return a shared connection."""
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            session_id TEXT PRIMARY KEY,
            gender TEXT,
            age INTEGER,
            fitness_level TEXT,
            goals TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    return conn


DB_CONN = init_db()


def get_profile(session_id: str) -> Dict[str, Optional[str]]:
    cur = DB_CONN.execute(
        "SELECT gender, age, fitness_level, goals FROM profiles WHERE session_id = ?",
        (session_id,),
    )
    row = cur.fetchone()
    if not row:
        return {"gender": None, "age": None, "fitness_level": None, "goals": None}
    gender, age, fitness_level, goals = row
    age_str = str(age) if age is not None else None
    return {
        "gender": gender,
        "age": age_str,
        "fitness_level": fitness_level,
        "goals": goals,
    }


def save_profile(session_id: str, updates: Dict[str, str]) -> None:
    if not updates:
        return
    profile = get_profile(session_id)
    profile.update({k: v for k, v in updates.items() if v})
    DB_CONN.execute(
        """
        INSERT INTO profiles (session_id, gender, age, fitness_level, goals)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            gender=excluded.gender,
            age=excluded.age,
            fitness_level=excluded.fitness_level,
            goals=excluded.goals,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            session_id,
            profile.get("gender"),
            int(profile["age"]) if profile.get("age") and profile["age"].isdigit() else None,
            profile.get("fitness_level"),
            profile.get("goals"),
        ),
    )
    DB_CONN.commit()


def extract_profile_updates(text: str) -> Dict[str, str]:
    """Lightweight regex-based extraction for profile fields from user replies."""
    lowered = text.lower()
    updates: Dict[str, str] = {}

    gender_match = re.search(r"\b(male|female|man|woman|non[-\s]?binary|nb)\b", lowered)
    if gender_match:
        gender = gender_match.group(1)
        updates["gender"] = {
            "man": "male",
            "male": "male",
            "woman": "female",
            "female": "female",
            "non-binary": "non-binary",
            "non binary": "non-binary",
            "nonbinary": "non-binary",
            "nb": "non-binary",
        }.get(gender, gender)

    age_match = re.search(r"(\d{2})\s*(?:years?|yo|yrs?)?\b", lowered)
    if age_match:
        age_val = age_match.group(1)
        if 10 <= int(age_val) <= 100:
            updates["age"] = age_val

    fitness_match = re.search(r"\b(beginner|intermediate|advanced)\b", lowered)
    if fitness_match:
        updates["fitness_level"] = fitness_match.group(1)

    goal_match = re.search(r"goal(?:s)?(?:\s*:?\s*)(.+)", lowered)
    if goal_match:
        updates["goals"] = goal_match.group(1).strip()
    elif "lose" in lowered or "gain" in lowered or "endurance" in lowered:
        updates.setdefault("goals", text.strip())

    return updates


def build_prompt() -> ChatPromptTemplate:
    system = """
You are a friendly fitness coach that produces daily workouts tailored to the user's profile.
Known profile:
- gender: {gender}
- age: {age}
- fitness level: {fitness_level}
- goals: {goals}
Missing fields: {missing_fields}

Rules:
- If any fields are missing, ask ONE concise question for all missing fields and wait for the reply.
- Once all fields are known, provide today's workout: a short title, bullet list with sets/reps/time, 
then a fuller rationale paragraph that explicitly references the profile details and prior chat context. 
Keep it concise and encouraging.
"""
    return ChatPromptTemplate.from_messages([
        ("system", system.strip()),
        MessagesPlaceholder("history"),
        ("human", "{input}"),
    ])


def get_message_history(session_id: str) -> SQLChatMessageHistory:
    return SQLChatMessageHistory(
        session_id=session_id,
        connection_string=f"sqlite:///{DB_PATH}",
    )


prompt = build_prompt()
model = ChatOllama(
    model="llama3.2",
    temperature=0.6,
    base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434")
)
chain = prompt | model | StrOutputParser()
chain_with_history = RunnableWithMessageHistory(
    chain,
    get_message_history,
    input_messages_key="input",
    history_messages_key="history",
)


def run_chain(user_message: str, session_id: str) -> Iterable[str]:
    updates = extract_profile_updates(user_message)
    if updates:
        save_profile(session_id, updates)

    profile = get_profile(session_id)
    missing = [key for key, val in profile.items() if not val]
    missing_fields = ", ".join(missing) if missing else "none"

    inputs = {
        "input": user_message,
        "gender": profile.get("gender") or "unknown",
        "age": profile.get("age") or "unknown",
        "fitness_level": profile.get("fitness_level") or "unknown",
        "goals": profile.get("goals") or "unknown",
        "missing_fields": missing_fields,
    }

    config = {"configurable": {"session_id": session_id}}
    partial: list[str] = []
    for chunk in chain_with_history.stream(inputs, config=config):
        partial.append(chunk)
        yield "".join(partial)


def chat_handler(message: str, history: Optional[list] = None):
    for partial in run_chain(message, SESSION_ID):
        yield partial


def build_interface() -> gr.Blocks:
    with gr.Blocks(title="Fitness Coach") as demo:
        gr.Markdown("""### Fitness Coach\nStreaming daily workouts with memory (single-user demo).""")
        gr.ChatInterface(
            fn=chat_handler,
            title="Fitness Coach",
            textbox=gr.Textbox(placeholder="Ask for today's workout or answer profile questions..."),
        )
    return demo


if __name__ == "__main__":
    app = build_interface()
    app.launch()
