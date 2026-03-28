from app.services.llm_service import call_secondary_llm
from app.models.schemas import ProcessResponse, Action, IntentType
from typing import Optional, Dict, Any
import urllib.parse


TOOLS_REQUIRING_CONFIRMATION = ["send_message", "make_call", "make_whatsapp_call", "send_whatsapp_message", "send_email"]

APP_PACKAGE_MAPPING = {
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
    "amazon": "com.amazon.mShop.android.shopping",
    "ebay": "com.ebay.mobile",
    "paypal": "com.paypal.android.p2pmobile",
    "phonepe": "com.phonepe.app",
    "jazzcash": "com.jazzcash.psp",
    "whatsapp business": "com.whatsapp.w4b",
}


def _normalize_contact(contact: str) -> str:
    """Normalize contact name to phone number format if needed."""
    if not contact:
        return ""
    contact = contact.strip()
    if contact.replace(" ", "").isdigit():
        digits = contact.replace(" ", "")
        if len(digits) >= 10:
            if not digits.startswith("+"):
                if len(digits) == 10:
                    return f"+92{digits[1:]}"
                elif len(digits) == 11 and digits.startswith("0"):
                    return f"+92{digits[1:]}"
        return digits
    return contact


def _url_encode(text: str) -> str:
    """URL encode a string."""
    return urllib.parse.quote_plus(text)


def _parse_hour(time_str: str) -> int:
    """Parse hour from time string like '7 am' or '19:30'."""
    if not time_str:
        return 7
    time_str = time_str.lower().strip()
    if "am" in time_str or "pm" in time_str:
        parts = time_str.replace("am", "").replace("pm", "").strip().split()
        if parts:
            hour = int(parts[0])
            if "pm" in time_str and hour < 12:
                hour += 12
            return hour
    else:
        parts = time_str.split(":")
        if parts:
            return int(parts[0])
    return 7


def _parse_minutes(time_str: str) -> int:
    """Parse minutes from time string like '7:30 am' or '19:30'."""
    if not time_str:
        return 0
    time_str = time_str.lower().strip()
    if ":" in time_str:
        parts = time_str.replace("am", "").replace("pm", "").strip().split(":")
        if len(parts) > 1:
            return int(parts[1].split()[0])
    return 0


def _execute_send_message(target: str, data: dict) -> dict:
    """Generate SMS or WhatsApp message action."""
    message = data.get("message", "")
    app = data.get("app", "sms").lower()
    
    return {
        "success": True,
        "action": "send_message",
        "type": "send_message",
        "target": target,
        "data": {
            "message": message,
            "recipient": target,
            "app": app,
            "sms_uri": f"smsto:{_normalize_contact(target)}",
            "whatsapp_uri": f"whatsapp://send?phone={_normalize_contact(target)}"
        },
        "message": f"Opening {app} to message {target}",
        "requires_confirmation": True,
        "confirmation_prompt": f"Send '{message}' to {target}?"
    }


def _execute_make_call(target: str, data: dict) -> dict:
    """Generate phone call action."""
    return {
        "success": True,
        "action": "make_call",
        "type": "make_call",
        "target": target,
        "data": {
            "phone_number": _normalize_contact(target),
            "tel_uri": f"tel:{_normalize_contact(target)}"
        },
        "message": f"Opening dialer to call {target}",
        "requires_confirmation": True,
        "confirmation_prompt": f"Call {target}?"
    }


def _execute_make_whatsapp_call(target: str, data: dict) -> dict:
    """Generate WhatsApp call action."""
    return {
        "success": True,
        "action": "make_whatsapp_call",
        "type": "make_whatsapp_call",
        "target": target,
        "data": {
            "phone_number": _normalize_contact(target),
            "whatsapp_uri": f"whatsapp://send?phone={_normalize_contact(target)}"
        },
        "message": f"Opening WhatsApp to call {target}",
        "requires_confirmation": True,
        "confirmation_prompt": f"WhatsApp call to {target}?"
    }


def _execute_send_whatsapp_message(target: str, data: dict) -> dict:
    """Generate WhatsApp message action."""
    message = data.get("message", "")
    return {
        "success": True,
        "action": "send_whatsapp_message",
        "type": "send_whatsapp_message",
        "target": target,
        "data": {
            "phone_number": _normalize_contact(target),
            "message": message,
            "whatsapp_uri": f"https://wa.me/{_normalize_contact(target)}?text={_url_encode(message)}"
        },
        "message": f"Opening WhatsApp to message {target}",
        "requires_confirmation": True,
        "confirmation_prompt": f"Send WhatsApp message to {target}?"
    }


