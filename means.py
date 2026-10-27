import telebot

# ==================== НАСТРОЙКИ ====================
TOKEN_PART1 = "8714175174:"
TOKEN_PART2 = "AAHOkyAVBWdRTEXC1L4tY_hO6vUobWfzeXY"
BOT_TOKEN = TOKEN_PART1 + TOKEN_PART2
# ==================================================

bot = telebot.TeleBot(BOT_TOKEN)

COMMENT_TEXT = "МИЯ ПРИВЕТ ЕСЛИ ЧИТАЕШЬ ЭТО С ФАНСТАТА БЛЯДСКИЙ ТРЕТИЙ РАЗ😁😁😁😁😁😁😁😁😁😁"

@bot.message_handler(func=lambda msg: msg.chat.type in ['group', 'supergroup'])
def comment_on_post(message):
    # Проверяем, что это автоматическая пересылка из канала
    is_auto = getattr(message, 'is_automatic_forward', False)
    if not is_auto:
        # fallback: если нет атрибута, проверяем forward_from_chat
        if message.forward_from_chat and message.forward_from_chat.type == 'channel':
            is_auto = True

    if is_auto:
        try:
            bot.reply_to(message, COMMENT_TEXT)
        except Exception as e:
            print(f"Не удалось оставить комментарий: {e}")

if __name__ == "__main__":
    print("Бот-комментатор запущен...")
    bot.infinity_polling()