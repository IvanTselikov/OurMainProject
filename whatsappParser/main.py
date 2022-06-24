from selenium.webdriver import Edge
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup as BS
from time import sleep
from datetime import datetime
# from tqdm import tqdm

import webbrowser

# открываем WhatsApp в браузере
driver = Edge()
driver.get("https://web.whatsapp.com")

try:
    # ожидаем, когда прогрузится страница с диалогами
    element = wait(driver, 600).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="pane-side"]/div/div/div'))
    )
    sleep(3)  # TODO: дожидаться пока диалоги прогрузятся полностью
    # pane_side = driver.find_element(by=By.XPATH, value='//*[@id="pane-side"]/div/div/div')

    # подгружаем диалоги
    dialogs = driver.find_elements(by=By.XPATH, value='//*[@id="pane-side"]/div/div/div/div')

    # print(len(dialogs))

    # dialog.click()

    # divs = pane_side.find_elements_by_tag_name('div')
    # print(len(divs))

    # html = pane_side.get_attribute('innerHTML')
    names_phones = []
    dates_messages = []
    # for dlg in dialogs:
    # with open('index.html', 'a', encoding='utf-8') as f:
    # f.write(dlg.get_attribute('innerHTML'))
    for dlg in dialogs:
        # заходим в диалог
        dlg.click()
        # ищем информацию о номере телефона
        # открываем информацию о профиле собеседника
        profile = driver.find_element(by=By.XPATH, value='//*[@id="main"]/header/div[2]/div/div/span')
        profile.click()
        sleep(3)  # TODO: дожидаться прогрузки
        name = driver.find_element(by=By.XPATH,
                                   value='//*[@id="app"]/div/div/div[2]/div[3]/span/div/span/div/div/section/div[1]/div[2]/h2/span').text
        phone = driver.find_element(by=By.XPATH,
                                    value='//*[@id="app"]/div/div/div[2]/div[3]/span/div/span/div/div/section/div[1]/div[2]/div/span/span').text
        names_phones.append((name, phone))
        # скроллим диалог до начала
        driver.find_element(by=By.XPATH,
                            value='//*[@id="main"]/div[3]/div/div[2]').send_keys(Keys.CONTROL + Keys.HOME)
        # собираем сообщения и их даты
        flis = driver.find_elements(by=By.CLASS_NAME, value='focusable-list-item')
        messages = []
        for fli in flis:
            # убираем из найденных элементов те, которые не являются
            # входящими или исходящими сообщениями
            classes = fli.get_attribute('class').split()
            if 'message-out' in classes or 'message-in' in classes:
                messages.append(fli)
        result = []
        for mes in messages:
            try:
                date_sender = mes.find_element(by=By.CLASS_NAME, value='copyable-text').get_attribute('data-pre-plain-text')
                date = date_sender[1:18]
                sender = date_sender[21:-2]
                mes_text = mes.find_element(by=By.CLASS_NAME, value='selectable-text').find_element(by=By.TAG_NAME, value='span')
                text = mes_text.text if mes_text else ''
                result.append((date, sender, text))  # TODO: классы вместо кортежей
            except:
                result.append(('хз когда', 'хз кто', 'хз что'))
        sleep(3)
    # webbrowser.open('index.html', new=2)
finally:
    print('Имена и номера:', names_phones)
    for date, sender, text in result:
        print('='*30)
        print('Дата:', date)
        print('От:', sender)
        print('Сообщение:', text)
    driver.quit()
    pass
