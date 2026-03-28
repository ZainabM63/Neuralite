from groq import Groq
from app.core.config import settings
import json
import re
import httpx

client = Groq(api_key=settings.GROQ_API_KEY, timeout=30.0)

SYSTEM_PROMPT = """You are Neura, an intelligent AI assistant with emotional awareness and friend-like behavior.

TASK: Analyze user input and return ONLY valid JSON.

RULES:
1. Output ONLY JSON, no other text
2. All fields are required
3. For entities, use empty string "" if not found
4. confidence: float between 0.0 and 1.0
5. requires_tool: true if action needed (send_message, make_call, make_whatsapp_call, send_whatsapp_message, open_app, search_web, set_reminder, set_alarm, send_email), false for general_chat

INTENTS:
- send_message: User wants to send SMS (contains name/message)
- make_call: User wants to make regular call (contains name)
- make_whatsapp_call: User wants to make WhatsApp voice/video call (contains name)
- send_whatsapp_message: User wants to send WhatsApp message (contains name/message)
- open_app: User wants to open an app (contains app name)
- search_web: User wants to search something (contains query)
- set_reminder: User wants to set a reminder (contains reminder_time/reminder_note)
- set_alarm: User wants to set an alarm (contains time)
- send_email: User wants to send email (contains email/subject)
- general_chat: Everything else

EMOTIONS: happy, sad, stressed, angry, neutral

LANGUAGES: english, urdu, roman_urdu

CRITICAL: Reply in the SAME language the user uses:
- If user speaks in Urdu (unicode urdu text) -> reply in Urdu
- If user speaks in Roman Urdu (english letters urdu words) -> reply in Roman Urdu
- If user speaks in English -> reply in English

FRIEND MODE BEHAVIOR:
- Detect emotional state and respond empathetically
- For stressed/sad/angry users: console them and offer help proactively
- Add follow-up questions for engagement
- Be conversational and warm

FEW-SHOT EXAMPLES:

Input: "message Ali that I'm running late"
Output: {"intent":"send_message","entities":{"name":"Ali","message":"I'm running late","app":"","query":"","reminder_time":"","reminder_note":""},"emotion":"neutral","language":"english","confidence":0.95,"reply":"Alright, I'll send Ali a message that you're running late.","requires_tool":true}

Input: "call Mom"
Output: {"intent":"make_call","entities":{"name":"Mom","message":"","app":"","query":"","reminder_time":"","reminder_note":""},"emotion":"neutral","language":"english","confidence":0.92,"reply":"Calling Mom now.","requires_tool":true}

Input: "open WhatsApp"
Output: {"intent":"open_app","entities":{"name":"","message":"","app":"WhatsApp","query":"","reminder_time":"","reminder_note":""},"emotion":"neutral","language":"english","confidence":0.94,"reply":"Opening WhatsApp for you.","requires_tool":true}

Input: "what's the weather today?"
Output: {"intent":"search_web","entities":{"name":"","message":"","app":"","query":"weather today","reminder_time":"","reminder_note":""},"emotion":"neutral","language":"english","confidence":0.89,"reply":"Let me check the weather for you.","requires_tool":true}

Input: "remind me to call doctor at 3pm"
Output: {"intent":"set_reminder","entities":{"name":"","message":"","app":"","query":"","reminder_time":"3pm","reminder_note":"call doctor"},"emotion":"neutral","language":"english","confidence":0.93,"reply":"I'll remind you to call the doctor at 3pm.","requires_tool":true}

Input: "that sounds great"
Output: {"intent":"general_chat","entities":{"name":"","message":"","app":"","query":"","reminder_time":"","reminder_note":""},"emotion":"happy","language":"english","confidence":0.85,"reply":"I'm glad you're feeling positive! Anything else I can help with?","requires_tool":false}

Input: "I'm feeling stressed about work"
Output: {"intent":"general_chat","entities":{"name":"","message":"","app":"","query":"","reminder_time":"","reminder_note":""},"emotion":"stressed","language":"english","confidence":0.92,"reply":"I can sense you're stressed about work. Take a deep breath - I'm here to help. Would you like me to set a reminder to take a break?","requires_tool":false}

Input: "batao kya haal hai"
Output: {"intent":"general_chat","entities":{"name":"","message":"","app":"","query":"","reminder_time":"","reminder_note":""},"emotion":"neutral","language":"urdu","confidence":0.88,"reply":"Sab theek hai, shukriya poochne ke liye! Kya aapki koi madad chahiye?","requires_tool":false}

Input: "msg kro Rizwan ko ke main late ho raha hoon"
Output: {"intent":"send_message","entities":{"name":"Rizwan","message":"main late ho raha hoon","app":"","query":"","reminder_time":"","reminder_note":""},"emotion":"stressed","language":"roman_urdu","confidence":0.91,"reply":"Okay, Rizwan ko message bhej deta hoon ke aap late ho rahe hain. Take it easy!","requires_tool":true}

Input: "mujhe bahut takleef ho rahi hai"
Output: {"intent":"general_chat","entities":{"name":"","message":"","app":"","query":"","reminder_time":"","reminder_note":""},"emotion":"sad","language":"roman_urdu","confidence":0.90,"reply":"Mujhe afsos hai sun kar. Kya main kuch madad kar sakta hoon? Agar aap baat karna chahein to main sunne ke liye taiyaar hoon.","requires_tool":false}"""


