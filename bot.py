from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, CallbackContext, MessageHandler
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, timedelta
import requests

# Инициализация Google Sheets клиента
creds = Credentials.from_service_account_file('credentials.json', scopes=['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
client = gspread.authorize(creds)

# Определение состояний для разговора
NAME, CITY, PHONE, TRANSPORT = range(4)

# Инициализация Google Sheets таблицы
sheet = client.open_by_key('1ncPCCTtGmrYND4IMqh4OQBsnXcrKqSwhZpcxo5MYkeE')
worksheet = sheet.get_worksheet(0)

# Определение функций обработки команд

def start(update: Update, context: CallbackContext) -> int:
    global start_counter
    start_counter += 1

    # Обновляем счетчик в Google Таблицах
    update_start_counter(start_counter)
    
    update.message.reply_text("Привет! Оставь информацию о себе и наш менеджер свяжется с тобой\n (Заполняй форму только если тебе есть 18 лет)\n\n"
                              "Введите ваше имя:")
    
    start_param = context.args[0] if context.args else None
    if start_param:
        print(f"Пользователь {update.message.from_user.id} перешел по ссылке с параметром start: {start_param}")
        context.user_data['start_param'] = start_param
    return NAME

def update_start_counter(counter):
    try:
        worksheet.update('I4', [[counter]])  # Обновляем значение в ячейке I7
        print(f"Счетчик обновлен: {counter}")
    except Exception as e:
        print(f"An error occurred while updating the start counter: {e}")

def save_name(update: Update, context: CallbackContext) -> int:
    context.user_data['name'] = update.message.text
    update.message.reply_text("Отлично! Теперь введите ваш город:")
    return CITY

def save_city(update: Update, context: CallbackContext) -> int:
    context.user_data['city'] = update.message.text
    update.message.reply_text("Предпоследний шаг. Твой никнейм в телеграме или номер телефона на который создан телеграм аккаунт:")
    return TRANSPORT

def save_transport(update: Update, context: CallbackContext) -> int:
    context.user_data['transport'] = update.message.text
    update.message.reply_text("И последний вопрос. Есть ли у вас транспортное средство? Если да, то какое?")
    return PHONE

new = f"New lead"
def send_to_google_sheets(user_id, username, name, city, transport, phone, start_param, new, full_name):
    try:
        row_to_insert = [user_id, username, name, city, transport, phone, start_param,  datetime.now().strftime("%Y-%m-%d %H:%M:%S"), new, full_name]
        worksheet.append_row(row_to_insert)
        print((datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"))
    except Exception as e:
        print(f"An error occurred while sending data to Google Sheets: {e}")

def save_phone(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    first_name = update.message.from_user.first_name or ""  # Если first_name None, присваиваем пустую строку
    last_name = update.message.from_user.last_name or ""    # Если last_name None, присваиваем пустую строку
    full_name = f"{first_name} {last_name}"
    name = context.user_data['name']
    city = context.user_data.get('city', 'не указан')
    phone = update.message.text
    new = f"New lead"
    # Получаем параметр start из контекста
    start_param = context.user_data.get('start_param', 'не указан')
    transport = context.user_data.get('transport', 'не указано')
    
    df = pd.DataFrame({
        'User ID': [user_id],
        'Username': [username],
        'Name': [name],
        'City': [city],
        'Phone': [phone]
    })

    try:
        existing_df = pd.read_excel('client_data_new.xlsx')
        updated_df = pd.concat([existing_df, df], ignore_index=True)
        updated_df.to_excel('client_data_new.xlsx', index=False)
    except FileNotFoundError:
        df.to_excel('client_data_new.xlsx', index=False)


    # postback 
    url = "https://mextraff.pro/cacec1a/postback"
    subid = start_param.split('_')[0]
    data = {
        'subid': subid,
        'status': 'lead',
        'from': 'TGBot'
    }

    try:
        response = requests.post(url, data=data)
        response.raise_for_status()  # Проверяем успешность запроса
        print("Lead postback sent successfully!")
    except requests.exceptions.HTTPError as errh:
        print(f"HTTP Error: {errh}")
    except requests.exceptions.ConnectionError as errc:
        print(f"Error Connecting: {errc}")
    except requests.exceptions.Timeout as errt:
        print(f"Timeout Error: {errt}")
    except requests.exceptions.RequestException as err:
        print(f"Request Exception: {err}")

    send_to_google_sheets(user_id, username, name, city, transport, phone, start_param, new, full_name)
    
    # update.message.reply_text(f"Спасибо, {name}! В ближайшее время мы с тобой свяжемся \U0001F44D")

    keyboard = [[InlineKeyboardButton(f'Написать нам', url=f'https://t.me/krisshrr')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Спасибо, мы получили все необходимое и в скором времени свяжемся с вами. Также, вы можете связаться прямо сейчас с нашим менеджером и перейти к следующему этапу собеседования. ', reply_markup=reply_markup)

    admin_id = 6699477319  # Замените на айди админа
    admin_message = f"Пользователь {name} (ID: {user_id} | @{username}) с города {city} ввел номер телефона: {phone}"
    context.bot.send_message(chat_id=admin_id, text=admin_message)

    return ConversationHandler.END

# ... остальные функции остаются без изменений ...

# Инициализация бота
def main():
    TOKEN = '6312484015:AAHUysdpMvGzL9JRYJYIanF0perFxVxsohI'  # Замените на ваш токен
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        NAME: [MessageHandler(None, save_name)],
        CITY: [MessageHandler(None, save_city)],
        TRANSPORT: [MessageHandler(None, save_transport)],
        PHONE: [MessageHandler(None, save_phone)]
    },
    fallbacks=[]
)

    dp.add_handler(conv_handler)
    dp.add_handler(conv_handler)
    global start_counter
    start_counter_cell = worksheet.acell('I4').value
    start_counter = int(start_counter_cell)
    
    # Запуск обновления счетчика
    update_start_counter(start_counter + 1)
    print('Бот запущен. Ожидание сообщений...')
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
