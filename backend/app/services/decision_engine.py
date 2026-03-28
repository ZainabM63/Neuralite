from app.models.schemas import ProcessResponse, Action, LLMOutput, IntentType, EmotionType
from typing import Optional, Dict, Any, List
from datetime import datetime
import random


class DecisionType:
    EXECUTE = "execute"
    CLARIFY = "clarify"
    CONVERSE = "converse"
    CONFIRM = "confirm"


EMOTIONAL_RESPONSES = {
    EmotionType.STRESSED.value: [
        "I can sense you're feeling stressed. Take a deep breath - I'm here to help.",
        "Sounds like you're having a tough time. Let me help make things easier for you.",
        "I understand this is stressful. Let's tackle this together.",
        "Hey, it's okay to feel overwhelmed. I'm here to help you out.",
        "I notice you're stressed. Would you like me to help lighten your load?"
    ],
    EmotionType.SAD.value: [
        "I'm sorry you're feeling down. I'm here for you.",
        "I can tell something's bothering you. Would you like to talk about it?",
        "Things can be tough sometimes. I'm here to help in any way I can.",
        "I'm here with you. Whatever you're going through, we can get through it together.",
        "Take all the time you need. I'm just a message away."
    ],
    EmotionType.ANGRY.value: [
        "I can hear you're frustrated. Let's see if I can help calm things down.",
        "I understand this is frustrating. Let me help you work through this.",
        "I'm sorry you're upset. How can I make things better?",
        "I sense your frustration. Let me help resolve this.",
        "I understand you're angry. Let's work together to fix whatever's bothering you."
    ],
    EmotionType.HAPPY.value: [
        "That's wonderful to hear! Your positivity is contagious!",
        "I'm so glad you're feeling good! What's making you happy?",
        "Yay! I love seeing you happy! Keep that energy going!",
        "Your happiness makes me happy too! Anything else you'd like to share?",
        "That's awesome! Great vibes!"
    ],
    EmotionType.NEUTRAL.value: [
        "Got it! How else can I help you today?",
        "Understood. Let me know if there's anything else.",
        "I'm ready to assist. What would you like to do next?"
    ]
}

EMOTION_ICONS = {
    EmotionType.STRESSED.value: "💆",
    EmotionType.SAD.value: "😢",
    EmotionType.ANGRY.value: "😤",
    EmotionType.HAPPY.value: "😊",
    EmotionType.NEUTRAL.value: "🤖"
}

PROACTIVE_SUGGESTIONS = {
    EmotionType.STRESSED.value: [
        "Would you like me to set a reminder to take a break?",
        "Want me to play some calming music?",
        "Should I set an alarm for a short relaxation break?",
        "Would a funny joke help lighten the mood?"
    ],
    EmotionType.SAD.value: [
        "Would you like to listen to some uplifting music?",
        "Should I send a motivational quote to your chat?",
        "Want me to set a reminder to do something you enjoy?",
        "Would talking about something else help?"
    ],
    EmotionType.ANGRY.value: [
        "Would you like me to help you with whatever's frustrating you?",
        "Should I give you some space or distract you with something?",
        "Want me to help solve the problem step by step?"
    ],
    EmotionType.HAPPY.value: [
        "That's great! Want to share what's making you happy?",
        "Keep spreading those positive vibes!",
        "Celebrate the good moments!"
    ],
    EmotionType.NEUTRAL.value: []
}


