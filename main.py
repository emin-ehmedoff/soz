import os
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Chat
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext, Filters
from dotenv import load_dotenv
from database.scores import update_scores, get_top_users, get_top_groups, get_group_top_users, get_started_users_count, get_groups_count, get_total_games_started
from words import words
from database.models import get_db
from game import game, stop_game, check_answer, button_callback
from database.scores import get_user_group_info, get_user_global_info

load_dotenv()

# Bot sahibi Telegram ID (bot sahibinin Telegram ID-sini buraya əlavə edin)
BOT_OWNER_ID = 5273794514  # Bot sahibinin ID-sini buraya əlavə edin

# Global dəyişənlər
games = {}  # Aktiv oyunları təyin etmək üçün istifadə edilən lüğət
game_play_count = 0  # Botla neçə dəfə oyun oynandığını təyin etmək üçün istifadə edilən dəyişən



# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)



def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_first_name = update.message.from_user.first_name

    # Yalnız şəxsi mesajlarda işləsin
    if update.effective_chat.type != Chat.PRIVATE:
        return

    # Kullanıcıyı MongoDB'ye kaydet
    db = get_db()
    db.started_users.update_one(
        {'user_id': user_id},
        {'$set': {'first_name': user_first_name}},
        upsert=True
    )

    # Düymələrin tərtibatı
    keyboard = [
        [InlineKeyboardButton("Məni qrupa əlavə et", url="https://t.me/joinchat/your_group_invite_link")],
        [InlineKeyboardButton("Sahibim", url="https://t.me/username"), InlineKeyboardButton("Kömək", callback_data='help')],
        [InlineKeyboardButton("Dəstək", url="https://t.me/support")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text('Səni qrupa əlavə etmək üçün aşağıdakı düymələrdən istifadə edə bilərsən:', reply_markup=reply_markup)

# Help funksiyası
def help_command(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    # Kömək məlumatı və geri qayt düyməsi
    keyboard = [
        [InlineKeyboardButton("Geri Qayıt", callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    help_text = "Bu botun komandaları:\n\n" \
                "/start - Botu başlatmaq\n" \
                "/help - Kömək məlumatı\n" \
                "/support - Dəstək almaq üçün\n"

    query.edit_message_text(text=help_text, reply_markup=reply_markup)

# Back funksiyası
def back_command(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    # Start menyusunu yenidən göstər
    keyboard = [
        [InlineKeyboardButton("Məni qrupa əlavə et", url="https://t.me/joinchat/your_group_invite_link")],
        [InlineKeyboardButton("Sahibim", url="https://t.me/username"), InlineKeyboardButton("Kömək", callback_data='help')],
        [InlineKeyboardButton("Dəstək", url="https://t.me/support")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(text='Səni qrupa əlavə etmək üçün aşağıdakı düymələrdən istifadə edə bilərsən:', reply_markup=reply_markup)


def bot_added_to_group(update: Update, context: CallbackContext):
    chat = update.effective_chat

    # Yalnız grup və süper grup tiplerini kontrol edin
    if chat.type not in [Chat.GROUP, Chat.SUPERGROUP]:
        return

    # Grubu MongoDB'ye kaydet
    db = get_db()
    db.groups.update_one(
        {'group_id': chat.id},
        {'$set': {'group_name': chat.title}},
        upsert=True
    )


# Stats command (sadece bot sahibi üçün)
def stats(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    # Yalnız bot sahibinə işləməsini təmin edin
    if user_id != BOT_OWNER_ID:
        update.message.reply_text("⚠️ Bu komanda yalnız bot sahibi üçün nəzərdə tutulub!")
        return
    
    # Botu başlatan istifadəçilərin sayını hesablayın
    started_users_count = get_started_users_count()
    
    # Botun olduğu qrupların sayını hesablayın
    group_count = get_groups_count()
    
    # Başlatılan toplam oyun sayını hesablayın
    total_games_started = get_total_games_started()

    # Aktiv oyunların sayını və toplam oyun sayını hesablayın
    active_game_count = sum(1 for game in games.values() if game.is_active)
    total_games_played = game_play_count

    # Statistik məlumatları göstərin
    stats_message = f"""
    📊 Bot Statistikas:
    - Botu başlatan istifadəçilərin sayı: {started_users_count}
    - Botun olduğu qrupların sayı: {group_count}
    - Başlatılan toplam oyun sayı: {total_games_started}
    - Aktiv oyunların sayı: {active_game_count}
    - Toplam oyun sayı: {total_games_played}
    """
    update.message.reply_text(stats_message)




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
        logger.error('Top qruplar xətası: %s', error)
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
            if 'first_name' in user and 'score' in user:
                leaderboard += f"{index}. {user['first_name']} - {user['score']} xal\n"
            else:
                logger.error(f"Missing data for user: {user}")

        context.bot.send_message(chat_id, leaderboard)
    except Exception as error:
        logger.error('Qrup top oyunçular xətası: %s', error)
        context.bot.send_message(chat_id, "⚠️ Xəta baş verdi. Zəhmət olmasa yenidən cəhd edin.")

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
    db = get_db()  # db obyektini burada təyin edin
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

        dp.add_handler(CommandHandler("game", game))
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("stats", stats))  # Yeni komanda əlavə edildi
        dp.add_handler(CallbackQueryHandler(help_command, pattern='^help$'))
        dp.add_handler(CallbackQueryHandler(back_command, pattern='^back$'))
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
