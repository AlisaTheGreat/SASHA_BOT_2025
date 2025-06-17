from telegram.ext import ApplicationBuilder, CommandHandler
from handlers.common import start_command, iam_command, status_command
from handlers.talk import talk_command
from handlers.actions import feed_command, hug_command, ...
from handlers.teach import teach_command
from state_manager import loade_state
from config import BOT_token

# Всё собрали, теперь запуск бота
async def main():
    loade_state()
    app = ApplicationBuilder().token(BOT_token).build()

    app.add_handler(CommandHandler("iam", iam_command))
    app.add_handler(CommandHandler("start", start_command))

    # Зарегистрировать хендлеры для команд

    app.add_handler(CommandHandler("talk", talk_command))

    app.add_handler(CommandHandler("feed", feed_command))
    app.add_handler(CommandHandler("hug", hug_command))
    app.add_handler(CommandHandler("play", play_command))
    app.add_handler(CommandHandler("praise", praise_command))
    app.add_handler(CommandHandler("sleep", sleep_command))


    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("teach", teach_command))

    app.job_queue.run_once(lambda _: asyncio.create_task(periodic_check(app)), when=1)

    print("Бот запущен. Ожидание команд...")

    await app.run_polling()


if __name__ == "__main__":
    import asyncio
    import nest_asyncio

    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
