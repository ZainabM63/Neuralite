from googletrans import Translator

translator = Translator()

def translate_to_english(text: str) -> tuple[str, str]:
    """
    Detects language and translates to English if needed.
    Returns: (translated_text, detected_language)
    """
    try:
        detection = translator.detect(text)
        detected_lang = detection.lang
        confidence = detection.confidence
        
        if detected_lang == 'en' or confidence > 0.9:
            return text, 'english'
        
        if detected_lang in ['ur', 'hi', 'ne']:
            translated = translator.translate(text, src=detected_lang, dest='en')
            return translated.text, detected_lang
        
        return text, 'unknown'
    except Exception as e:
        print(f"Translation error: {e}")
        return text, 'unknown'


def translate_from_english(text: str, target_lang: str) -> str:
    """
    Translates English text to target language for TTS.
    """
    if target_lang == 'en':
        return text
    
    try:
        translated = translator.translate(text, src='en', dest=target_lang)
        return translated.text
    except Exception as e:
        print(f"Translation error: {e}")
        return text
