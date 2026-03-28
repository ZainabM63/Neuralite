from app.models.schemas import Action
from app.services.tool_executor import execute_tool, get_device_action
from fastapi import APIRouter, HTTPException, Request
from app.models.schemas import ProcessRequest, ProcessResponse
from app.services.llm_service import call_primary_llm
from app.services.model_router import route
from app.services.intent_parser import build_action_response as legacy_build_action_response
from app.services.rag_service import (
    add_conversation,
    retrieve_context,
    add_structured_data,
    get_emotional_context,
    get_user_preferences
)
from app.services.decision_engine import (
    analyze,
    DecisionType,
    handle_confirmation_response,
    handle_clarification_response
)
from app.models.schemas import LLMOutput

# Try to import translation service
try:
    from app.services.translation_service import translate_to_english, translate_from_english
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False
    def translate_to_english(text):
        return text, 'unknown'
    def translate_from_english(text, lang):
        return text

router = APIRouter()


@router.post("/debug", response_model=ProcessResponse)
async def debug_endpoint(request: Request):
    """Debug endpoint to see raw request data"""
    try:
        body = await request.json()
        print(f"Raw request body: {body}")
        return ProcessResponse(
            reply="Debug: Request received",
            emotion="neutral",
            intent="debug",
            action=Action(type="debug", target="", data={}),
            status="ok",
            options=[],
            requires_confirmation=False
        )
    except Exception as e:
        print(f"Debug error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/process", response_model=ProcessResponse)
