from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, CallbackContext, Filters, CallbackQueryHandler
import gspread
from google.oauth2.service_account import Credentials
import requests
from datetime import datetime

# Инициализация Google Sheets клиента
creds = Credentials.from_service_account_file('credentials.json', scopes=['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
client = gspread.authorize(creds)

# Определение состояний для разговора
CITY, TRANSPORT, PHONE, DELIVERY_CONFIRMATION = range(4)

# Инициализация Google Sheets таблицы
sheet = client.open_by_key('1ncPCCTtGmrYND4IMqh4OQBsnXcrKqSwhZpcxo5MYkeE')
worksheet = sheet.get_worksheet(0)

# Определение функций обработки команд
def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Привет! Ответь, пожалуйста, на несколько вопросов.\nВ каком городе вы проживаете?")
    return CITY

def save_city(update: Update, context: CallbackContext) -> int:
    context.user_data['city'] = update.message.text
    update.message.reply_text("Есть ли у вас транспортное средство, если есть то какое?")
    return TRANSPORT

def save_transport(update: Update, context: CallbackContext) -> int:
    context.user_data['transport'] = update.message.text
    update.message.reply_text("Если ваш никнейм скрыт, для связи поделитесь своим контактным номером.")
    return PHONE

def save_phone(update: Update, context: CallbackContext) -> int:
    context.user_data['phone'] = update.message.text
    keyboard = [[InlineKeyboardButton("Да", callback_data='yes'),
                 InlineKeyboardButton("Нет", callback_data='no')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Готовы ли вы доставлять посылки особой важности за повышенную оплату ставке?", reply_markup=reply_markup)
    return DELIVERY_CONFIRMATION

def delivery_confirmation(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    context.user_data['delivery_confirmation'] = query.data
    query.edit_message_text(text=f"Ваш выбор: {'Да' if query.data == 'yes' else 'Нет'}")

    # Отправка данных и postback
    send_data_and_postback(context.user_data, update.effective_user, context)

    # Отправка сообщения пользователю с предложением связаться с менеджером
    keyboard = [[InlineKeyboardButton('Написать нам', url='https://t.me/krisshrr')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.effective_message.reply_text(
        'Спасибо, мы получили все необходимое и в скором времени свяжемся с вами. '
        'Также, вы можете связаться прямо сейчас с нашим менеджером и перейти к следующему этапу собеседования.',
        reply_markup=reply_markup
    )

    # Отправка уведомления администратору
    admin_id = 6699477319  # Замените на айди админа
    user_data = context.user_data
    admin_message = f"Пользователь {user_data.get('name', 'Неизвестный')} " \
                    f"(ID: {update.effective_user.id} | @{update.effective_user.username}) " \
                    f"с города {user_data.get('city', 'Не указан')} " \
                    f"ввел номер телефона: {user_data.get('phone', 'Не указан')}"
    context.bot.send_message(chat_id=admin_id, text=admin_message)

    return ConversationHandler.END


def send_data_and_postback(user_data, user, context):
    user_id = user.id
    username = user.username or "Не указан"
    name = user_data.get('name', 'Не указано')
    city = user_data.get('city', 'Не указано')
    transport = user_data.get('transport', 'Не указано')
    phone = user_data.get('phone', 'Не указано')
    delivery_confirmation = user_data.get('delivery_confirmation', 'Не указано')
    start_param = context.user_data.get('start_param', 'не указан')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_lead = "New lead"

    # Отправка данных в Google Sheets
    row_to_insert = [user_id, username, name, city, phone, transport, start_param, timestamp, new_lead]
    worksheet.append_row(row_to_insert)

    # Отправка postback запроса
    url = "https://mextraff.pro/cacec1a/postback"
    subid = start_param.split('_')[0] if start_param != 'не указан' else 'не указан'
    data = {
        'subid': subid,
        'status': 'lead',
        'from': 'TGBot'
    }
    try:
        requests.post(url, data=data)
    except requests.exceptions.RequestException as e:
        print(f"Error sending postback: {e}")


# Инициализация бота
def main():
    TOKEN = '6371529125:AAG-g0wLSRYldOSNgKDI-6MmWq-AXAfZ7dY'  # Замените на ваш токен
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CITY: [MessageHandler(Filters.text & ~Filters.command, save_city)],
            TRANSPORT: [MessageHandler(Filters.text & ~Filters.command, save_transport)],
            PHONE: [MessageHandler(Filters.text & ~Filters.command, save_phone)],
            DELIVERY_CONFIRMATION: [CallbackQueryHandler(delivery_confirmation)]
        },
        fallbacks=[]
    )

    dp.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