def analyze(parsed_output: dict, context: str = "") -> tuple[str, Optional[ProcessResponse]]:
    """
    Analyzes parsed LLM output and decides the appropriate course of action.
    
    Returns:
        tuple: (decision_type, optional_response)
    """
    intent = parsed_output.get("intent", "general_chat")
    emotion = parsed_output.get("emotion", "neutral")
    entities = parsed_output.get("entities", {})
    requires_tool = parsed_output.get("requires_tool", False)
    confidence = parsed_output.get("confidence", 0.5)
    
    if emotion in [EmotionType.STRESSED.value, EmotionType.SAD.value, EmotionType.ANGRY.value]:
        response = _handle_emotional_state(emotion, intent, parsed_output.get("reply", ""))
        if not requires_tool or intent == IntentType.GENERAL_CHAT.value:
            return DecisionType.CONVERSE, response
    
    if confidence < 0.6 and requires_tool:
        response = _handle_low_confidence(intent, parsed_output.get("reply", ""))
        return DecisionType.CLARIFY, response
    
    if intent in [IntentType.SEND_MESSAGE.value, IntentType.MAKE_CALL.value]:
        if _needs_confirmation(entities):
            response = _build_confirmation_response(intent, entities, parsed_output.get("reply", ""))
            return DecisionType.CONFIRM, response
    
    if requires_tool:
        clarification = _check_missing_entities(intent, entities)
        if clarification:
            return DecisionType.CLARIFY, clarification
    
    if intent in [IntentType.SEND_MESSAGE.value, IntentType.MAKE_CALL.value]:
        ambiguity_response = _check_contact_ambiguity(entities)
        if ambiguity_response:
            return DecisionType.CLARIFY, ambiguity_response
    
    if not requires_tool or intent == IntentType.GENERAL_CHAT.value:
        response = _build_conversational_response(parsed_output)
        return DecisionType.CONVERSE, response
    
    return DecisionType.EXECUTE, None


def _handle_emotional_state(emotion: str, intent: str, base_reply: str) -> ProcessResponse:
    """Handle emotional states with empathetic responses."""
    
    if base_reply and any(word in base_reply.lower() for word in ["sorry", "understand", "help", "feel"]):
        reply = base_reply
    else:
        reply = random.choice(EMOTIONAL_RESPONSES.get(emotion, [base_reply]))
    
    suggestions = PROACTIVE_SUGGESTIONS.get(emotion, [])
    if suggestions and random.random() > 0.5:
        reply += " " + random.choice(suggestions)
    
    return ProcessResponse(
        reply=reply,
        emotion=emotion,
        intent=intent,
        action=Action(type="none", target="", data={}),
        status="ok",
        options=[],
        requires_confirmation=False
    )


def _handle_low_confidence(intent: str, base_reply: str) -> ProcessResponse:
    """Handle low confidence predictions."""
    clarification_options = _get_clarification_options(intent)
    
    return ProcessResponse(
        reply="I'm not entirely sure what you mean. Could you clarify?",
        emotion="neutral",
        intent=intent,
        action=Action(type="none", target="", data={}),
        status="need_clarification",
        options=clarification_options
    )


def _get_clarification_options(intent: str) -> List[str]:
    """Get contextual clarification options based on intent."""
    options_map = {
        IntentType.SEND_MESSAGE.value: [
            "Send a text message",
            "Send a WhatsApp message",
            "Cancel"
        ],
        IntentType.MAKE_CALL.value: [
            "Make a phone call",
            "Cancel"
        ],
        IntentType.OPEN_APP.value: [
            "Open an app",
            "Cancel"
        ],
        IntentType.SEARCH_WEB.value: [
            "Search the web",
            "Cancel"
        ],
        IntentType.SET_REMINDER.value: [
            "Set a reminder",
            "Set an alarm",
            "Cancel"
        ]
    }
    return options_map.get(intent, ["Please rephrase your request", "Cancel"])


def _needs_confirmation(entities: dict) -> bool:
    """Check if action requires user confirmation."""
    name = entities.get("name", "")
    return bool(name)


def _build_confirmation_response(intent: str, entities: dict, base_reply: str) -> ProcessResponse:
    """Build confirmation response for send_message and make_call."""
    
    name = entities.get("name", "")
    message = entities.get("message", "")
    app = entities.get("app", "sms")
    
    if intent == IntentType.SEND_MESSAGE.value:
        reply = f"I'll send a message to {name}"
        if message:
            reply += f' saying: "{message}"'
        reply += ". Is that correct?"
        action_type = "send_message"
        data = {"message": message, "app": app}
    else:
        reply = f"I'll call {name}. Is that correct?"
        action_type = "make_call"
        data = {}
    
    return ProcessResponse(
        reply=reply,
        emotion="neutral",
        intent=intent,
        action=Action(
            type=action_type,
            target=name,
            data=data
        ),
        status="need_clarification",
        options=[f"Yes, {action_type.replace('_', ' ')} {name}", "Cancel"],
        requires_confirmation=True
    )


