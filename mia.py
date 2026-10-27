import json
import os
import time
import logging
from collections import defaultdict

import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv

load_dotenv()

# ════════════════════════════════════════════════════════════
#  КОНФИГ
# ════════════════════════════════════════════════════════════
_token1 = os.getenv("8714175174:", "").strip()
_token2 = os.getenv("AAHOkyAVBWdRTEXC1L4tY_hO6vUobWfzeXY", "").strip()
BOT_TOKEN = f"{_token1}:{_token2}" if _token1 and _token2 else ""

if not BOT_TOKEN:
    raise SystemExit("❌ Задай BOT_TOKEN_PART1 и BOT_TOKEN_PART2 в .env")

DISCUSSION_CHAT_ID = os.getenv("DISCUSSION_CHAT_ID", "").strip() or None
DELAY_SECONDS = float(os.getenv("DELAY_SECONDS", "0") or "0")

REPLY_TEXT = (
    "МИЯ ПРИВЕТ ЕСЛИ ЧИТАЕШЬ ЭТО С ФАНСТАТА "
    "БЛЯДСКИЙ ТРЕТИЙ РАЗ😁😁😁😁😁😁😁😁😁😁"
)

EMOJIS = ["😁", "🔥", "❤️", "👍", "💯"]
VOTES_FILE = "votes.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("mia_bot")

# ════════════════════════════════════════════════════════════
#  ХРАНИЛИЩЕ ГОЛОСОВ
#  votes[msg_id][emoji] = set(user_id)
# ════════════════════════════════════════════════════════════
votes: dict[int, dict[str, set[int]]] = defaultdict(lambda: defaultdict(set))


def load_votes() -> None:
    if not os.path.exists(VOTES_FILE):
        return
    try:
        with open(VOTES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        log.warning("Не смог прочитать %s: %s", VOTES_FILE, e)
        return
    votes.clear()
    for k, em in data.items():
        votes[int(k)] = defaultdict(set, {e: set(u) for e, u in em.items()})
    log.info("Загружено %d постов с голосами", len(votes))


def save_votes() -> None:
    try:
        clean = {
            str(k): {e: list(u) for e, u in v.items() if u}
            for k, v in votes.items()
            if any(v.values())
        }
        tmp = VOTES_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(clean, f, ensure_ascii=False)
        os.replace(tmp, VOTES_FILE)
    except Exception as e:
        log.exception("Не смог сохранить голоса: %s", e)


# ════════════════════════════════════════════════════════════
#  КЛАВИАТУРА РЕАКЦИЙ
# ════════════════════════════════════════════════════════════
def build_kb(msg_id: int) -> types.InlineKeyboardMarkup:
    v = votes[msg_id]
    kb = types.InlineKeyboardMarkup()
    row = []
    for i, e in enumerate(EMOJIS):
        cnt = len(v[e])
        label = f"{e} {cnt}" if cnt else e
        row.append(types.InlineKeyboardButton(
            text=label,
            callback_data=f"react:{msg_id}:{i}",
        ))
    kb.row(*row)
    return kb


# ════════════════════════════════════════════════════════════
#  БОТ
# ════════════════════════════════════════════════════════════
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)


@bot.message_handler(
    content_types=["text", "photo", "video", "document", "animation",
                   "audio", "voice", "sticker", "poll", "media_group"],
    func=lambda m: getattr(m, "is_automatic_forward", False) is True,
)
def on_channel_post(message: types.Message) -> None:
    """Ловит новый пост канала, авто-форварднутый в обсуждение."""
    if DISCUSSION_CHAT_ID and str(message.chat.id) != DISCUSSION_CHAT_ID:
        return

    if DELAY_SECONDS > 0:
        time.sleep(DELAY_SECONDS)

    try:
        bot.reply_to(
            message,
            REPLY_TEXT,
            reply_markup=build_kb(message.message_id),
        )
        log.info("Ответил на пост %s в чате %s",
                 message.message_id, message.chat.id)
    except ApiTelegramException as e:
        log.exception("Telegram API не дал ответить: %s", e)
    except Exception as e:
        log.exception("Не смог ответить на пост: %s", e)


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("react:"))
def handle_reaction(cb: types.CallbackQuery) -> None:
    """Обработка клика по кнопке-реакции."""
    try:
        _, msg_id_str, idx_str = cb.data.split(":", 2)
        msg_id = int(msg_id_str)
        idx = int(idx_str)
        emoji = EMOJIS[idx]
    except (ValueError, IndexError):
        bot.answer_callback_query(cb.id, text="Ошибка данных")
        return

    uid = cb.from_user.id
    v = votes[msg_id]

    # toggle: одна реакция на пользователя
    if uid in v[emoji]:
        v[emoji].discard(uid)
        bot.answer_callback_query(cb.id, text=f"Убрал {emoji}")
    else:
        for e in EMOJIS:
            v[e].discard(uid)
        v[emoji].add(uid)
        bot.answer_callback_query(cb.id, text=f"Ты поставил {emoji}")

    save_votes()

    # обновляем счётчики на кнопках
    try:
        bot.edit_message_reply_markup(
            chat_id=cb.message.chat.id,
            message_id=cb.message.message_id,
            reply_markup=build_kb(msg_id),
        )
    except ApiTelegramException as e:
        # сообщение удалили, клавиатура не изменилась, «message is not modified» и т.п.
        log.warning("Не смог обновить клавиатуру для %s: %s", msg_id, e)


# ════════════════════════════════════════════════════════════
#  СТАРТ
# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    load_votes()
    me = bot.get_me()
    log.info("Бот @%s запущен (id=%s)", me.username, me.id)
    bot.infinity_polling(
        skip_pending=True,
        allowed_updates=["message", "callback_query"],
    )