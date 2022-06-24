from selenium.webdriver import Edge
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup as BS
from time import sleep
# from tqdm import tqdm

import webbrowser

# открываем WhatsApp в браузере
driver = Edge()
driver.get("https://web.whatsapp.com")

try:
    element = wait(driver, 600).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="pane-side"]/div/div/div'))
    )
    sleep(3)
    # pane_side = driver.find_element(by=By.XPATH, value='//*[@id="pane-side"]/div/div/div')
    dialogs = driver.find_elements(by=By.XPATH, value='//*[@id="pane-side"]/div/div/div/div')

    print(len(dialogs))

    # dialog.click()

    # divs = pane_side.find_elements_by_tag_name('div')
    # print(len(divs))

    # html = pane_side.get_attribute('innerHTML')
    namelist = []
    phonenumber = []
    Date = []
    # for dlg in dialogs:
    # with open('index.html', 'a', encoding='utf-8') as f:
    # f.write(dlg.get_attribute('innerHTML'))
    for dil in dialogs:
        dil.click()
        profile = driver.find_element(by=By.XPATH, value='//*[@id="main"]/header/div[2]/div/div/span')
        profile.click()
        sleep(3)
        name = driver.find_element(by=By.XPATH,
                                   value='//*[@id="app"]/div/div/div[2]/div[3]/span/div/span/div/div/section/div[1]/div[2]/h2/span')
        namelist.append(name.text)
        phone = driver.find_element(by=By.XPATH,
                                    value='//*[@id="app"]/div/div/div[2]/div[3]/span/div/span/div/div/section/div[1]/div[2]/div/span/span')
        phonenumber.append(phone.text)
        driver.find_element(by=By.XPATH, value='//*[@id="main"]/div[3]/div/div[2]').send_keys(Keys.CONTROL + Keys.HOME)
        messagesout = driver.find_elements(by=By.CLASS_NAME, value='message-out')
        messagesin = driver.find_elements(by=By.CLASS_NAME, value='message-in')
        messages = messagesout+messagesin
        for mes in messages:
            date = mes.find_element(by=By.CLASS_NAME, value='copyable-text').get_attribute('data-pre-plain-text')
            Date.append(date)
            mes_text = mes.find_element(by=By.CLASS_NAME, value='selectable-text').find_element(by=By.TAG_NAME, value='span')


        sleep(3)
    # webbrowser.open('index.html', new=2)
finally:

    print('Имена профилей', namelist)
    print('Номера телефонов', phonenumber)
    driver.quit()
    pass
