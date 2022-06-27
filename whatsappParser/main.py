from selenium.webdriver import Edge
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup as BS
from time import sleep
import datetime as dt
# from tqdm import tqdm
import re
import webbrowser


class MessageInfo:
    def __init__(self, date_time, sender, text):
        self.date_time = date_time
        self.sender = sender
        self.text = text


class Dialog:
    def __init__(self, name, web_el):
        self.name = name
        self.web_el = web_el


class WhatsAppParser:
    def __init__(self, driver):
        self.driver = driver
        self.dialogs = []


    def __enter__(self):
        # открываем WhatsApp в браузере
        self.driver.get('https://web.whatsapp.com')  # TODO: сделать браузер невидимым

        # сохраняем qr-коды
        self.save_qr_screenshots()

        # ожидаем, когда прогрузится страница с диалогами
        pane_side = wait(self.driver, 60).until(
            EC.presence_of_element_located((By.XPATH,
                                            '//*[@id="pane-side"]/div'))
        )
        # TODO: если вышел таймаут

        # sleep(3)  # TODO: дожидаться пока диалоги прогрузятся полностью

        # проверяем наличие надписи "Список диалогов пуст"
        no_chats_span = self.find_element_or_none(parent=self.driver, by=By.XPATH,
                                             value='//*[@id="pane-side"]/div/div/span')

        # TODO: timeoutException
        if not no_chats_span:
            # ждём, пока прогрузятся диалоги
            wait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH,
                                                '//*[@id="pane-side"]/div/div/div/div'))
            )
            dialogs_count = self.find_element_or_none(parent=self.driver,
                                                 by=By.XPATH,
                                                 value='//*[@id="pane-side"]/div/div/div')
            dialogs_count = int(dialogs_count.get_attribute('aria-rowcount'))
            pane_side.send_keys(Keys.DOWN)
            pane_side.send_keys(Keys.UP)
            last_dlg = None
            while len(self.dialogs) < dialogs_count:
                # подгружаем диалоги
                current_dlg = self.driver.switch_to.active_element
                if current_dlg == last_dlg:
                    break
                else:
                    last_dlg = current_dlg
                dialog_web_el = self.find_element_or_none(parent=current_dlg,
                                                          by=By.XPATH,
                                                          value='..')
                dialog_name = self.__verify_contact_name(dialog_web_el)
                self.dialogs.append(Dialog(dialog_name, current_dlg))
                pane_side.send_keys(Keys.DOWN)
        # TODO: parent=self.driver, by=By.XPATH по умолчанию
        self.searchbar = self.find_element_or_none(parent=self.driver,
                                                   by=By.XPATH,
                                                   value='//*[@id="side"]/div[1]/div/div/div[2]/div/div[2]')


    def __exit__(self, exc_type, exc_val, exc_tb):
        # выходим из аккаунта
        self.__log_out()
        # закрываем браузер
        self.driver.quit()


    def __log_out(self):
        # ищем и открываем меню
        menu_web_el = self.find_element_or_none(parent=self.driver,
                                           by=By.XPATH,
                                           value='//*[@id="side"]/header/div[2]/div/span/div[3]/div/span')
        menu_web_el.click()

        # ждём и кликаем по кнопке "Выход"
        quit_btn = wait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH,
                                                '//*[@id="side"]/header/div[2]/div/span/div[3]/span/div/ul/li[5]'))
        )
        quit_btn.click()

        # подтверждаем выход
        sure_quit = wait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH,
                                                '//*[@id="app"]/div/span[2]/div/div/div/div/div/div/div[3]/div/div[2]/div/div'))
        )
        sure_quit.click()


    def __verify_contact_name(self, dialog_web_el):
        dialog_name = self.find_element_or_none(parent=dialog_web_el,
                                                by=By.XPATH,
                                                value='.//div/div/div[2]/div[1]/div[1]/span').text
        if re.match(r'\+\d{1} \d{3} \d{3}-\d{2}-\d{2}', dialog_name):
            sleep(2)  # TODO: посмотреть что можно сделать с задержкой
            dialog_name = self.find_element_or_none(parent=dialog_web_el,
                                                by=By.XPATH,
                                                value='.//div/div/div[2]/div[1]/div[1]/span').text
        return dialog_name


    def get_contacts_from_dialog(self, name=None):
        if name:
            # ищем диалог по имени и парсим его
            found_dialogs = list(filter(lambda dlg: dlg.name == name, self.dialogs))
        else:
            # парсим все контакты
            found_dialogs = self.dialogs
        if found_dialogs:
            return list(map(self.get_name_and_number, found_dialogs))
        else:
            # диалог с указанным именем не найден, либо диалогов нет вообще
            return None


    def get_messages_from_dialog(self, name=None):
        if name:
            # ищем диалог по имени и парсим его
            found_dialogs = list(filter(lambda dlg: dlg.name == name, self.dialogs))
        else:
            # парсим все контакты
            found_dialogs = self.dialogs
        if found_dialogs:
            return list(map(self.get_messages, found_dialogs))
        else:
            # диалог с указанным именем не найден, либо диалогов нет вообще
            return None


    DAYS_OF_WEEK = ['ПОНЕДЕЛЬНИК', 'ВТОРНИК', 'СРЕДА', 'ЧЕТВЕРГ', 'ПЯТНИЦА', 'СУББОТА', 'ВОСКРЕСЕНЬЕ']
    def get_date_by_weekday(self, weekday):
        current_day = dt.datetime.today().isoweekday()
        delta = abs(current_day - (DAYS_OF_WEEK.index(weekday) + 1))
        return (dt.date.today() - dt.timedelta(days=delta)).date.strftime('%d.%m.%Y')


    def find_element_or_none(self, parent, by, value):
        try:
            return parent.find_element(by=by, value=value)
        except NoSuchElementException:
            return None


    def find_elements_or_none(self, parent, by, value):
        try:
            return parent.find_elements(by=by, value=value)
        except NoSuchElementException:
            return None


    def save_qr_screenshots(self):
        # ждём появления qr-кода
        # TODO: скроллить список диалогов вниз
        # TODO: попытаться сократить пути
        wait(self.driver, 30).until(
            EC.presence_of_element_located((By.XPATH,
                                            '//*[@id="app"]/div/div/div[2]/div[1]/div/div[2]/div/canvas'))
        )
        token = self.find_element_or_none(parent=self.driver,
                                     by=By.XPATH,
                                     value='//*[@id="app"]/div/div/div[2]/div[1]/div/div[2]/div').get_attribute('data-ref')
        print('Скриншот сделан')
        screenshot = self.driver.save_screenshot('my_screenshot.png')
        while True:
            # TODO: поставить таймаут
            sleep(10)
            button = self.find_element_or_none(parent=self.driver,
                                          by=By.XPATH,
                                          value='//*[@id="app"]/div/div/div[2]/div[1]/div/div[2]/div/span/button')
            if button:
                # перегенерируем qr-код
                sleep(1)
                button.click()
                sleep(1)
            new_token_web_el = self.find_element_or_none(parent=self.driver,
                                             by=By.XPATH,
                                             value='//*[@id="app"]/div/div/div[2]/div[1]/div/div[2]/div')
            if not new_token_web_el:
                # токен пропал - страница поменялась
                break
            new_token = new_token_web_el.get_attribute('data-ref')
            if new_token != token:
                token = new_token
                screenshot = self.driver.save_screenshot('my_screenshot.png')
                print('QR изменился')


    def get_name_and_number(self, dialog):
        self.searchbar.send_keys(dialog.name)
        dlg = dialog.web_el
        # заходим в диалог
        dlg.click()
        # ищем информацию о номере телефона
        # открываем информацию о профиле собеседника
        profile = self.find_element_or_none(parent=self.driver,
                                       by=By.XPATH,
                                       value='//*[@id="main"]/header/div[2]/div/div/span')
        profile.click()
        sleep(3)  # TODO: дожидаться прогрузки
        name_web_el = self.find_element_or_none(parent=self.driver,
                                    by=By.XPATH,
                                    value='//*[@id="app"]/div/div/div[2]/div[3]/span/div/span/div/div/section/div[1]/div[2]/h2/span')
        phones = []
        if name_web_el:
            # парсим диалог
            name = name_web_el
            phone = self.find_element_or_none(parent=self.driver,
                                     by=By.XPATH,
                                     value='//*[@id="app"]/div/div/div[2]/div[3]/span/div/span/div/div/section/div[1]/div[2]/div/span/span').text
            phones.append(phone)
        else:
            # парсим групповой чат
            name = self.find_element_or_none(parent=self.driver,
                                    by=By.XPATH,
                                    value='//*[@id="app"]/div/div/div[2]/div[3]/span/div/span/div/div/section/div[1]/div/div[2]/div/div[1]/div/div/div[2]').text
            phones_raw = self.find_element_or_none(parent=self.driver,
                                               by=By.XPATH,
                                               value='//*[@id="main"]/header/div[2]/div[2]/span').text
            phones = phones_raw.split(', ')
        return (name, phones)


    def get_messages(self, dialog):
        dlg = dialog.web_el
        # скроллим диалог до начала
        self.find_element_or_none(parent=self.driver,
                             by=By.XPATH,
                             value='//*[@id="main"]/div[3]/div/div[2]').send_keys(Keys.CONTROL + Keys.HOME)
        # собираем сообщения и их даты
        list_items = self.find_elements_or_none(parent=self.driver,
                                           by=By.CLASS_NAME,
                                           value='focusable-list-item')
        messages = []
        for i, item in enumerate(list_items):
            # ищем элемент, содержащий дату и отправителя
            datetime_sender_web_el = self.find_element_or_none(parent=item,
                                                          by=By.CLASS_NAME,
                                                          value='copyable-text')
            if datetime_sender_web_el:
                mes_info = self.extract_info_from_text_message(datetime_sender_web_el)
            else:
                mes_info = self.extract_info_from_media_message(item, list_items)
            messages.append(mes_info)
        return messages


    def extract_info_from_text_message(self, datetime_sender_web_el):
        # для сообщений типа "текст", "контакт"
        datetime_sender = datetime_sender_web_el.get_attribute('data-pre-plain-text')
        date_time = datetime_sender[1:18]
        sender = datetime_sender[20:-2]
        text_web_el = self.find_element_or_none(parent=item,
                                           by=By.CLASS_NAME,
                                           value='selectable-text')
        text_web_el = self.find_element_or_none(parent=text_web_el,
                                           by=By.TAG_NAME,
                                           value='span')
        text = text_web_el.text if text_web_el else ''
        return MessageInfo(date_time, sender, text)


    def extract_info_from_media_message(self, item, list_items):
        # для сообщений типа "фото", "видео", "документ"
        # ищем элемент со временем отправки
        time_web_el = self.find_element_or_none(parent=item,
                                           by=By.XPATH,
                                           value='.//div/div[1]/div[1]/div/div[2]/div/span')
        if time_web_el:
            time = time_web_el.text  # TODO: время последнего видео
            text = '[фото/видео]'  # TODO: различать фото и видео
        else:
            time_web_el = self.find_element_or_none(parent=item,
                                               by=By.XPATH,
                                               value='.//div/div[1]/div[1]/div[2]/div/span')
            if time_web_el:
                time = time_web_el.text
                text = '[документ]'  # TODO: название документа
            else:
                # плашка с датой
                pass
        for item_reversed in list_items[i::-1]:
            # ищём дату сообщения
            date_web_el = self.find_element_or_none(parent=item_reversed,
                                               by=By.XPATH,
                                               value='.//div/span')
            if date_web_el:
                date = date_web_el.text
                if date == 'ВЧЕРА':
                    date = dt.date.today() - dt.timedelta(days=1)
                    date = date.strftime('%d.%m.%Y')
                elif date == 'СЕГОДНЯ':
                    date = dt.date.today().strftime('%d.%m.%Y')
                elif date in DAYS_OF_WEEK:
                    date = self.get_date_by_weekday(date)
                if not re.match(r'[\d]{2}.[\d]{2}.[\d]{4}', date):
                    # в дате лежит что-то не то
                    self.find_element_or_none(parent=self.driver,
                                         by=By.XPATH,
                                         value='//*[@id="main"]/div[3]/div/div[2]/div[2]').send_keys(Keys.DOWN)
                    date = self.find_element_or_none(parent=self.driver,
                                                by=By.XPATH,
                                                value='//*[@id="main"]/div[3]/div/span/div/div/div/span').text
                    date = self.get_date_by_weekday(date)
                # TODO: проверить, что в длинном диалоге не теряются сообщения
                # TODO: исправить "Сообщения защищены сквозным шифрованием. Третьи лица, включая WhatsApp, не могут прочитать или прослушать их. Нажмите, чтобы узнать подробнее."
        date_time = f'{time}, {date}'
        sender = 'ну кто-то'  # TODO: кто
        return MessageInfo(date_time, sender, text)


driver = Edge()
with WhatsAppParser(driver) as parser:
    names_phones = parser.get_contacts_from_dialog('Выпускники 1989')
    for name, phone in names_phones:
        print('='*25 + i + '='*25)
        print('Имя:', name)
        print('Телефон:', phone)
        print('='*50)
