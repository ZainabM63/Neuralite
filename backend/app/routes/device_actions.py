from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum


router = APIRouter()


class ActionType(str, Enum):
    SEND_MESSAGE = "send_message"
    MAKE_CALL = "make_call"
    OPEN_APP = "open_app"
    SEARCH_WEB = "search_web"
    SET_REMINDER = "set_reminder"
    SET_ALARM = "set_alarm"
    SEND_EMAIL = "send_email"


class DeviceActionRequest(BaseModel):
    action_type: str
    target: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    confirmed: bool = False


class DeviceActionResponse(BaseModel):
    success: bool
    action_type: str
    message: str
    requires_confirmation: bool = False
    confirmation_prompt: str = ""
    deep_link: Optional[str] = None
    package_name: Optional[str] = None


APP_PACKAGES = {
    "chrome": "com.android.chrome",
    "whatsapp": "com.whatsapp",
    "settings": "com.android.settings",
    "phone": "com.android.dialer",
    "messages": "com.google.android.apps.messaging",
    "gmail": "com.google.android.gm",
    "instagram": "com.instagram.android",
    "facebook": "com.facebook.katana",
    "twitter": "com.twitter.android",
    "youtube": "com.google.android.youtube",
    "spotify": "com.spotify.music",
    "camera": "com.android.camera2",
    "maps": "com.google.android.apps.maps",
    "calendar": "com.android.calendar",
    "clock": "com.google.android.deskclock",
    "calculator": "com.android.calculator2",
    "gallery": "com.google.android.apps.photos",
    "drive": "com.google.android.apps.docs",
    "notes": "com.google.android.keep",
    "telegram": "org.telegram.messenger",
    "snapchat": "com.snapchat.android",
    "tiktok": "com.zhiliaoapp.musically",
    "linkedin": "com.linkedin.android",
    "zoom": "us.zoom.videomeetings",
    "teams": "com.microsoft.teams",
    "slack": "com.Slack",
    "discord": "com.discord",
    "reddit": "com.reddit.frontpage",
    "netflix": "com.netflix.mediaclient",
    "paypal": "com.paypal.android.p2pmobile",
    "phonepe": "com.phonepe.app",
}


def normalize_phone(phone: str) -> str:
    """Normalize phone number format."""
    if not phone:
        return ""
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.isdigit():
        if len(phone) == 10:
            return f"+92{phone[1:]}"
        elif len(phone) == 11 and phone.startswith("0"):
            return f"+92{phone[1:]}"
        elif len(phone) == 12 and phone.startswith("92"):
            return f"+{phone}"
    return phone


@router.post("/device_action", response_model=DeviceActionResponse)
async def execute_device_action(request: DeviceActionRequest):
    """
    Execute a device action and return the necessary information for Flutter to perform it.
    """
    action_type = request.action_type
    target = request.target
    data = request.data
    confirmed = request.confirmed
    
    if not confirmed:
        confirmation_prompt = _get_confirmation_prompt(action_type, target, data)
        return DeviceActionResponse(
            success=True,
            action_type=action_type,
            message="Confirmation required",
            requires_confirmation=True,
            confirmation_prompt=confirmation_prompt
        )
    
    if action_type == ActionType.SEND_MESSAGE.value:
        return _handle_send_message(target, data)
    elif action_type == ActionType.MAKE_CALL.value:
        return _handle_make_call(target, data)
    elif action_type == ActionType.OPEN_APP.value:
        return _handle_open_app(target, data)
    elif action_type == ActionType.SEARCH_WEB.value:
        return _handle_search_web(target, data)
    elif action_type == ActionType.SET_REMINDER.value:
        return _handle_set_reminder(target, data)
    elif action_type == ActionType.SET_ALARM.value:
        return _handle_set_alarm(target, data)
    elif action_type == ActionType.SEND_EMAIL.value:
        return _handle_send_email(target, data)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action type: {action_type}")


