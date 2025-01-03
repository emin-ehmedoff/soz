import os
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler, CallbackQueryHandler, CallbackContext
from dotenv import load_dotenv
from database.scores import update_scores, get_top_users, get_top_groups, get_group_top_users
from words import words
from database.models import get_db
from game import start_game, stop_game, check_answer, button_callback

load_dotenv()

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)






def show_top_players(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    try:
        users = get_top_users(25)

        if not users:
            context.bot.send_message(chat_id, "⚠️ Hələ heç bir oyunçu yoxdur!")
            return

        leaderboard = "🏅 Top 25 İstifadəçi:\n\n"
        for index, user in enumerate(users, 1):
            leaderboard += f"{index}. {user['first_name']} - {user['totalScore']} xal\n"

        context.bot.send_message(chat_id, leaderboard)
    except Exception as error:
        logger.error('Top oyunçular xətası: %s', error)
        context.bot.send_message(chat_id, "⚠️ Xəta baş verdi. Zəhmət olmasa yenidən cəhd edin.")

def show_top_groups(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    try:
        groups = get_top_groups(25)

        if not groups:
            context.bot.send_message(chat_id, "⚠️ Hələ heç bir qrup yoxdur!")
            return

        leaderboard = "🏅 Top 25 Qrup:\n\n"
        for index, group in enumerate(groups, 1):
            leaderboard += f"{index}. {group['groupName']} - {group['totalScore']} xal\n"

        context.bot.send_message(chat_id, leaderboard)
    except Exception as error:
        logger.error('Top qrfirst_nameuplar xətası: %s', error)
        context.bot.send_message(chat_id, "⚠️ Xəta baş verdi. Zəhmət olmasa yenidən cəhd edin.")

def show_current_group(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    try:
        users = get_group_top_users(chat_id, 25)

        if not users:
            context.bot.send_message(chat_id, "⚠️ Bu qrupda hələ heç bir oyunçu yoxdur!")
            return

        leaderboard = "🏅 Cari Qrup üzrə Top 25 İstifadəçi:\n\n"
        for index, user in enumerate(users, 1):
            leaderboard += f"{index}. {user['first_name']} - {user['score']} xal\n"

        context.bot.send_message(chat_id, leaderboard)
    except Exception as error:
        logger.error('Qrup top oyunçular xətası: %s', error)
        context.bot.send_message(chat_id, "⚠️ Xəta baş verdi. Zəhmət olmasa yenidən cəhd edin.")

def start_bot():
    logger.info('🚀 Bot başladılır...')
    try:
        get_db()
        updater = Updater(os.getenv('BOT_TOKEN'), use_context=True)
        dp = updater.dispatcher

        dp.add_handler(CommandHandler("start", start_game))
        dp.add_handler(CommandHandler("stop", stop_game))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, check_answer))
        dp.add_handler(CallbackQueryHandler(button_callback))

        dp.add_handler(CommandHandler("topplayers", show_top_players))
        dp.add_handler(CommandHandler("topgroups", show_top_groups))
        dp.add_handler(CommandHandler("currentgroup", show_current_group))

        updater.start_polling()
        updater.idle()
    except Exception as error:
        logger.error('Bot başlatma xətası: %s', error)

if __name__ == '__main__':
    start_bot()