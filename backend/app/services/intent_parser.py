from app.models.schemas import ProcessResponse, Action, IntentType, StatusType
from typing import Optional, Dict, Any


INTENT_TO_ACTION = {
    IntentType.SEND_MESSAGE.value: "send_message",
    IntentType.MAKE_CALL.value: "make_call",
    IntentType.OPEN_APP.value: "open_app",
    IntentType.SEARCH_WEB.value: "search_web",
    IntentType.SET_REMINDER.value: "set_reminder",
    IntentType.SET_ALARM.value: "set_alarm",
    IntentType.SEND_EMAIL.value: "send_email",
    IntentType.GENERAL_CHAT.value: "no_action"
}

TOOLS_REQUIRING_CONFIRMATION = ["send_message", "make_call", "send_email"]


def build_action_response(llm_output: dict, secondary_result: Optional[Dict[str, Any]] = None) -> ProcessResponse:
    """
    Builds the final ProcessResponse from LLM output.
    """
    if secondary_result is not None:
        action_type = secondary_result.get("action_type", llm_output.get("intent", ""))
        target = secondary_result.get("target", "")
        data = secondary_result.get("data") or {}
        reply = secondary_result.get("refined_reply", llm_output.get("reply", ""))
    else:
        intent = llm_output.get("intent", "general_chat")
        entities = llm_output.get("entities", {})
        
        if intent == IntentType.SEND_MESSAGE.value:
            action_type = "send_message"
            target = entities.get("name", "")
            data = {"message": entities.get("message", "")}
        elif intent == IntentType.MAKE_CALL.value:
            action_type = "make_call"
            target = entities.get("name", "")
            data = {}
        elif intent == IntentType.OPEN_APP.value:
            action_type = "open_app"
            target = entities.get("app", "")
            data = {}
        elif intent == IntentType.SEARCH_WEB.value:
            action_type = "search_web"
            target = entities.get("query", "")
            data = {}
        elif intent == IntentType.SET_REMINDER.value:
            action_type = "set_reminder"
            target = entities.get("reminder_time", "")
            data = {"note": entities.get("reminder_note", "")}
        else:
            action_type = "no_action"
            target = ""
            data = {}
        
        reply = llm_output.get("reply", "Understood.")
    
    # Check if confirmation is required
    requires_confirmation = action_type in TOOLS_REQUIRING_CONFIRMATION
    
    return ProcessResponse(
        reply=reply,
        emotion=llm_output.get("emotion", "neutral"),
        intent=llm_output.get("intent", "general_chat"),
        action=Action(
            type=action_type,
            target=target,
            data=data
        ),
        status=StatusType.OK.value,
        options=[],
        requires_confirmation=requires_confirmation
    )