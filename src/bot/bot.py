from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from src.core.config import settings

_bot_enabled = settings.bot_token and settings.bot_token != "disabled"

if _bot_enabled:
    from aiogram.fsm.storage.redis import RedisStorage
    from redis.asyncio import Redis

    redis = Redis.from_url(settings.redis_url)
    storage = RedisStorage(redis)
else:
    storage = MemoryStorage()

bot = Bot(
    token=settings.bot_token if _bot_enabled else "0:placeholder",
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher(storage=storage)
