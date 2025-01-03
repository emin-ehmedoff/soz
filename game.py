from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
import random
import logging
from database.scores import update_scores, get_top_users, get_top_groups, get_group_top_users
from words import words
from database.models import get_db
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
        # Only set mode if provided, otherwise keep existing mode
        if mode is not None:
            self.mode = mode
            self.last_activity_time = time.time()  # Oyun başladığında aktivlik vaxtını yenilə

    def remove_host(self):
        self.host = None
        self.current_word = None
        self.last_activity_time = time.time()  # Oyun başladığında aktivlik vaxtını yenilə
        # Don't reset mode when host leaves
        # self.mode = None  # This line is removed

    def start_game(self):
        self.is_active = True
        self.last_activity_time = time.time()  # Oyun başladığında aktivlik vaxtını yenilə

    def stop_game(self):
        self.is_active = False
        self.remove_host()
        self.mode = None  # Only reset mode when game stops completely

def update_last_activity_time(self):
        self.last_activity_time = time.time()  # Bot hər mesaj yazanda sonuncu aktivlik vaxtını yenilə

# Oyun müddətini təqib edərək, 5 dəqiqə aktivlik olmasa oyunu dayandırır
def check_inactive_games(context):
    current_time = time.time()

    for chat_id, game in list(games.items()):
        if game.is_active:
            # Əgər sonuncu aktivlik vaxtı 5 dəqiqədən artıqdırsa
            if current_time - game.last_activity_time > 15:  # 15 saniye (15 saniyə)
                game.stop_game()
                del games[chat_id]
                context.bot.send_message(chat_id, "🛑 Oyun bitdi. Aktivlik yoxdur.")
                break

# Botun göndərdiyi mesajları izləyirik
def bot_send_message(update, context):
    chat_id = update.effective_chat.id

    if chat_id in games:
        game = games[chat_id]
        if game.is_active:
            game.update_last_activity_time()  # Botun göndərdiyi hər mesajda aktivlik vaxtını yeniləyir






games = {}


# Stop əmri handleri
def stop_game(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    game = games.get(chat_id)

    # Aktiv oyun yoxdursa, xəbərdarlıq mesajı
    if not game or not game.is_active:
        context.bot.send_message(chat_id, "⚠️ Aktiv oyun yoxdur!")
        return

    # Qrup adminlərini alırıq
    chat_admins = context.bot.get_chat_administrators(chat_id)

    # İstifadəçinin admin olub olmadığını yoxlayırıq
    is_admin = any(admin.user.id == user_id for admin in chat_admins)

    if not is_admin:
        context.bot.send_message(chat_id, "⚠️ Bu əmri yalnız qrup adminləri işlədə bilər!")
        return

    # Adminsə, oyun dayandırılır
    game.stop_game()
    del games[chat_id]  # Oyun dayandırıldıqdan sonra, `games` sözlüyündən bu oyunu silirik
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

            # Əgər tam rejimdirsə, aparıcı dəyişdirilir
            if game.mode == "full":
                game.set_host(update.effective_user.id, update.effective_user.username)
            else:
                # Yalnız yeni söz seçilir, əgər aparıcı dəyişmirsə
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

            # Təbrik mesajı
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
            # Keep existing game mode when new host joins
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
            game.remove_host()  # This no longer resets the game mode

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