def _check_missing_entities(intent: str, entities: dict) -> Optional[ProcessResponse]:
    """Check for missing required entities."""
    
    missing_entity_responses = {
        IntentType.SEND_MESSAGE.value: (
            "name",
            "Who would you like to send the message to?",
            "Please specify the recipient"
        ),
        IntentType.MAKE_CALL.value: (
            "name",
            "Who would you like to call?",
            "Please specify the contact"
        ),
        IntentType.OPEN_APP.value: (
            "app",
            "Which app would you like me to open?",
            "Please specify the app name"
        ),
        IntentType.SEARCH_WEB.value: (
            "query",
            "What would you like me to search for?",
            "Please specify your search query"
        ),
        IntentType.SET_REMINDER.value: (
            "reminder_time",
            "What time should I set the reminder for?",
            "Please specify the time"
        ),
        IntentType.SEND_EMAIL.value: (
            "email",
            "What email address should I send to?",
            "Please specify the email address"
        )
    }
    
    if intent in missing_entity_responses:
        entity_key, question, option = missing_entity_responses[intent]
        if not entities.get(entity_key):
            return ProcessResponse(
                reply=question,
                emotion="neutral",
                intent=intent,
                action=Action(type="none", target="", data={}),
                status="need_clarification",
                options=[option]
            )
        
        if intent == IntentType.SEND_MESSAGE.value and not entities.get("message"):
            return ProcessResponse(
                reply="What message would you like to send?",
                emotion="neutral",
                intent=intent,
                action=Action(type="send_message", target=entities.get("name", ""), data={}),
                status="need_clarification",
                options=["Please specify the message"]
            )
    
    return None


def _check_contact_ambiguity(entities: dict) -> Optional[ProcessResponse]:
    """Check for ambiguous contact names."""
    
    name = entities.get("name", "").lower()
    common_ambiguous = ["john", "ali", "ahmed", "mike", "saad", "david", "alex", "sam", "khan", "hassan"]
    
    if name in common_ambiguous:
        return ProcessResponse(
            reply=f"I found multiple contacts named {entities.get('name')}. Which one did you mean?",
            emotion="neutral",
            intent="make_call",
            action=Action(type="none", target="", data={}),
            status="need_clarification",
            options=[
                f"{entities.get('name')} (Home)",
                f"{entities.get('name')} (Work)",
                f"{entities.get('name')} (Mobile)"
            ]
        )
    
    return None


def _build_conversational_response(parsed_output: dict) -> ProcessResponse:
    """Build a conversational response with emotional awareness."""
    
    intent = parsed_output.get("intent", "general_chat")
    emotion = parsed_output.get("emotion", "neutral")
    base_reply = parsed_output.get("reply", "I'm here to help!")
    
    emotion_icon = EMOTION_ICONS.get(emotion, "")
    
    follow_ups = {
        EmotionType.HAPPY.value: " Anything else I can help with?",
        EmotionType.NEUTRAL.value: " How can I assist you further?",
        EmotionType.STRESSED.value: " Take your time - I'm here when you need me.",
        EmotionType.SAD.value: " Remember, I'm always here to listen.",
        EmotionType.ANGRY.value: " Let's work through this together."
    }
    
    reply = base_reply
    if emotion in follow_ups and not any(word in base_reply.lower() for word in ["?", "how", "what", "anything"]):
        reply += follow_ups[emotion]
    
    return ProcessResponse(
        reply=reply,
        emotion=emotion,
        intent=intent,
        action=Action(type="none", target="", data={}),
        status="ok",
        options=[],
        requires_confirmation=False
    )


