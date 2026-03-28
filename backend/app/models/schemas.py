from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class IntentType(str, Enum):
    SEND_MESSAGE = "send_message"
    MAKE_CALL = "make_call"
    OPEN_APP = "open_app"
    SEARCH_WEB = "search_web"
    SET_REMINDER = "set_reminder"
    SET_ALARM = "set_alarm"
    SEND_EMAIL = "send_email"
    GENERAL_CHAT = "general_chat"


class EmotionType(str, Enum):
    HAPPY = "happy"
    SAD = "sad"
    STRESSED = "stressed"
    ANGRY = "angry"
    NEUTRAL = "neutral"


class LanguageType(str, Enum):
    ENGLISH = "english"
    URDU = "urdu"
    ROMAN_URDU = "roman_urdu"


class StatusType(str, Enum):
    OK = "ok"
    NEED_CLARIFICATION = "need_clarification"


class Entities(BaseModel):
    name: str = ""
    message: str = ""
    app: str = ""
    query: str = ""
    reminder_time: str = ""
    reminder_note: str = ""
    email: str = ""
    subject: str = ""
    body: str = ""
    time: str = ""
    note: str = ""


class Action(BaseModel):
    type: str = ""
    target: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    intent_data: Dict[str, Any] = Field(default_factory=dict)


class DeviceAction(BaseModel):
    action: str = ""
    type: str = ""
    target: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    message: str = ""
    success: bool = True
    requires_confirmation: bool = False
    confirmation_prompt: str = ""


class LLMOutput(BaseModel):
    intent: str = ""
    entities: Entities = Field(default_factory=Entities)
    emotion: str = ""
    language: str = ""
    confidence: float = 0.0
    reply: str = ""
    requires_tool: bool = False


class ProcessRequest(BaseModel):
    user_id: str
    text: str
    conversation_context: Optional[str] = ""
    last_intent: Optional[str] = ""
    last_target: Optional[str] = ""


class ProcessResponse(BaseModel):
    reply: str
    emotion: str
    intent: str
    action: Action
    status: str
    options: List[str] = Field(default_factory=list)
    requires_confirmation: bool = False
    device_action: Optional[Dict[str, Any]] = None