async def process_input(request: ProcessRequest):
    """
    Main endpoint for processing user input.
    Handles intent detection, emotional analysis, decision making, and action execution.
    """
    try:
        print(f"Processing request from user: {request.user_id}")
        print(f"Text: {request.text}")
        print(f"Last intent: {request.last_intent}, Last target: {request.last_target}")
        
        text = request.text.lower().strip()
        original_text = request.text
        
        last_intent = request.last_intent or ""
        last_target = request.last_target or ""
        
        user_input_lower = text.strip()
        
        positive_keywords = ["yes", "yeah", "yep", "sure", "ok", "okay", "do it", "go ahead", "confirm", "send", "call", "please"]
        negative_keywords = ["no", "nope", "nah", "cancel", "stop", "don't", "never mind", "nevermind", "skip"]
        
        is_positive = any(keyword in user_input_lower for keyword in positive_keywords)
        is_negative = any(keyword in user_input_lower for keyword in negative_keywords)
        
        if last_intent and (is_positive or is_negative) and request.conversation_context:
            if is_positive and last_intent not in ["general_chat", "error"]:
                return ProcessResponse(
                    reply=f"Great! Executing {last_intent} for {last_target}...",
                    emotion="happy",
                    intent=last_intent,
                    action=Action(type=last_intent, target=last_target, data={}),
                    status="ok",
                    options=[],
                    requires_confirmation=False
                )
            elif is_negative:
                return ProcessResponse(
                    reply="No problem! I've cancelled that action. What else can I help you with?",
                    emotion="neutral",
                    intent="general_chat",
                    action=Action(type="none", target="", data={}),
                    status="ok",
                    options=[],
                    requires_confirmation=False
                )
        
        # Quick responses for greetings
        QUICK_RESPONSES = {
            "hi": ("Hey there! 👋 How can I help you today?", "happy"),
            "hello": ("Hi! 👋 How are you doing?", "happy"),
            "hey": ("Hey! What's up?", "happy"),
            "help": ("I can help you with:\n• Sending messages\n• Making calls\n• Opening apps\n• Searching the web\n• Setting reminders\n• And more! Just tell me what you need.", "neutral"),
            "who are you": ("I'm Neura, your AI assistant! I can help you with phone tasks, have conversations, and I'm here to help whenever you need me 😊", "happy"),
            "thanks": ("You're welcome! 😊 Is there anything else I can help with?", "happy"),
            "thank you": ("Happy to help! 😊 Anything else?", "happy"),
            "bye": ("Bye! Take care! 😊", "happy"),
            "goodbye": ("Goodbye! See you soon! 😊", "happy"),
        }
        
        # Emotional phrases that don't need LLM
        EMOTIONAL_RESPONSES = {
            "i don't feel good": ("I'm sorry you're not feeling well. 😔 Take care of yourself. Would you like me to set a reminder for you to rest?", "sad"),
            "i dont feel good": ("I'm sorry you're not feeling well. 😔 Take care of yourself. Would you like me to set a reminder for you to rest?", "sad"),
            "i feel sad": ("I'm here for you. 😢 It's okay to feel sad sometimes. Would you like to talk about it?", "sad"),
            "i'm sad": ("I'm sorry you're feeling down. 😢 I'm here if you want to talk.", "sad"),
            "i am sad": ("I'm here with you. 😢 Sometimes it helps to share what's on your mind.", "sad"),
            "i feel stressed": ("I understand you're stressed. 💆 Take a deep breath. Let me know if there's anything I can do to help.", "stressed"),
            "i'm stressed": ("I sense you're feeling overwhelmed. 💆 Remember to take breaks. I'm here to help.", "stressed"),
            "i am stressed": ("Take it easy! 💆 Would a short break reminder help?", "stressed"),
            "i feel angry": ("I can sense you're frustrated. 😤 Take a moment. How can I help?", "angry"),
            "i'm angry": ("I understand you're upset. 😤 Let's work through this together.", "angry"),
            "i am angry": ("Breathe. 😤 I'm here to help you.", "angry"),
            "i'm happy": ("That's wonderful! 😊 What made you happy?", "happy"),
            "i am happy": ("Yay! 😊 I love seeing you happy!", "happy"),
            "i feel happy": ("Great to hear! 😊 Keep spreading those positive vibes!", "happy"),
            "feeling tired": ("I understand. 😴 Make sure to get enough rest. Need me to set a reminder?", "neutral"),
            "i'm tired": ("Rest is important. 😴 Would you like me to set an alarm for a short nap?", "neutral"),
            "i am tired": ("Take care of yourself. 😴 Don't overdo it.", "neutral"),
            "i miss you": ("Aww that's sweet! 😊 I'm always here for you!", "happy"),
            "i love you": ("That's so kind! 😊 I love helping you too!", "happy"),
            "i'm bored": ("Let's do something fun! 😄 Want me to search for something interesting or tell you a joke?", "happy"),
            "i am bored": ("Boredom be gone! 😄 Tell me something you'd like to explore.", "happy"),
        }
        
        # Check exact match greetings first
        if text in QUICK_RESPONSES:
            reply, emotion = QUICK_RESPONSES[text]
            return ProcessResponse(
                reply=reply,
                emotion=emotion,
                intent="general_chat",
                action=Action(type="none", target="", data={}),
                status="ok",
                options=[],
                requires_confirmation=False
            )
        
        # Check emotional phrases (normalize apostrophes for matching)
        normalized_text = text.replace("'", "'").replace("'", "'")
        
        if normalized_text in EMOTIONAL_RESPONSES or text in EMOTIONAL_RESPONSES:
            key = normalized_text if normalized_text in EMOTIONAL_RESPONSES else text
            reply, emotion = EMOTIONAL_RESPONSES[key]
            return ProcessResponse(
                reply=reply,
                emotion=emotion,
                intent="general_chat",
                action=Action(type="none", target="", data={}),
                status="ok",
                options=[],
                requires_confirmation=False
            )
        
        # Normalize text for keyword matching
        normalized_for_match = text.replace("'", "").replace("'", "")
        
        # Check if text contains emotional keywords (check longer phrases first)
        emotional_patterns = [
            # Longest patterns first
            ("not feeling good", "I'm sorry you're not feeling well. 😔 Take care of yourself.", "sad"),
            ("not feeling well", "I hope you feel better soon. 😔 Take care of yourself.", "sad"),
            ("don't feel good", "I'm sorry you're not feeling well. 😔 Take care of yourself.", "sad"),
            ("dont feel good", "I'm sorry you're not feeling well. 😔 Take care of yourself.", "sad"),
            ("don't feel well", "I hope you feel better soon. 😔 Take care of yourself.", "sad"),
            ("feeling unwell", "Take it easy. 😔 I hope you feel better soon.", "sad"),
            ("feeling terrible", "Oh no! 😔 I hope you feel better soon.", "sad"),
            ("not feeling great", "I hope things get better. 😔 Take care of yourself.", "sad"),
            ("feeling horrible", "I'm sorry you're feeling awful. 😔 Take care of yourself.", "sad"),
            ("feel sick", "I hope you feel better soon. 😔 Take care!", "sad"),
            ("am sick", "I hope you feel better soon. 😔 Take care!", "sad"),
            ("feeling bad", "I'm here for you. 😔 Things will get better.", "sad"),
            ("i feel bad", "I'm here for you. 😔 Things will get better.", "sad"),
            ("not good", "I'm here for you. 😔 Tell me more if you'd like.", "sad"),
            ("don't feel", "I'm sorry you're not feeling well. 😔 Take care of yourself.", "sad"),
            ("dont feel", "I'm sorry you're not feeling well. 😔 Take care of yourself.", "sad"),
            ("feeling sad", "I'm here for you. 😢 It's okay to feel sad sometimes.", "sad"),
            ("feel sad", "I'm here for you. 😢 It's okay.", "sad"),
            ("feeling down", "I'm here for you. 😢 Things will get better.", "sad"),
            ("feeling upset", "I understand. 😢 I'm here to listen.", "sad"),
            ("not happy", "I'm here for you. 😔 What's bothering you?", "sad"),
            ("feeling stressed", "I understand you're stressed. 💆 Take a deep breath.", "stressed"),
            ("feel stressed", "I understand you're stressed. 💆 Take a deep breath.", "stressed"),
            ("stressed out", "I sense you're stressed. 💆 Remember to breathe.", "stressed"),
            ("under pressure", "I understand you're stressed. 💆 How can I help?", "stressed"),
            ("feeling angry", "I can sense you're frustrated. 😤 Take a moment.", "angry"),
            ("feel angry", "I understand you're angry. 😤 Let's work through this.", "angry"),
            ("feeling annoyed", "I sense you're frustrated. 😤 Let's take it slow.", "angry"),
            ("feeling frustrated", "I understand your frustration. 😤 How can I help?", "angry"),
            ("so angry", "I understand you're upset. 😤 Take a deep breath.", "angry"),
            ("really angry", "I hear you. 😤 Take your time.", "angry"),
        ]
        
        for pattern, reply, emotion in emotional_patterns:
            pattern_normalized = pattern.replace("'", "").replace("'", "")
            if pattern_normalized in normalized_for_match or pattern in text:
                return ProcessResponse(
                    reply=reply,
                    emotion=emotion,
                    intent="general_chat",
                    action=Action(type="none", target="", data={}),
                    status="ok",
                    options=[],
                    requires_confirmation=False
                )
        
        # Urdu/Roman Urdu emotional patterns
        URDU_PATTERNS = [
            ("achha nahi ho raha", "Mujhe afsos hai aap achha feel nahi kar rahe. 😔 Apna khayal rakhna.", "sad"),
            ("achha nahi ho raha hoon", "Mujhe afsos hai aap achha feel nahi kar rahe. 😔 Apna khayal rakhna.", "sad"),
            ("bimari hai", "Mujhe afsos hai. 😔 Jaldi theek hona. Apna khayal rakhna.", "sad"),
            ("takleef ho rahi hai", "Mujhe afsos hai. 😔 Koi baat nahi, main yahan hoon.", "sad"),
            ("takleef ho raha hai", "Mujhe afsos hai. 😔 Koi baat nahi, main yahan hoon.", "sad"),
            ("dukhi hoon", "Main yahan hoon aapke liye. 😢 Baat karna chahein to batao.", "sad"),
            ("dukhi hoon", "Main yahan hoon aapke liye. 😢 Baat karna chahein to batao.", "sad"),
            ("zukaam hai", "Mujhe afsos hai. 😔 Rest karo aur jaldi theek hona.", "sad"),
            ("bukhar hai", "Mujhe afsos hai aap beemar hain. 😔 Rest karo.", "sadt"),
            ("main takleef mein hoon", "Mujhe afsos hai. 😔 Main madad kar sakta hoon.", "sad"),
            ("khush nahi hoon", "Kya baat hai? 😔 Main sunne ke liye yahan hoon.", "sad"),
            ("afsoos hai", "Mujhe bhi afsos hai. 😔 Kya main kuch madad kar sakta hoon?", "sad"),
            ("ro raha hoon", "Rona normal hai. 😢 Main yahan hoon aapke liye.", "sad"),
            ("ro rahi hoon", "Rona normal hai. 😢 Main yahan hoon aapke liye.", "sad"),
            ("main rota hoon", "Rona normal hai. 😢 Baat karo, main sunta hoon.", "sad"),
            ("main roti hoon", "Rona normal hai. 😢 Baat karo, main sunti hoon.", "sad"),
            ("sharab", "Aap sharab ki baat kar rahe hain. Main yahan hoon aapki madad ke liye. 💙", "sad"),
            ("peena", "Agar aapko takleef ho rahi hai to baat karna accha rahega. 💙", "sad"),
            ("tension hai", "Tension lena normal hai. 💆 Thoda relax karo.", "stressed"),
            ("preshan hoon", "Main samajhta hoon aap preshan hain. 💆 Saans lo.", "stressed"),
            ("preshan hoon", "Main samajhti hoon aap preshan hain. 💆 Saans lo.", "stressed"),
            ("gussa aa raha hai", "Gussa normal hai. 😤 Thoda saans lo.", "angry"),
            ("gussa aa rahi hai", "Gussa normal hai. 😤 Thoda saans lo.", "angry"),
            ("khush hoon", "Yeh sunke accha laga! 😊 Kya baat hai?", "happy"),
            ("khush hoon", "Yeh sunke accha laga! 😊 Kya baat hai?", "happy"),
            ("bahut khush hoon", "Kya baat! 😊 Aapki khushi mein mujhe bhi khushi.", "happy"),
            ("maza aa gaya", "Mujhe bhi maza aa gaya! 😊 Aur batao.", "happy"),
        ]
        
        for pattern, reply, emotion in URDU_PATTERNS:
            if pattern in text or pattern in original_text:
                return ProcessResponse(
                    reply=reply,
                    emotion=emotion,
                    intent="general_chat",
                    action=Action(type="none", target="", data={}),
                    status="ok",
                    options=[],
                    requires_confirmation=False
                )
        
        # Try to translate if not English and translation is available
        detected_language = 'unknown'
        if TRANSLATION_AVAILABLE and not text.replace("'", "").replace("!", "").replace("?", "").replace(".", "").isalpha():
            translated_text, detected_language = translate_to_english(original_text)
            if detected_language != 'en' and detected_language != 'unknown':
                print(f"Detected language: {detected_language}, Translated: {translated_text}")
        
        # Try to use LLM
        context = ""
        try:
            # First try local conversation context from Flutter
            if request.conversation_context:
                context = request.conversation_context
            else:
                # Fallback to RAG
                context = retrieve_context(request.user_id, request.text)
        except Exception as e:
            print(f"Context retrieval error: {e}")
            context = request.conversation_context or ""
        
        try:
            primary_output = call_primary_llm(original_text, context)
        except Exception as e:
            print(f"LLM call failed: {e}")
            return ProcessResponse(
                reply="I'm having trouble thinking right now. Please try again in a moment.",
                emotion="neutral",
                intent="general_chat",
                action=Action(type="none", target="", data={}),
                status="ok",
                options=[],
                requires_confirmation=False
            )
        
        response, needs_secondary = route(primary_output)
        
        if needs_secondary:
            decision, decision_response = analyze(primary_output, context)
            
            if decision == DecisionType.CONFIRM or decision == DecisionType.CLARIFY:
                try:
                    add_structured_data(
                        request.user_id,
                        primary_output.get("intent", "general_chat"),
                        primary_output.get("entities", {}),
                        primary_output.get("emotion", "neutral")
                    )
                except Exception:
                    pass
                reply = decision_response.reply if decision_response else "Understood."
                try:
                    add_conversation(request.user_id, request.text, reply)
                except Exception:
                    pass
                return decision_response
            
            if decision == DecisionType.CONVERSE:
                try:
                    add_structured_data(
                        request.user_id,
                        primary_output.get("intent", "general_chat"),
                        primary_output.get("entities", {}),
                        primary_output.get("emotion", primary_output.get("emotion", "neutral"))
                    )
                except Exception:
                    pass
                reply = decision_response.reply if decision_response else "Understood."
                try:
                    add_conversation(request.user_id, request.text, reply)
                except Exception:
                    pass
                return decision_response
            
            action_response = legacy_build_action_response(primary_output)
            
            # Check for web platform (no device actions)
            if action_response.action.type in ["open_app", "make_call", "send_message", "set_alarm"]:
                device_action = execute_tool(
                    action_response.action.type,
                    action_response.action.target,
                    action_response.action.data
                )
                
                # Return message saying it only works on Android
                return ProcessResponse(
                    reply=f"{action_response.reply}\n\nNote: This action works on Android devices only. On web, you'll need to do this manually.",
                    emotion=action_response.emotion,
                    intent=action_response.intent,
                    action=action_response.action,
                    status="ok",
                    options=[],
                    requires_confirmation=False,
                    device_action=device_action
                )
            
            if action_response.requires_confirmation:
                try:
                    add_structured_data(
                        request.user_id,
                        primary_output.get("intent", "general_chat"),
                        primary_output.get("entities", {}),
                        primary_output.get("emotion", "neutral")
                    )
                except Exception:
                    pass
                try:
                    add_conversation(request.user_id, request.text, action_response.reply)
                except Exception:
                    pass
                return action_response
            
            device_action = execute_tool(
                action_response.action.type,
                action_response.action.target,
                action_response.action.data
            )
            
            try:
                add_structured_data(
                    request.user_id,
                    primary_output.get("intent", "general_chat"),
                    primary_output.get("entities", {}),
                    primary_output.get("emotion", "neutral")
                )
            except Exception:
                pass
            
            try:
                add_conversation(request.user_id, request.text, action_response.reply)
            except Exception:
                pass
            
            return ProcessResponse(
                reply=action_response.reply,
                emotion=action_response.emotion,
                intent=action_response.intent,
                action=action_response.action,
                status="ok",
                options=[],
                requires_confirmation=device_action.get("requires_confirmation", False),
                device_action=device_action
            )
        
        try:
            add_structured_data(
                request.user_id,
                primary_output.get("intent", "general_chat"),
                primary_output.get("entities", {}),
                primary_output.get("emotion", primary_output.get("emotion", "neutral"))
            )
        except Exception:
            pass
        
        if response:
            try:
                add_conversation(request.user_id, request.text, response.reply)
            except Exception:
                pass
            return response
        else:
            fallback_response = ProcessResponse(
                reply="I'm here to help! What would you like me to do?",
                emotion="neutral",
                intent="general_chat",
                action=Action(type="none", target="", data={}),
                status="ok",
                options=[],
                requires_confirmation=False
            )
            try:
                add_conversation(request.user_id, request.text, fallback_response.reply)
            except Exception:
                pass
            return fallback_response
        
    except Exception as e:
        print(f"Error processing request: {e}")
        import traceback
        traceback.print_exc()
        return ProcessResponse(
            reply="Oops! Something went wrong. Please try again.",
            emotion="neutral",
            intent="general_chat",
            action=Action(type="none", target="", data={}),
            status="ok",
            options=[],
            requires_confirmation=False
        )


