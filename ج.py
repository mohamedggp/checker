import telebot
import requests
import time
import os
from telebot import types

# --- الإعدادات ---
API_TOKEN = '6582886742:AAGkoCRK1NCgvoMVC6rvJNHs0cOtrp96Bwg'
STRIPE_SK = 'pk_test_51SoVeCPQHXbJQNKNB343k4Rvhaql0Ozb6kTmPoUEJyiE8fPePSioGX138xsH8p5TOfjx9FaKl6xgBe3elOgm41Na00Qbn6A1Y4'

bot = telebot.TeleBot(API_TOKEN)

# متغيرات للتحكم في الحالة
stop_status = {}

def check_gate_live(cc, mm, yy, cvv):
    auth_header = {"Authorization": f"Bearer {STRIPE_SK}"}
    try:
        token_url = "api.stripe.com"
        card_data = {
            'card[number]': cc,
            'card[exp_month]': mm,
            'card[exp_year]': "20" + yy if len(yy) == 2 else yy,
            'card[cvc]': cvv,
        }
        token_res = requests.post(token_url, headers=auth_header, data=card_data, timeout=10).json()
        
        if 'error' in token_res:
            return f"DEAD ❌ ({token_res['error']['message']})"
            
        token_id = token_res['id']
        charge_url = "api.stripe.com"
        charge_data = {'amount': 50, 'currency': 'usd', 'source': token_id}
        
        charge_res = requests.post(charge_url, headers=auth_header, data=charge_data, timeout=10).json()

        if 'id' in charge_res:
            return "LIVE ✅ (Charged)"
        elif 'error' in charge_res:
            if charge_res['error'].get('decline_code') == 'insufficient_funds':
                return "LIVE ✅ (Low Funds)"
            return f"DECLINED ❌ ({charge_res['error']['message']})"
        return "UNKNOWN ⚠️"
    except:
        return "ERROR ⚠️"

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    chat_id = message.chat.id
    if not message.document.file_name.endswith('.txt'):
        bot.reply_to(message, "❌ أرسل ملف .txt فقط!")
        return

    # إنشاء زر الإيقاف
    stop_status[chat_id] = False
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🛑 إيقاف الفحص", callback_data="stop_scan"))

    status_msg = bot.reply_to(message, "📥 جاري البدء...", reply_markup=markup)

    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    input_file = f"in_{chat_id}.txt"
    
    with open(input_file, 'wb') as f: f.write(downloaded_file)
    with open(input_file, 'r') as f: lines = f.read().splitlines()

    total = len(lines)
    hits = 0
    
    for index, line in enumerate(lines, 1):
        # التحقق إذا ضغط المستخدم على إيقاف
        if stop_status.get(chat_id):
            bot.edit_message_text("⚠️ تم إيقاف الفحص بواسطة المستخدم.", chat_id, status_msg.message_id)
            break

        try:
            line = line.strip()
            if "|" not in line: continue
            
            cc, mm, yy, cvv = [p.strip() for p in line.split('|')[:4]]
            result = check_gate_live(cc, mm, yy, cvv)
            
            if "LIVE" in result:
                hits += 1
                bot.send_message(chat_id, f"🔥 **LIVE HIT:** `{line}`\nResult: {result}", parse_mode="Markdown")
            
            # تحديث العداد الفوري
            bot.edit_message_text(
                f"📊 **عداد الفحص الفوري:**\n\n"
                f"✅ تم فحص: `{index}/{total}`\n"
                f"🎯 الناجحة: `{hits}`\n"
                f"❌ المرفوضة: `{index - hits}`", 
                chat_id, status_msg.message_id, reply_markup=markup, parse_mode="Markdown"
            )
            time.sleep(2) 
        except: continue

    bot.send_message(chat_id, "🏁 **انتهت العملية.**")
    if os.path.exists(input_file): os.remove(input_file)

@bot.callback_query_handler(func=lambda call: call.data == "stop_scan")
def callback_stop(call):
    stop_status[call.message.chat.id] = True
    bot.answer_callback_query(call.id, "جاري الإيقاف...")

print("🚀 البوت يعمل مع أزرار التحكم والعداد الفوري...")
bot.infinity_polling()
