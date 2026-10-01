from security_bot.locales import get_text, normalize_language

def test_language_fallback():
    assert normalize_language("es-AR")=="es"; assert normalize_language("fr")=="es"

def test_translation_format():
    text=get_text("es","challenge_body",name="Ana",chat_title="Grupo",a=2,b=3,timeout=120,attempts=2)
    assert "Ana" in text and "Grupo" in text and "2 + 3" in text
