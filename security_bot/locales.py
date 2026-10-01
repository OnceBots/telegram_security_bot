import json
from pathlib import Path
from typing import Any
LOCALE_DIR=Path(__file__).resolve().parent.parent/"locales"

def load_translations()->dict[str,dict[str,Any]]:
    data={p.stem:json.loads(p.read_text(encoding="utf-8")) for p in LOCALE_DIR.glob("*.json")}
    if "es" not in data: raise RuntimeError("Falta locales/es.json")
    return data
TRANSLATIONS=load_translations()

def normalize_language(lang_code:str|None)->str:
    lang=(lang_code or "es").split("-")[0].lower()
    return lang if lang in TRANSLATIONS else "es"

def get_text(lang_code:str|None,key:str,**kwargs:Any)->str:
    lang=normalize_language(lang_code)
    template=TRANSLATIONS[lang].get(key,TRANSLATIONS["es"].get(key,key))
    return template.format(**kwargs) if kwargs else template
