from app.models.schemas import ProcessResponse, Action, LLMOutput, IntentType
from typing import Optional


def check_ambiguity(llm_output: LLMOutput) -> tuple[bool, Optional[ProcessResponse]]:
    """
    Checks if the output has ambiguous elements requiring clarification.
    
    Returns:
        tuple: (is_ambiguous: bool, response: ProcessResponse or None)
    """
    intent = llm_output.intent
    entities = llm_output.entities
    
    if intent == IntentType.SEND_MESSAGE.value or intent == IntentType.MAKE_CALL.value:
        if not entities.name:
            response = ProcessResponse(
                reply="I couldn't find who you want to contact. Could you please specify the name?",
                emotion="neutral",
                intent=intent,
                action=Action(type="none", target="", data={}),
                status="need_clarification",
                options=["Please tell me who you want to message/call"]
            )
            return True, response
        
        if _has_multiple_meanings(entities.name):
            response = ProcessResponse(
                reply=f"I found multiple contacts named {entities.name}. Which one did you mean?",
                emotion="neutral",
                intent=intent,
                action=Action(type="none", target="", data={}),
                status="need_clarification",
                options=[f"{entities.name} (Home)", f"{entities.name} (Work)", f"{entities.name} (Mobile)"]
            )
            return True, response
    
    if intent == IntentType.OPEN_APP.value:
        if not entities.app:
            response = ProcessResponse(
                reply="Which app would you like me to open?",
                emotion="neutral",
                intent=intent,
                action=Action(type="none", target="", data={}),
                status="need_clarification",
                options=[]
            )
            return True, response
    
    return False, None


def _has_multiple_meanings(name: str) -> bool:
    common_ambiguous = ["john", "ali", "ahmed", "mike", "saad"]
    return name.lower() in common_ambiguous


def resolve_clarification(user_response: str, context: dict) -> ProcessResponse:
    """
    Handles user's clarification response.
    """
    return ProcessResponse(
        reply="Got it! Let me do that now.",
        emotion="neutral",
        intent=context.get("intent", "general_chat"),
        action=Action(type="none", target="", data={}),
        status="ok",
        options=[]
    )
