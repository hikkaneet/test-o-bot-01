import asyncio
import logging
from aiogram import Bot, Dispatcher

import config
from functions import create_table, create_answers_table
from handlers import router

# Запуск процесса поллинга новых апдейтов
async def main():
    # Объект бота, token храниться в отдельном файле config.py
    bot = Bot(token=config.API_TOKEN)
    # Диспетчер
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    # Запускаем создание таблицы базы данных
    await create_table()
    await create_answers_table()
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Включаем логирование, чтобы не пропустить важные сообщения
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())