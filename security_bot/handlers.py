import logging
from aiogram import Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import ChatJoinRequest, CallbackQuery, Message
from .locales import get_text
from .metrics import HANDLER_ERRORS
from .service import SecurityService
logger=logging.getLogger("Handlers")

def setup_handlers(dp:Dispatcher,service:SecurityService)->Router:
    router=Router(name="security"); dp.include_router(router)
    @router.message(CommandStart())
    async def handle_start(message:Message)->None:
        try: await message.answer(get_text(message.from_user.language_code,"start"))
        except Exception: HANDLER_ERRORS.inc(); logger.exception("Error en /start.")
    @router.chat_join_request()
    async def handle_join_request(request:ChatJoinRequest)->None:
        try: await service.handle_join_request(request)
        except Exception: HANDLER_ERRORS.inc(); logger.exception("Error en ChatJoinRequest.")
    @router.callback_query(F.data.startswith("chk:"))
    async def handle_captcha(call:CallbackQuery)->None:
        try: await service.handle_callback(call)
        except Exception:
            HANDLER_ERRORS.inc(); logger.exception("Error en callback CAPTCHA.")
            try: await call.answer(get_text(call.from_user.language_code,"generic_error"),show_alert=True)
            except Exception: pass
    return router