def _get_confirmation_prompt(action_type: str, target: str, data: Dict[str, Any]) -> str:
    """Get confirmation prompt based on action type."""
    prompts = {
        "send_message": f"Send message to {target}: '{data.get('message', '')}'?",
        "make_call": f"Call {target}?",
        "open_app": f"Open {target}?",
        "search_web": f"Search for '{target}'?",
        "set_reminder": f"Set reminder for {target}: '{data.get('note', '')}'?",
        "set_alarm": f"Set alarm for {target}: '{data.get('label', '')}'?",
        "send_email": f"Send email to {target} about '{data.get('subject', '')}'?"
    }
    return prompts.get(action_type, f"Proceed with {action_type}?")


def _handle_send_message(target: str, data: Dict[str, Any]) -> DeviceActionResponse:
    """Handle send message action."""
    message = data.get("message", "")
    app = data.get("app", "sms").lower()
    
    if app == "whatsapp":
        phone = normalize_phone(target)
        deep_link = f"whatsapp://send?phone={phone}&text={message.replace(' ', '%20')}"
    else:
        phone = normalize_phone(target)
        deep_link = f"sms:{phone}?body={message.replace(' ', '%20')}"
    
    return DeviceActionResponse(
        success=True,
        action_type="send_message",
        message=f"Opening {app} to message {target}",
        requires_confirmation=False,
        deep_link=deep_link
    )


def _handle_make_call(target: str, data: Dict[str, Any]) -> DeviceActionResponse:
    """Handle make call action."""
    phone = normalize_phone(target)
    deep_link = f"tel:{phone}"
    
    return DeviceActionResponse(
        success=True,
        action_type="make_call",
        message=f"Opening dialer for {target}",
        requires_confirmation=False,
        deep_link=deep_link
    )


def _handle_open_app(target: str, data: Dict[str, Any]) -> DeviceActionResponse:
    """Handle open app action."""
    app_name = target.lower()
    package = APP_PACKAGES.get(app_name, data.get("package", f"com.{app_name}"))
    
    return DeviceActionResponse(
        success=True,
        action_type="open_app",
        message=f"Opening {target}",
        requires_confirmation=False,
        package_name=package
    )


def _handle_search_web(target: str, data: Dict[str, Any]) -> DeviceActionResponse:
    """Handle web search action."""
    query = target or data.get("query", "")
    encoded_query = query.replace(" ", "+")
    deep_link = f"https://www.google.com/search?q={encoded_query}"
    
    return DeviceActionResponse(
        success=True,
        action_type="search_web",
        message=f"Searching for: {query}",
        requires_confirmation=False,
        deep_link=deep_link
    )


def _handle_set_reminder(target: str, data: Dict[str, Any]) -> DeviceActionResponse:
    """Handle set reminder action."""
    time = target or data.get("time", "")
    note = data.get("note", "")
    
    deep_link = "clock://"
    
    return DeviceActionResponse(
        success=True,
        action_type="set_reminder",
        message=f"Reminder set for {time}: {note}" if note else f"Alarm set for {time}",
        requires_confirmation=False,
        deep_link=deep_link
    )


def _handle_set_alarm(target: str, data: Dict[str, Any]) -> DeviceActionResponse:
    """Handle set alarm action."""
    time = target or data.get("time", "")
    label = data.get("label", "Neura Reminder")
    
    deep_link = "clock://"
    
    return DeviceActionResponse(
        success=True,
        action_type="set_alarm",
        message=f"Alarm set for {time}: {label}",
        requires_confirmation=False,
        deep_link=deep_link
    )


def _handle_send_email(target: str, data: Dict[str, Any]) -> DeviceActionResponse:
    """Handle send email action."""
    subject = data.get("subject", "")
    body = data.get("body", "")
    encoded_subject = subject.replace(" ", "%20")
    encoded_body = body.replace(" ", "%20").replace("\n", "%0A")
    deep_link = f"mailto:{target}?subject={encoded_subject}&body={encoded_body}"
    
    return DeviceActionResponse(
        success=True,
        action_type="send_email",
        message=f"Opening email to compose to {target}",
        requires_confirmation=False,
        deep_link=deep_link
    )


@router.get("/installed_apps")
async def get_installed_apps():
    """Return list of known apps with their package names."""
    return {
        "apps": [
            {"name": name, "package": package}
            for name, package in APP_PACKAGES.items()
        ]
    }


@router.get("/health")
async def device_action_health():
    """Health check for device action service."""
    return {"status": "ok", "service": "device_actions"}
