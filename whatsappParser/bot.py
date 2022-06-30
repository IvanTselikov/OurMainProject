import telebot
from telebot import types
from config import TOKEN
from whatsapp_parser import *
from selenium.webdriver import Edge
from Youtube_parser import main
import threading


class User:
    def __init__(self, id, chat_id, last_message=None, parser=None):
        self.id = id
        self.chat_id = chat_id
        self.last_message = last_message
        self.parser = parser
        self.current_operation = None
        self.operation_cancelled = False


class Bot:
    # идентификаторы кнопок
    START = 'start'
    WHATSAPP = 'WhatsApp'
    YOUTUBE = 'YouTube'
    CONTACTS_ONE = 'GetContactsFromOne'
    CONTACTS_ALL = 'GetContactsFromAll'
    MESSAGES_ONE = 'GetMessagesFromOne'
    MESSAGES_ALL = 'GetMessagesFromAll'
    BACK = 'Back'


    def __init__(self, token):
        self.__tgbot = telebot.TeleBot(token)
        self.__user_table = []
        print('Бот запущен')

        @self.__tgbot.message_handler(commands=['start'])
        def start(message):
            # заносим пользователя в список, если он ещё не был в него внесён
            if not self.__find_user(message.from_user.id):
                new_user = User(message.from_user.id, message.chat.id, self.START)
                self.__user_table.append(new_user)
                print(f'Пользователь {new_user.id} начал использовать парсер.')
                # предлагаем выбрать парсер
                self.__send_parser_choosing_menu(new_user.chat_id)


        @self.__tgbot.callback_query_handler(func=lambda call: True)
        def buttons_handler(call):
            self.__tgbot.answer_callback_query(call.id)
            user = self.__find_user(call.from_user.id)
            if user:
                next_menu = types.InlineKeyboardMarkup()
                if call.data == self.WHATSAPP and user.last_message == self.START:
                    # запускаем WhatsApp-парсер
                    next_menu.add(types.InlineKeyboardButton('Отмена',
                                                             callback_data=self.BACK))
                    self.__tgbot.send_message(user.chat_id,
                                              text='Ожидайте, требуется авторизация в WhatsApp...',
                                              reply_markup=next_menu)
                    if not (user.current_operation and user.current_operation.is_alive()):
                        user.current_operation = threading.Thread(target=self.__start_whatsapp_parsing, args=(user, ))
                        user.current_operation.start()
                    user.last_message = self.WHATSAPP
                elif call.data == self.BACK:
                    if user.last_message == self.WHATSAPP:
                        # отменяем авторизацию
                        self.__operation_cancelled = True
                        self.__tgbot.send_message(user.chat_id, 'Отмена операции...')
                        user.last_message = self.START
                        # присылаем меню с выбором парсеров
                        self.__send_parser_choosing_menu(user.chat_id)
                elif call.data == self.YOUTUBE:
                    self.__tgbot.send_message(call.message.chat.id, 'Введите название видео')
                elif call.data == self.CONTACTS_ONE:
                    self.__tgbot.send_message(call.message.chat.id, "Введите название чата")
                elif call.data == self.CONTACTS_ALL:
                    get_all_name_and_number(call)
                elif call.data == self.MESSAGES_ONE:
                    pass
                elif call.data == self.MESSAGES_ALL:
                    get_all_messages(call)

        self.__tgbot.polling(none_stop=True)


    def __send_parser_choosing_menu(self, chat_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Парсинг WhatsApp',
                                              callback_data=self.WHATSAPP))
        markup.add(types.InlineKeyboardButton('Парсинг YouTube',
                                              callback_data=self.YOUTUBE))
        self.__tgbot.send_message(chat_id,
                                  text='Выберите действие:',
                                  reply_markup=markup)


    def __send_whatsapp_options_menu(self, chat_id):
        markup = types.InlineKeyboardMarkup()

        markup.add(types.InlineKeyboardButton('Получить список телефонов из чата',
                                                    callback_data=self.CONTACTS_ONE))
        markup.add(types.InlineKeyboardButton('Получить список телефонов из всех чатов',
                                                    callback_data=self.CONTACTS_ALL))
        markup.add(types.InlineKeyboardButton('Получить сообщения из чата',
                                                    callback_data=self.MESSAGES_ONE))
        markup.add(types.InlineKeyboardButton('Получить сообщения из всех чатов',
                                                    callback_data=self.MESSAGES_ALL))
        markup.add(types.InlineKeyboardButton('Назад',
                                                    callback_data=self.BACK))
        self.__tgbot.send_message(chat_id,
                                  text='Что вы хотите сделать?',
                                  reply_markup=markup)


    def __start_whatsapp_parsing(self, user):
        user.parser = WhatsAppParser(hidden=False)
        threading.Thread(target=self.__authorize_user, args=(user, )).start()
        user.parser.open()


    def __authorize_user(self, user):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Назад',
                                              callback_data=self.BACK))
        try_num, limit = 0, 10
        while True:
            # ждём появления или изменения скриншота с qr-кодом
            is_set = user.parser.screenshot_changed.wait(180)
            if not is_set:
                # время ожидания истекло
                break
            user.parser.screenshot_changed.clear()
            if user.operation_cancelled:
                # пользователь прервал операцию
                user.parser.close()
                break
            if user.parser.screenshot:
                # qr-код изменился
                self.__tgbot.send_photo(user.chat_id,
                                        photo=user.parser.screenshot,
                                        caption='Пожалуйста, проследуйте инструкции на скриншоте.\n' +
                                        'Боту необходим временный доступ к вашим чатам.\n' +
                                        'QR-код актуален не более одной минуты. При его изменении вам будет ' +
                                        'отправлена его обновлённая версия.',
                                        reply_markup=markup)
                try_num += 1
                if try_num >= limit:
                    # если пользователь забросил бота, нужно перестать выполнять эту операцию
                    break
            else:
                # авторизация завершена
                self.__send_whatsapp_options_menu(user.chat_id)
                break


    def __find_user(self, user_id):
        return next((user for user in self.__user_table if user_id == user.id), None)


Bot(TOKEN)
