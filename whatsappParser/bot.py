import telebot
from telebot import types
from config import TOKEN
from whatsapp_parser import *
from selenium.webdriver import Edge
from Youtube_parser import main
import threading
import ctypes

# TODO: удаление кнопок

class InterruptableThread(threading.Thread):
    def __init__(self, target, args=()):
        threading.Thread.__init__(self, target=target, args=args)
        self.target = target
        self.args = args


    # def run(self):
    #     # target function of the thread class
    #     try:
    #         self.target(*args)
    #     finally:
    #         print('ended')


    def get_id(self):
        if hasattr(self, '_thread_id'):
            return self._thread_id
        for id, thread in threading._active.items():
            if thread is self:
                return id


    def interrupt(self):
        thread_id = self.get_id()
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id,
                                                         ctypes.py_object(SystemExit))
        if res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
            print('Exception raise failure')


class User:
    def __init__(self, id, chat_id, last_message=None, parser=None):
        self.id = id
        self.chat_id = chat_id
        self.last_message = last_message
        self.parser = parser
        self.__current_operation = None
        self.__operation_started = threading.Event()
        self.operation_cancelled = False
        threading.Thread(target=self.__close_on_inaction).start()


    def start_operation(self, target, args=()):
        if not (self.__current_operation and self.__current_operation.is_alive()):
            self.__operation_started.set()
            self.__current_operation = InterruptableThread(target=target, args=args)
            self.__current_operation.start()


    def stop_operation(self):
        if self.__current_operation and self.__current_operation.is_alive():
            self.__current_operation.interrupt()


    def __close_on_inaction(self):
        # если парсер длительное время бездействует, закрываем его
        while True:
            is_set = self.__operation_started.wait(180)
            if (not is_set and  # таймаут вышел
                self.parser and  # парсер запущен
                not (self.__current_operation and self.__current_operation.is_alive())):  # а работы не идёт
                self.parser.close()
                self.parser = None
                break
            self.__operation_started.clear()


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
                if call.data == self.START:
                    self.__send_parser_choosing_menu(new_user.chat_id)
                elif call.data == self.WHATSAPP and user.last_message == self.START:
                    # запускаем WhatsApp-парсер
                    next_menu.add(types.InlineKeyboardButton('Отмена',
                                                             callback_data=self.BACK))
                    self.__tgbot.send_message(user.chat_id,
                                              text='Ожидайте, требуется авторизация в WhatsApp...',
                                              reply_markup=next_menu)
                    user.start_operation(self.__start_whatsapp_parsing, (user, ))
                    user.last_message = self.WHATSAPP
                elif call.data == self.BACK:
                    if user.last_message == self.WHATSAPP:
                        # отменяем авторизацию
                        # self.__operation_cancelled = True
                        user.stop_operation()
                        self.__tgbot.send_message(user.chat_id, 'Отмена операции...')
                        user.last_message = self.START
                        # присылаем меню с выбором парсеров
                        self.__send_parser_choosing_menu(user.chat_id)
                elif call.data == self.YOUTUBE:
                    self.__tgbot.send_message(call.message.chat.id, 'Введите название видео')
                elif call.data == self.CONTACTS_ONE and user.last_message == self.WHATSAPP:
                    if user.parser:
                        next_menu.add(types.InlineKeyboardButton('Назад',
                                                                 callback_data=self.BACK))
                        self.__tgbot.send_message(call.message.chat.id,
                                                  text='Введите название чата, телефоны ' +
                                                       'из которого вы хотите получить, ' +
                                                       'или вернитесь к меню выбора действий:',
                                                  reply_markup=next_menu)
                        user.last_message = self.CONTACTS_ONE
                    else:
                        # парсер был выключен из-за длительного бездействия
                        self.__restart(user)
                elif call.data == self.CONTACTS_ALL:
                    get_all_name_and_number(call)
                elif call.data == self.MESSAGES_ONE:
                    pass
                elif call.data == self.MESSAGES_ALL:
                    get_all_messages(call)

        self.__tgbot.polling(none_stop=True)


    def __restart(self, user):
        next_menu.add(types.InlineKeyboardButton('Старт',
                                                 callback_data=self.START))
        self.__tgbot.send_message(user.chat_id,
                                  text='Время ожидания истекло! Нажмите "Старт", чтобы начать снова:',
                                  reply_markup=next_menu)
        user.last_message = self.START


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
        try:
            user.parser = WhatsAppParser(hidden=False)
            t1 = threading.Thread(target=self.__authorize_user, args=(user, ))
            t1.start()
            user.parser.open()
            t1.join()
        except:
            # пользователь прервал операцию
            user.parser.close()


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
            # if user.operation_cancelled:
            #     # пользователь прервал операцию
            #     user.parser.close()
            #     break
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
