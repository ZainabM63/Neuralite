import chromadb
from chromadb.config import Settings
from app.core.config import settings
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

client = None
collection = None
structured_collection = None


def init_rag():
    global client, collection, structured_collection
    try:
        client = chromadb.PersistentClient(path=settings.RAG_PERSIST_DIR, settings=Settings(anonymized_telemetry=False))
        collection = client.get_or_create_collection("conversations")
        structured_collection = client.get_or_create_collection("structured_data")
    except Exception as e:
        print(f"RAG init error: {e}")
        pass


def add_conversation(user_id: str, user_text: str, assistant_reply: str, language: str = "english"):
    """Add conversation to RAG memory (legacy format)."""
    if collection is None:
        init_rag()
    try:
        import time
        doc_id = f"{user_id}_{int(time.time() * 1000)}"
        collection.add(
            documents=[f"User: {user_text}\nAssistant: {assistant_reply}"],
            ids=[doc_id],
            metadatas=[{"user_id": user_id, "language": language}]
        )
    except Exception as e:
        print(f"RAG add conversation error: {e}")
        pass


def add_structured_data(user_id: str, intent: str, entities: Dict[str, Any], emotion: str):
    """Add structured data to RAG memory for better context retrieval."""
    if structured_collection is None:
        init_rag()
    
    try:
        timestamp = datetime.now().isoformat()
        structured_doc = json.dumps({
            "user_id": user_id,
            "intent": intent,
            "entities": entities,
            "emotion": emotion,
            "timestamp": timestamp
        })
        
        doc_id = f"{user_id}_{timestamp}"
        structured_collection.add(
            documents=[structured_doc],
            ids=[doc_id],
            metadatas=[{
                "user_id": user_id,
                "intent": intent,
                "emotion": emotion,
                "timestamp": timestamp
            }]
        )
    except Exception:
        pass


def retrieve_context(user_id: str, query: str, limit: int = 5) -> str:
    """Retrieve conversational context (legacy format)."""
    if collection is None:
        init_rag()
    try:
        results = collection.query(
            query_texts=[query],
            n_results=limit,
            where={"user_id": user_id}
        )
        if results and results.get("documents") and results["documents"][0]:
            return "\n".join(results["documents"][0])
    except Exception as e:
        print(f"RAG retrieve context error: {e}")
        pass
    return ""


def retrieve_structured_context(user_id: str, query: str = "", limit: int = 5) -> Dict[str, Any]:
    """
    Retrieve structured context including:
    - Past conversations
    - User preferences
    - Emotional history
    """
    if structured_collection is None:
        init_rag()
    
    context = {
        "past_intents": [],
        "emotional_history": [],
        "preferences": {}
    }
    
    try:
        # Get recent structured data
        results = structured_collection.query(
            query_texts=[query] if query else ["conversation"],
            n_results=limit,
            where={"user_id": user_id}
        )
        
        if results and results.get("documents"):
            for doc in results["documents"][0]:
                try:
                    data = json.loads(doc)
                    if data.get("intent"):
                        context["past_intents"].append(data["intent"])
                    if data.get("emotion"):
                        context["emotional_history"].append(data["emotion"])
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    
    return context


def get_user_preferences(user_id: str) -> Dict[str, Any]:
    """Extract user preferences from past interactions."""
    context = retrieve_structured_context(user_id, limit=20)
    
    preferences = {
        "common_contacts": [],
        "common_apps": [],
        "emotional_trends": []
    }
    
    # Analyze past intents to find patterns
    intent_counts = {}
    for intent in context.get("past_intents", []):
        intent_counts[intent] = intent_counts.get(intent, 0) + 1
    
    # Most common intents suggest preferences
    if intent_counts:
        sorted_intents = sorted(intent_counts.items(), key=lambda x: x[1], reverse=True)
        preferences["top_intents"] = [i[0] for i in sorted_intents[:3]]
    
    # Emotional trends
    emotional_history = context.get("emotional_history", [])
    if emotional_history:
        # Count emotions
        emotion_counts = {}
        for emotion in emotional_history:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        # Most common recent emotion
        if emotion_counts:
            preferences["dominant_emotion"] = max(emotion_counts.items(), key=lambda x: x[1])[0]
    
    return preferences


def get_emotional_context(user_id: str) -> str:
    """Get a summary of user's recent emotional state for empathetic responses."""
    context = retrieve_structured_context(user_id, limit=10)
    
    emotional_history = context.get("emotional_history", [])
    if not emotional_history:
        return ""
    
    # Get the most recent emotion
    recent_emotion = emotional_history[-1] if emotional_history else "neutral"
    
    # Check for concerning patterns
    stress_count = emotional_history.count("stressed")
    sad_count = emotional_history.count("sad")
    
    if stress_count >= 3:
        return "user_seems_stressed_recently"
    elif sad_count >= 3:
        return "user_seems_sad_recently"
    
    return recent_emotion


def clear_history(user_id: str):
    """Clear conversation history for a user."""
    if collection is None:
        init_rag()
    try:
        collection.delete(where={"user_id": user_id})
    except Exception:
        pass
    
    # Also clear structured data
    if structured_collection is None:
        init_rag()
    try:
        structured_collection.delete(where={"user_id": user_id})
    except Exception:
        pass