import asyncio, html, logging, time, uuid
from datetime import datetime, timezone
from dataclasses import dataclass
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import ChatJoinRequest, CallbackQuery
from .captcha import build_keyboard, create_challenge
from .config import Settings
from .database import Database
from .locales import get_text
from .metrics import ACTIVE_SESSIONS, CAPTCHA_APPROVED, CAPTCHA_REJECTED, CAPTCHA_STARTED, CAPTCHA_TIMEOUT, HANDLER_ERRORS, VERIFICATION_DURATION
from .rate_limit import RateLimiter
logger=logging.getLogger("SecurityService")
@dataclass(slots=True)
class SessionTask:
    task: asyncio.Task
    created_monotonic: float
class SecurityService:
    def __init__(self,bot:Bot,db:Database,settings:Settings):
        self.bot=bot; self.db=db; self.settings=settings
        self.rate_limiter=RateLimiter(settings.join_rate_limit,settings.join_rate_window_seconds)
        self._timers:dict[str,SessionTask]={}; self._lock=asyncio.Lock()
    async def handle_join_request(self,request:ChatJoinRequest)->None:
        user,chat=request.from_user,request.chat; user_id,chat_id=user.id,chat.id; lang=user.language_code
        if not await self.rate_limiter.allow(user_id):
            await self.db.log_access(user_id=user_id,chat_id=chat_id,status="RATE_LIMITED",details="Join request rate limit")
            await self._safe_decline(chat_id,user_id)
            try: await self.bot.send_message(chat_id=user_id,text=get_text(lang,"rate_limited"))
            except Exception: pass
            return
        await self.db.delete_user_session(user_id)
        session_id=uuid.uuid4().hex[:12]
        challenge=create_challenge(min_a=self.settings.captcha_min_a,max_a=self.settings.captcha_max_a,min_b=self.settings.captcha_min_b,max_b=self.settings.captcha_max_b)
        session={"session_id":session_id,"user_id":user_id,"chat_id":chat_id,"chat_title":chat.title or "Telegram","correct":challenge.correct,"attempts":0,"lang":lang,"created_at":datetime.now(timezone.utc),"expires_at":Database.expiration(self.settings.captcha_timeout)}
        body=f"{get_text(lang,'challenge_title')}\n\n"+get_text(lang,"challenge_body",name=html.escape(user.first_name or "usuario"),chat_title=html.escape(chat.title or "Telegram"),a=challenge.a,b=challenge.b,timeout=self.settings.captcha_timeout,attempts=self.settings.captcha_max_attempts)
        try:
            msg=await self.bot.send_message(chat_id=user_id,text=body,reply_markup=build_keyboard(session_id,challenge.options))
            session["message_id"]=msg.message_id; await self.db.create_session(session)
            task=asyncio.create_task(self._timeout_worker(session_id,msg.message_id),name=f"captcha-timeout-{session_id}")
            async with self._lock: self._timers[session_id]=SessionTask(task,time.monotonic())
            ACTIVE_SESSIONS.inc(); CAPTCHA_STARTED.inc()
            await self.db.log_access(user_id=user_id,chat_id=chat_id,status="CHALLENGE_SENT",session_id=session_id)
            logger.info("CAPTCHA enviado.",extra={"user_id":user_id,"chat_id":chat_id,"session_id":session_id})
        except (TelegramForbiddenError,TelegramBadRequest) as exc:
            await self._cancel_timer(session_id); await self._safe_decline(chat_id,user_id)
            await self.db.log_access(user_id=user_id,chat_id=chat_id,status="REJECTED_AUTO",details=f"Telegram error: {type(exc).__name__}")
        except Exception:
            await self._cancel_timer(session_id); HANDLER_ERRORS.inc(); logger.exception("Error creando CAPTCHA.",extra={"user_id":user_id,"chat_id":chat_id}); await self._safe_decline(chat_id,user_id)
    async def handle_callback(self,call:CallbackQuery)->None:
        parts=(call.data or "").split(":")
        if len(parts)!=3 or parts[0]!="chk": await call.answer(); return
        _,session_id,answer_raw=parts
        try: selected=int(answer_raw)
        except ValueError: await call.answer(); return
        session=await self.db.get_session(session_id)
        if not session:
            await call.answer(get_text(call.from_user.language_code,"session_expired"),show_alert=True); return
        if call.from_user.id!=session["user_id"]:
            await call.answer(get_text(call.from_user.language_code,"session_expired"),show_alert=True); return
        duration=max(0.0,time.time()-session["created_at"].timestamp()) if session.get("created_at") else 0.0
        if selected==session["correct"]:
            consumed=await self.db.consume_session(session_id)
            if not consumed: await call.answer(get_text(session["lang"],"session_expired"),show_alert=True); return
            await self._cancel_timer(session_id); ACTIVE_SESSIONS.dec(); VERIFICATION_DURATION.observe(duration)
            try:
                await self.bot.approve_chat_join_request(chat_id=session["chat_id"],user_id=session["user_id"]); CAPTCHA_APPROVED.inc()
                await self.db.log_access(user_id=session["user_id"],chat_id=session["chat_id"],status="APPROVED",details="Correct answer",session_id=session_id)
                if call.message: await call.message.edit_text(get_text(session["lang"],"success",chat_title=html.escape(session["chat_title"])))
            except Exception:
                HANDLER_ERRORS.inc(); logger.exception("Error aprobando solicitud.",extra={"user_id":session["user_id"],"chat_id":session["chat_id"],"session_id":session_id})
                await self.db.log_access(user_id=session["user_id"],chat_id=session["chat_id"],status="APPROVAL_ERROR",details="Telegram approval failed",session_id=session_id)
                if call.message: await call.message.edit_text(get_text(session["lang"],"generic_error"))
            await call.answer(); return
        updated=await self.db.increment_attempts(session_id)
        if updated is not None and updated["attempts"]<self.settings.captcha_max_attempts:
            remaining=self.settings.captcha_max_attempts-updated["attempts"]
            if call.message:
                try: await call.message.edit_text(get_text(updated["lang"],"wrong_retry",attempts=remaining),reply_markup=build_keyboard(session_id,self._retry_options(updated["correct"])))
                except Exception: logger.exception("No se pudo actualizar CAPTCHA.",extra={"session_id":session_id})
            await call.answer(); return
        consumed=await self.db.consume_session(session_id)
        if not consumed: await call.answer(get_text(session["lang"],"session_expired"),show_alert=True); return
        await self._cancel_timer(session_id); ACTIVE_SESSIONS.dec(); VERIFICATION_DURATION.observe(duration)
        await self._safe_decline(session["chat_id"],session["user_id"]); CAPTCHA_REJECTED.inc()
        await self.db.log_access(user_id=session["user_id"],chat_id=session["chat_id"],status="REJECTED",details=f"Incorrect answer: {selected}",session_id=session_id)
        if call.message: await call.message.edit_text(get_text(session["lang"],"wrong"))
        await call.answer()
    async def _timeout_worker(self,session_id:str,message_id:int)->None:
        try:
            await asyncio.sleep(self.settings.captcha_timeout)
            session=await self.db.consume_session(session_id)
            if not session: return
            ACTIVE_SESSIONS.dec(); CAPTCHA_TIMEOUT.inc()
            if session.get("created_at"): VERIFICATION_DURATION.observe(max(0.0,time.time()-session["created_at"].timestamp()))
            await self._safe_decline(session["chat_id"],session["user_id"])
            await self.db.log_access(user_id=session["user_id"],chat_id=session["chat_id"],status="TIMEOUT",details="Verification expired",session_id=session_id)
            try: await self.bot.edit_message_text(chat_id=session["user_id"],message_id=message_id,text=get_text(session["lang"],"timeout",timeout=self.settings.captcha_timeout))
            except Exception: pass
        except asyncio.CancelledError: return
        except Exception:
            HANDLER_ERRORS.inc(); logger.exception("Error en timeout worker.",extra={"session_id":session_id})
        finally:
            async with self._lock: self._timers.pop(session_id,None)
    async def _cancel_timer(self,session_id:str)->None:
        async with self._lock: holder=self._timers.pop(session_id,None)
        if holder:
            holder.task.cancel()
            try: await holder.task
            except asyncio.CancelledError: pass
    async def shutdown(self)->None:
        async with self._lock: holders=list(self._timers.values()); self._timers.clear()
        for holder in holders: holder.task.cancel()
        for holder in holders:
            try: await holder.task
            except asyncio.CancelledError: pass
    async def _safe_decline(self,chat_id:int,user_id:int)->None:
        try: await self.bot.decline_chat_join_request(chat_id=chat_id,user_id=user_id)
        except Exception: logger.warning("No se pudo rechazar solicitud.",extra={"user_id":user_id,"chat_id":chat_id},exc_info=True)
    @staticmethod
    def _retry_options(correct:int)->tuple[int,int,int,int]:
        pool=[]
        for candidate in (correct-4,correct-2,correct+2,correct+4,correct+1,correct-1):
            if candidate>0 and candidate!=correct and candidate not in pool: pool.append(candidate)
            if len(pool)==3: break
        options=pool+[correct]; return tuple(options)  # type: ignore[return-value]
