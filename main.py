from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN:Final = '7315336925:AAH-dKTF6dXXoRneuc9fEQg-nL62TAL6sSo'
BOT_NAME:Final = '@crypto737263_bot'

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello! This is Crypto Bot, how can i help.')


if __name__ == '__main__':
    print('started bot')

    app = Application.builder().token(TOKEN).build()


    app.add_handler(CommandHandler('start',start_command))

    print('polling---')

    app.run_polling(poll_interval=3)