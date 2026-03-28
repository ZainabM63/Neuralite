from app.models.schemas import LLMOutput, Action, ProcessResponse
from typing import Optional


def route(parsed_output: dict) -> tuple[Optional[ProcessResponse], bool]:
    """
    Routes based on requires_tool flag.
    
    Returns:
        tuple: (ProcessResponse or None, needs_secondary_model: bool)
    """
    llm_output = LLMOutput(
        intent=parsed_output.get("intent", "general_chat"),
        emotion=parsed_output.get("emotion", "neutral"),
        language=parsed_output.get("language", "english"),
        confidence=parsed_output.get("confidence", 0.5),
        reply=parsed_output.get("reply", "Understood."),
        requires_tool=parsed_output.get("requires_tool", False)
    )
    
    entities = parsed_output.get("entities", {})
    if isinstance(entities, dict):
        llm_output.entities.name = entities.get("name", "")
        llm_output.entities.message = entities.get("message", "")
        llm_output.entities.app = entities.get("app", "")
        llm_output.entities.query = entities.get("query", "")
    
    if not llm_output.requires_tool:
        response = ProcessResponse(
            reply=llm_output.reply,
            emotion=llm_output.emotion,
            intent=llm_output.intent,
            action=Action(type="none", target="", data={}),
            status="ok",
            options=[]
        )
        return response, False
    
    return None, True
