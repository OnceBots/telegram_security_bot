import asyncio, logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from .config import Settings
from .database import Database
from .handlers import setup_handlers
from .logging_setup import configure_logging
from .service import SecurityService
from .web import make_health_app
logger=logging.getLogger("App")
async def main()->None:
    settings=Settings(); settings.validate(); configure_logging(settings.log_level)
    bot=Bot(token=settings.bot_token,default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp=Dispatcher(); db=Database(settings); await db.connect(); service=SecurityService(bot,db,settings); setup_handlers(dp,service)
    app=make_health_app(db)
    if settings.mode=="webhook":
        webhook_url=f"{settings.webhook_base_url}{settings.webhook_path}"
        async def on_startup()->None:
            await bot.set_webhook(webhook_url,secret_token=settings.webhook_secret,drop_pending_updates=settings.drop_pending_updates,allowed_updates=dp.resolve_used_update_types())
            logger.info("Webhook configurado.",extra={"mode":"webhook"})
        async def on_shutdown()->None:
            await service.shutdown(); await bot.delete_webhook(); await db.close()
        dp.startup.register(on_startup); dp.shutdown.register(on_shutdown)
        SimpleRequestHandler(dispatcher=dp,bot=bot,handle_in_background=True,secret_token=settings.webhook_secret).register(app,path=settings.webhook_path)
        setup_application(app,dp,bot=bot)
        runner=web.AppRunner(app); await runner.setup(); await web.TCPSite(runner,"0.0.0.0",settings.port).start(); logger.info("Servidor webhook iniciado.",extra={"mode":"webhook"})
        try: await asyncio.Event().wait()
        finally: await runner.cleanup()
        return
    runner=web.AppRunner(app); await runner.setup(); await web.TCPSite(runner,"0.0.0.0",settings.port).start()
    await bot.delete_webhook(drop_pending_updates=settings.drop_pending_updates); logger.info("Bot iniciado con polling.",extra={"mode":"polling"})
    try: await dp.start_polling(bot,allowed_updates=dp.resolve_used_update_types())
    finally: await service.shutdown(); await db.close(); await runner.cleanup(); await bot.session.close()