@router.post("/confirm_action", response_model=ProcessResponse)
async def confirm_action(request: ProcessRequest):
    """
    Endpoint to confirm and execute an action after user confirmation.
    """
    try:
        user_input = request.text.lower().strip()
        
        positive_keywords = ["yes", "yeah", "yep", "sure", "ok", "okay", "do it", "go ahead", "confirm", "send", "call"]
        negative_keywords = ["no", "nope", "nah", "cancel", "stop", "don't", "never mind", "nevermind"]
        
        is_positive = any(keyword in user_input for keyword in positive_keywords)
        is_negative = any(keyword in user_input for keyword in negative_keywords)
        
        if is_negative:
            return ProcessResponse(
                reply="No problem! I've cancelled that action. What else can I help you with?",
                emotion="neutral",
                intent="general_chat",
                action=Action(type="none", target="", data={}),
                status="ok",
                options=[],
                requires_confirmation=False
            )
        elif is_positive:
            primary_output = call_primary_llm(request.text, "")
            action_response = legacy_build_action_response(primary_output)
            
            device_action = execute_tool(
                action_response.action.type,
                action_response.action.target,
                action_response.action.data
            )
            
            return ProcessResponse(
                reply=f"Done! {device_action.get('message', 'Action completed.')}",
                emotion="happy",
                intent=action_response.intent,
                action=action_response.action,
                status="ok",
                options=[],
                requires_confirmation=False,
                device_action=device_action
            )
        else:
            return ProcessResponse(
                reply="I'm not sure I understood. Did you want to proceed? (yes/no)",
                emotion="neutral",
                intent="general_chat",
                action=Action(type="none", target="", data={}),
                status="need_clarification",
                options=["Yes, proceed", "No, cancel"]
            )
            
    except Exception as e:
        print(f"Error confirming action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/preferences")
async def get_preferences(user_id: str):
    """Get user preferences and history."""
    try:
        preferences = get_user_preferences(user_id)
        return {"user_id": user_id, "preferences": preferences}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/user/{user_id}/history")
async def clear_history(user_id: str):
    """Clear user conversation history."""
    from app.services.rag_service import clear_history as clear_rag_history
    try:
        clear_rag_history(user_id)
        return {"status": "ok", "message": f"History cleared for user {user_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