def handle_confirmation_response(user_input: str, context: Dict[str, Any]) -> ProcessResponse:
    """
    Handle user's response to a confirmation prompt.
    """
    positive_keywords = ["yes", "yeah", "yep", "sure", "ok", "okay", "do it", "go ahead", "confirm", "send", "call", "please"]
    negative_keywords = ["no", "nope", "nah", "cancel", "stop", "don't", "never mind", "nevermind", "skip"]
    
    user_input_lower = user_input.lower().strip()
    
    is_positive = any(keyword in user_input_lower for keyword in positive_keywords)
    is_negative = any(keyword in user_input_lower for keyword in negative_keywords)
    
    negative_responses = [
        "No problem! I've cancelled that action. What else can I help you with?",
        "Sure thing! Cancelled. Is there anything else you'd like me to do?",
        "Got it! No worries. What else can I help you with?",
        "Alright, I've cancelled it. Let me know if you need anything else!",
        "Done! No action taken. What would you like to do next?"
    ]
    
    import random
    
    if is_negative:
        reply = random.choice(negative_responses)
        return ProcessResponse(
            reply=reply,
            emotion="neutral",
            intent="general_chat",
            action=Action(type="none", target="", data={}),
            status="ok",
            options=[],
            requires_confirmation=False
        )
    elif is_positive:
        original_intent = context.get("intent", "general_chat")
        target = context.get("target", "")
        data = context.get("data", {})
        
        positive_responses = [
            f"Great! Executing {original_intent} for {target}...",
            f"Perfect! I'll {original_intent.replace('_', ' ')} {target} now.",
            f"Awesome! Let me do that for you.",
            f"Done! Working on {original_intent.replace('_', ' ')} for {target}.",
            f"Great choice! I'll get that done for you."
        ]
        
        reply = random.choice(positive_responses)
        return ProcessResponse(
            reply=reply,
            emotion="happy",
            intent=original_intent,
            action=Action(type=original_intent, target=target, data=data),
            status="ok",
            options=[],
            requires_confirmation=False
        )
    else:
        clarification_responses = [
            "I'm not sure I understood. Did you want to proceed? (yes/no)",
            "Could you please confirm? Just say yes or no.",
            "I didn't catch that. Would you like me to go ahead?",
            "Sorry, I need a yes or no to proceed."
        ]
        reply = random.choice(clarification_responses)
        return ProcessResponse(
            reply=reply,
            emotion="neutral",
            intent="general_chat",
            action=Action(type="none", target="", data={}),
            status="need_clarification",
            options=["Yes, proceed", "No, cancel"]
        )


def handle_clarification_response(user_input: str, original_intent: str) -> ProcessResponse:
    """
    Handle user's clarification and re-route to appropriate action.
    """
    user_input_lower = user_input.lower().strip()
    
    clarification_responses = {
        "send_message": [
            "Got it! Let me send that message for you.",
            "Sure! Sending the message now.",
            "Alright, I'll send that message right away.",
            "Done! Your message has been sent."
        ],
        "make_call": [
            "Okay! I'll make that call for you.",
            "Sure thing! Calling now.",
            "Alright, dialing the number for you.",
            "Done! The call should be connecting."
        ],
        "open_app": [
            "Sure! Opening that app for you.",
            "Got it! Launching the app now.",
            "Alright, opening it up.",
            "Done! The app should be opening now."
        ],
        "set_reminder": [
            "Got it! Setting that reminder for you.",
            "Sure! Creating the reminder now.",
            "Alright, I'll set that reminder.",
            "Done! Your reminder has been set."
        ],
        "set_alarm": [
            "Got it! Setting that alarm for you.",
            "Sure! Creating the alarm now.",
            "Alright, I'll set that alarm.",
            "Done! Your alarm has been set."
        ],
        "general_chat": [
            "Got it! Let me help you with that.",
            "Sure thing! I'm on it.",
            "Alright, let me figure that out for you.",
            "Got it! Give me a moment."
        ]
    }
    
    responses = clarification_responses.get(original_intent, clarification_responses["general_chat"])
    import random
    reply = random.choice(responses)
    
    return ProcessResponse(
        reply=reply,
        emotion="neutral",
        intent=original_intent,
        action=Action(type="none", target="", data={}),
        status="ok",
        options=[],
        requires_confirmation=False
    )