def _execute_open_app(target: str, data: dict) -> dict:
    """Generate app launch action."""
    app_name = target.lower()
    package = APP_PACKAGE_MAPPING.get(app_name, data.get("package", f"com.{app_name}"))
    
    return {
        "success": True,
        "action": "open_app",
        "type": "open_app",
        "target": target,
        "data": {
            "app_name": target,
            "package": package
        },
        "message": f"Opening {target}",
        "requires_confirmation": False
    }


def _execute_search_web(target: str, data: dict) -> dict:
    """Generate web search action."""
    query = target or data.get("query", "")
    encoded_query = query.replace(" ", "+")
    
    return {
        "success": True,
        "action": "search_web",
        "type": "search_web",
        "target": target,
        "data": {
            "query": query,
            "search_url": f"https://www.google.com/search?q={encoded_query}"
        },
        "message": f"Searching for: {query}",
        "requires_confirmation": False
    }


def _execute_set_reminder(target: str, data: dict) -> dict:
    """Generate reminder/alarm action."""
    time = target or data.get("time", "")
    note = data.get("note", data.get("reminder_note", ""))
    
    return {
        "success": True,
        "action": "set_reminder",
        "type": "set_reminder",
        "target": time,
        "data": {
            "time": time,
            "note": note
        },
        "message": f"Reminder set for {time}: {note}" if note else f"Alarm set for {time}",
        "requires_confirmation": True,
        "confirmation_prompt": f"Set reminder for {time} - '{note}'?"
    }


def _execute_send_email(target: str, data: dict) -> dict:
    """Generate email action."""
    to = target or data.get("to", "")
    subject = data.get("subject", "")
    body = data.get("body", "")
    
    return {
        "success": True,
        "action": "send_email",
        "type": "send_email",
        "target": to,
        "data": {
            "to": to,
            "subject": subject,
            "body": body,
            "mailto_uri": f"mailto:{to}?subject={_url_encode(subject)}&body={_url_encode(body)}"
        },
        "message": f"Opening email to compose to {to}",
        "requires_confirmation": True,
        "confirmation_prompt": f"Send email to {to} about '{subject}'?"
    }


def _execute_set_alarm(target: str, data: dict) -> dict:
    """Generate alarm action."""
    time = target or data.get("time", "")
    label = data.get("label", "Neura Reminder")
    
    return {
        "success": True,
        "action": "set_alarm",
        "type": "set_alarm",
        "target": time,
        "data": {
            "time": time,
            "label": label
        },
        "message": f"Alarm set for {time}: {label}",
        "requires_confirmation": True,
        "confirmation_prompt": f"Set alarm for {time} - '{label}'?"
    }


def _execute_general_chat(target: str, data: dict) -> dict:
    """Handle general chat (no action)."""
    return {
        "success": True,
        "action": "general_chat",
        "type": "general_chat",
        "target": "",
        "data": {},
        "message": "Conversation response",
        "requires_confirmation": False
    }


def execute_tool(action_type: str, target: str, data: dict) -> dict:
    """
    Generates device action commands for frontend execution.
    Returns structured response with action details for Flutter to handle.
    """
    if action_type == "send_message":
        return _execute_send_message(target, data)
    elif action_type == "make_call":
        return _execute_make_call(target, data)
    elif action_type == "make_whatsapp_call":
        return _execute_make_whatsapp_call(target, data)
    elif action_type == "send_whatsapp_message":
        return _execute_send_whatsapp_message(target, data)
    elif action_type == "open_app":
        return _execute_open_app(target, data)
    elif action_type == "search_web":
        return _execute_search_web(target, data)
    elif action_type == "set_reminder":
        return _execute_set_reminder(target, data)
    elif action_type == "send_email":
        return _execute_send_email(target, data)
    elif action_type == "set_alarm":
        return _execute_set_alarm(target, data)
    elif action_type == "general_chat":
        return _execute_general_chat(target, data)
    else:
        return {
            "success": False,
            "message": f"Unknown action type: {action_type}",
            "action": "none"
        }


def get_device_action(response: ProcessResponse) -> Dict[str, Any]:
    """
    Convert ProcessResponse to device action format for frontend.
    """
    action = response.action
    return execute_tool(action.type, action.target, action.data)
