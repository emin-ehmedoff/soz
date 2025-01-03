from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from database.scores import update_scores
from words import words  # words obyektini burada import edin
from database.models import get_db  # db obyektini burada import edin
import random
import logging
import time

class Game:
    def __init__(self):
        self.host = None
        self.current_word = None
        self.is_active = False
        self.mode = None  # Game mode (None, "full", "host")
        self.last_activity_time = time.time()  # Sonuncu aktivlik vaxtı

    def set_host(self, user_id, username, mode=None):
        self.host = {'id': user_id, 'username': username}
        self.current_word = random.choice(words)
        if mode is not None:
            self.mode = mode
        self.last_activity_time = time.time()

    def remove_host(self):
        self.host = None
        self.current_word = None
        self.last_activity_time = time.time()

    def start_game(self):
        self.is_active = True
        self.last_activity_time = time.time()

    def stop_game(self):
        self.is_active = False
        self.remove_host()
        self.mode = None

    def update_last_activity_time(self):
        self.last_activity_time = time.time()

games = {}

def stop_game(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    game = games.get(chat_id)

    if not game or not game.is_active:
        context.bot.send_message(chat_id, "⚠️ Aktiv oyun yoxdur!")
        return

    chat_admins = context.bot.get_chat_administrators(chat_id)
    is_admin = any(admin.user.id == user_id for admin in chat_admins)

    if not is_admin:
        context.bot.send_message(chat_id, "⚠️ Bu əmri yalnız qrup adminləri işlədə bilər!")
        return

    game.stop_game()
    del games[chat_id]
    context.bot.send_message(chat_id, "🛑 Oyun dayandırıldı!")

def start_game(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    if update.effective_chat.type not in ['group', 'supergroup']:
        context.bot.send_message(chat_id, "⚠️ Bu bot yalnız qruplar üçün nəzərdə tutulub!")
        return

    if chat_id in games and games[chat_id].is_active:
        context.bot.send_message(chat_id, "⚠️ Hal-hazırda aktiv oyun var!")
        return

    if chat_id not in games:
        games[chat_id] = Game()

    game = games[chat_id]

    if game.host:
        context.bot.send_message(chat_id, "⚠️ Oyunda artıq aparıcı var!")
        return

    keyboard = [
        [
            InlineKeyboardButton("🎮 Oyun Başlat", callback_data='start_full_game'),
            InlineKeyboardButton("👑 Aparıcı Başlat", callback_data='start_host_game')
        ],
        [InlineKeyboardButton("🚫 Heçnə Etmə", callback_data='do_nothing')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(
        chat_id,
        f"🎮 Oyun başlamağa hazırdır. Başlamaq istəyirsiniz?",
        reply_markup=reply_markup
    )

def check_answer(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    game = games.get(chat_id)

    if not game or not game.host or not game.is_active or not update.message.text:
        return

    if game.host['id'] == update.effective_user.id:
        return

    if update.message.text.lower().strip() == game.current_word.lower().strip():
        try:
            correct_word = game.current_word  # Doğru sözü saxla
            update_scores(
                update.effective_user.id,
                update.effective_user.first_name,
                chat_id,
                update.effective_chat.title
            )

            db = get_db()  # db obyektini burada təyin edin

            # İstifadəçinin doğru cavab sayını artırın
            db.user_groups.update_one(
                {'user_id': update.effective_user.id, 'group_id': chat_id},
                {'$inc': {'correct_answers': 1}},
                upsert=True
            )

            if game.mode == "full":
                game.set_host(update.effective_user.id, update.effective_user.username)
                db.user_groups.update_one(
                    {'user_id': update.effective_user.id, 'group_id': chat_id},
                    {'$inc': {'host_count': 1}},
                    upsert=True
                )
            else:
                old_word = game.current_word
                while game.current_word == old_word:
                    game.current_word = random.choice(words)

            keyboard = [
                [
                    InlineKeyboardButton("🎲 Sözə bax", callback_data='show_word'),
                    InlineKeyboardButton("🔄 Sözü dəyiş", callback_data='change_word')
                ],
                [InlineKeyboardButton("❌ Aparıcılıqdan çıx", callback_data='quit_host')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            message = (
                f"🎯 Təbriklər! [{update.effective_user.first_name}](tg://user?id={update.effective_user.id}) düzgün cavab verdi!\n"
                f"{'👑 Aparıcı dəyişmədi, çünki oyun aparıcı rejimindədir!' if game.mode == 'host' else f'👑 İndi [{update.effective_user.first_name}](tg://user?id={update.effective_user.id}) yeni aparıcıdır!'}"
            )

            context.bot.send_message(chat_id, message, reply_markup=reply_markup, parse_mode='Markdown')

        except Exception as error:
            logging.error('Xal yeniləmə xətası: %s', error)
            context.bot.send_message(chat_id, "⚠️ Xəta baş verdi. Zəhmət olmasa yenidən cəhd edin.")

def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    game = games.get(chat_id)

    if query.data == 'start_full_game':
        if game.host:
            context.bot.answer_callback_query(
                query.id,
                text="⚠️ Oyunda artıq aparıcı var!",
                show_alert=True
            )
            return

        game.set_host(user_id, query.from_user.username, mode="full")
        game.start_game()

        keyboard = [
            [
                InlineKeyboardButton("🎲 Sözə bax", callback_data='show_word'),
                InlineKeyboardButton("🔄 Sözü dəyiş", callback_data='change_word')
            ],
            [InlineKeyboardButton("❌ Aparıcılıqdan çıx", callback_data='quit_host')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.edit_message_text(
            f"🎮 [{update.effective_user.first_name}](tg://user?id={update.effective_user.id}) tam oyunu başlatdı. Oyun başladı!",
            chat_id=chat_id,
            parse_mode='Markdown',
            message_id=query.message.message_id,
            reply_markup=reply_markup
        )

    elif query.data == 'start_host_game':
        if game.host:
            context.bot.answer_callback_query(
                query.id,
                text="⚠️ Oyunda artıq aparıcı var!",
                show_alert=True
            )
            return

        game.set_host(user_id, query.from_user.username, mode="host")
        game.start_game()

        keyboard = [
            [
                InlineKeyboardButton("🎲 Sözə bax", callback_data='show_word'),
                InlineKeyboardButton("🔄 Sözü dəyiş", callback_data='change_word')
            ],
            [InlineKeyboardButton("❌ Aparıcılıqdan çıx", callback_data='quit_host')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.edit_message_text(
            f"👑 @{query.from_user.username} aparıcı rejimini başlatdı!",
            chat_id=chat_id,
            message_id=query.message.message_id,
            reply_markup=reply_markup
        )

    elif query.data == 'become_host':
        if not game.host:
            game.set_host(user_id, query.from_user.username)
            keyboard = [
                [
                    InlineKeyboardButton("🎲 Sözə bax", callback_data='show_word'),
                    InlineKeyboardButton("🔄 Sözü dəyiş", callback_data='change_word')
                ],
                [InlineKeyboardButton("❌ Aparıcılıqdan çıx", callback_data='quit_host')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            context.bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)

            mode_text = "aparıcı rejimində" if game.mode == "host" else "tam oyun rejimində"
            context.bot.send_message(
                chat_id,
                f"🎮 @{query.from_user.username} yeni aparıcı oldu! ({mode_text})",
                reply_markup=reply_markup
            )

        else:
            context.bot.answer_callback_query(
                query.id,
                text="⚠️ Artıq aparıcı var!",
                show_alert=True
            )

    elif query.data == 'quit_host':
        if game.host and game.host['id'] == user_id:
            game.remove_host()

            context.bot.delete_message(
                chat_id,
                message_id=query.message.message_id
            )

            mode_text = "aparıcı rejimində" if game.mode == "host" else "tam oyun rejimində"
            context.bot.send_message(
                chat_id,
                f"👋 @{query.from_user.username} aparıcılıqdan çıxdı! ({mode_text})\n\n"
                f"🎮 Yeni aparıcı olmaq üçün aşağıdakı düyməyə basın:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👑 Aparıcı olmaq istəyirəm", callback_data='become_host')]
                ])
            )
        else:
            context.bot.answer_callback_query(
                query.id,
                text="⚠️ Siz aparıcı deyilsiniz!",
                show_alert=True
            )

    elif query.data == 'show_word':
        if game.host and game.host['id'] == user_id:
            context.bot.answer_callback_query(
                query.id,
                text=f"🎯 Sizin sözünüz: {game.current_word}",
                show_alert=True
            )
        else:
            context.bot.answer_callback_query(
                query.id,
                text="⚠️ Siz aparıcı deyilsiniz!",
                show_alert=True
            )

    elif query.data == 'change_word':
        if game.host and game.host['id'] == user_id:
            old_word = game.current_word
            while game.current_word == old_word:
                game.current_word = random.choice(words)
            context.bot.answer_callback_query(
                query.id,
                text=f"🎲 Yeni sözünüz: {game.current_word}",
                show_alert=True
            )
        else:
            context.bot.answer_callback_query(
                query.id,
                text="⚠️ Siz aparıcı deyilsiniz!",
                show_alert=True
            )

    elif query.data == 'do_nothing':
        context.bot.answer_callback_query(
            query.id,
            text="⚠️ Hələlik heç bir şey edilmədi.",
            show_alert=True
        )