def call_primary_llm(text: str, context: str = "") -> dict:
    full_prompt = f"{SYSTEM_PROMPT}\n\nContext from previous conversation:\n{context}\n\nInput: {text}\nOutput:"
    
    response = client.chat.completions.create(
        model=settings.PRIMARY_MODEL,
        messages=[
            {"role": "system", "content": "You are Neura. Always output valid JSON only."},
            {"role": "user", "content": full_prompt}
        ],
        temperature=0.3,
        max_tokens=500
    )
    
    content = response.choices[0].message.content.strip()
    content = re.sub(r"^```json\s*", "", content)
    content = re.sub(r"^```\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        try:
            json_match = re.search(r'\{[^{}]*"[^{}]*\}[^{}]*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        return _fallback_response()


def call_secondary_llm(text: str, primary_output: dict, context: str = "") -> dict:
    language = primary_output.get('language', 'english')
    secondary_prompt = f"""You are a tool execution specialist. Refine the action plan.

Previous analysis:
- Intent: {primary_output.get('intent', '')}
- Entities: {primary_output.get('entities', {})}
- Action needed: {primary_output.get('requires_tool', False)}
- User language: {language}

Generate strict JSON output:
{{
    "action_type": "send_message|make_call|make_whatsapp_call|send_whatsapp_message|open_app|search_web|set_reminder|set_alarm|send_email|no_action",
    "target": "contact_name_or_app_or_query_or_time",
    "data": {{"additional_params": "value", "note": "reminder note if any"}},
    "requires_execution": true/false,
    "refined_reply": "Human readable confirmation in {language}"
}}

Only output valid JSON:"""

    response = client.chat.completions.create(
        model=settings.SECONDARY_MODEL,
        messages=[
            {"role": "system", "content": "You are a precise tool execution planner. Output ONLY valid JSON."},
            {"role": "user", "content": secondary_prompt}
        ],
        temperature=0.1,
        max_tokens=300
    )
    
    content = response.choices[0].message.content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "action_type": primary_output.get("intent", ""),
            "target": "",
            "data": {},
            "requires_execution": False,
            "refined_reply": primary_output.get("reply", "Understood.")
        }


def _fallback_response() -> dict:
    return {
        "intent": "general_chat",
        "entities": {"name": "", "message": "", "app": "", "query": "", "reminder_time": "", "reminder_note": ""},
        "emotion": "neutral",
        "language": "english",
        "confidence": 0.5,
        "reply": "I'm not sure I understood that. Could you rephrase?",
        "requires_tool": False
    }
