from dataclasses import dataclass
import secrets
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

@dataclass(frozen=True, slots=True)
class CaptchaChallenge:
    a: int
    b: int
    correct: int
    options: tuple[int, int, int, int]

def create_challenge(*, min_a=2, max_a=15, min_b=1, max_b=14) -> CaptchaChallenge:
    if min_a > max_a or min_b > max_b: raise ValueError("Rangos CAPTCHA inválidos")
    a = secrets.randbelow(max_a-min_a+1)+min_a
    b = secrets.randbelow(max_b-min_b+1)+min_b
    correct = a+b
    decoys=set(); offsets=(-4,-3,-2,-1,1,2,3,4)
    while len(decoys)<3:
        candidate=correct+secrets.choice(offsets)
        if candidate>0 and candidate!=correct: decoys.add(candidate)
    options=list(decoys)+[correct]
    secrets.SystemRandom().shuffle(options)
    return CaptchaChallenge(a,b,correct,tuple(options))

def build_keyboard(session_id: str, options: tuple[int,int,int,int]) -> InlineKeyboardMarkup:
    def button(value:int) -> InlineKeyboardButton:
        return InlineKeyboardButton(text=f"📌 {value}", callback_data=f"chk:{session_id}:{value}")
    return InlineKeyboardMarkup(inline_keyboard=[[button(options[0]),button(options[1])],[button(options[2]),button(options[3])]])
