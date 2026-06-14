import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

import config
from handlers import business, panel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> web.Application:
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()
    dp.include_router(panel.router)
    dp.include_router(business.router)

    async def on_startup(app: web.Application):
        await bot.set_webhook(
            url=config.WEBHOOK_URL,
            secret_token=config.WEBHOOK_SECRET or None,
            allowed_updates=[
                "message",
                "callback_query",
                "business_connection",
                "business_message",
                "edited_business_message",
                "deleted_business_messages",
            ],
            drop_pending_updates=True,
        )
        logger.info("Webhook set to: %s", config.WEBHOOK_URL)

    async def on_shutdown(app: web.Application):
        await bot.session.close()

    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # فحص صحة للخدمة (Render يستخدمه + يبقي الخدمة حية)
    async def health(request):
        return web.Response(text="ok")

    app.router.add_get("/", health)

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=config.WEBHOOK_SECRET or None,
    ).register(app, path=config.WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)
    return app


if __name__ == "__main__":
    application = create_app()
    web.run_app(application, host=config.HOST, port=config.PORT)
