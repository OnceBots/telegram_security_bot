from aiohttp import web
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from .database import Database
async def health(request:web.Request)->web.Response: return web.json_response({"status":"ok","service":"telegram-security-bot"})
async def ready(request:web.Request)->web.Response:
    db:Database=request.app["db"]
    if await db.is_ready(): return web.json_response({"status":"ready"})
    return web.json_response({"status":"not_ready"},status=503)
async def metrics(request:web.Request)->web.Response:
    return web.Response(body=generate_latest(),headers={"Content-Type":CONTENT_TYPE_LATEST})
def make_health_app(db:Database)->web.Application:
    app=web.Application(); app["db"]=db
    app.router.add_get("/",health); app.router.add_get("/health",health); app.router.add_get("/ready",ready); app.router.add_get("/metrics",metrics)
    return app
