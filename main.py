import os
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext, Filters
from dotenv import load_dotenv
from database.scores import update_scores, get_top_users, get_top_groups, get_group_top_users
from words import words
from database.models import get_db
from game import start_game, stop_game, check_answer, button_callback
from database.scores import get_user_group_info, get_user_global_info

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


def show_user_rating(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    try:
        user_group_info = get_user_group_info(user_id, chat_id)
        user_global_info = get_user_global_info(user_id)

        if not user_group_info or not user_global_info:
            context.bot.send_message(chat_id, "⚠️ İstifadəçi haqqında məlumat tapılmadı!")
            return

        message = (
            f"Bu qrupda:\n"
            f"✅ Doğru cavablar: {user_group_info['correct_answers']} dəfə\n"
            f"📢 Aparıcı olma: {user_group_info['host_count']} dəfə\n"
            f"📈 Reytinq: {user_group_info['rank']} sırada\n"
            f"⭐ Ümumi xal: {user_group_info['total_score']}\n\n"
            f"Ümumi:\n"
            f"✅ Doğru cavablar: {user_global_info['correct_answers']} dəfə\n"
            f"📢 Aparıcı olma: {user_global_info['host_count']} dəfə\n"
            f"📈 Global reytinq: {user_global_info['rank']} sırada\n"
            f"⭐ Ümumi xal: {user_global_info['total_score']}\n"
        )

        context.bot.send_message(chat_id, message)
    except Exception as error:
        logger.error('İstifadəçi reytinqi xətası: %s', error)
        context.bot.send_message(chat_id, "⚠️ Xəta baş verdi. Zəhmət olmasa yenidən cəhd edin.")

def show_top_hosts(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    try:
        # Müvafiq məlumatları əldə edin (bu hissəni öz tələblərinizə uyğunlaşdırın)
        hosts = db.user_groups.aggregate([
            {
                '$group': {
                    '_id': '$user_id',
                    'host_count': {'$sum': '$host_count'}
                }
            },
            {'$sort': {'host_count': -1}},
            {'$limit': 25}
        ])

        hosts = list(hosts)
        if not hosts:
            context.bot.send_message(chat_id, "⚠️ Hələ heç bir aparıcı yoxdur!")
            return

        leaderboard = "🏅 Top 25 Aparıcı:\n\n"
        for index, host in enumerate(hosts, 1):
            user = db.users.find_one({'user_id': host['_id']})
            leaderboard += f"{index}. {user['first_name']} - {host['host_count']} dəfə\n"

        context.bot.send_message(chat_id, leaderboard)
    except Exception as error:
        logger.error('Top aparıcılar xətası: %s', error)
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
        dp.add_handler(CommandHandler("raparici", show_top_hosts))  
        dp.add_handler(CommandHandler("myreytinq", show_user_rating))  # Yeni komut əlavə edildi

        updater.start_polling()
        updater.idle()
    except Exception as error:
        logger.error('Bot başlatma xətası: %s', error)

if __name__ == '__main__':
    start_bot()
