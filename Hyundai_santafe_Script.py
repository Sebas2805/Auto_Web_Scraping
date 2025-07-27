import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import locale
locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')

import time
from datetime import datetime


from bs4 import BeautifulSoup
import requests

import pandas as pd


# 1. Import driver and get to the link
chrome_options = Options()
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

chrome_options.add_argument("--disable-features=RendererCodeIntegrity")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-features=VizDisplayCompositor")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--headless=new")  # Ejecutar sin abrir ventana
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')

service = Service()
driver = webdriver.Chrome(service=service, options=chrome_options)

driver.get("https://crautos.com/autosusados/index.cfm")

# 2. Set and find cars list based on filters

# ---- Hyundai Santa Fe ---- #

select_filters_element = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, '//*[@id="searchform"]/div/div[1]/table/tbody/tr[1]/td[2]/select'))
)

select_brand = Select(select_filters_element)
select_brand.select_by_visible_text('Hyundai')

# -- As first select is visible, rest of the elements are visible too (No need to use Web Driver Wait)

set_model = driver.find_element(By.XPATH,'//*[@id="searchform"]/div/div[1]/table/tbody/tr[2]/td[2]/input')
set_model.send_keys("SANTA FE")

start_date = driver.find_element(By.XPATH, '//*[@id="searchform"]/div/div[2]/table/tbody/tr[1]/td[2]/select')
end_date = driver.find_element(By.XPATH, '//*[@id="searchform"]/div/div[2]/table/tbody/tr[2]/td[2]/select')

select_start_date = Select(start_date)
select_end_date = Select(end_date)

select_start_date.select_by_visible_text('2006')
select_end_date.select_by_visible_text('2015')

search_button = driver.find_element(By.XPATH, '//*[@id="searchform"]/div/div[2]/table/tbody/tr[8]/td/button')
search_button.click()


# 3. Collect Links

car_links = []

while True:
    time.sleep(1)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "form"))
    )

    # get the links from the main form
    link_elements = driver.find_elements(By.XPATH, '//form[@name="form"]//a[contains(@href, "cardetail.cfm?c=")]')
    car_links.extend([elem.get_attribute("href") for elem in link_elements])

    # Determinate wheter stop the loop if it is in the last page
    try:
        next_li = driver.find_element(By.CSS_SELECTOR, "li.page-item.page-next")
        next_a = next_li.find_element(By.TAG_NAME, "a")
        next_a.click()
    except NoSuchElementException:
        # No next page available, break loop
        break

# 4. Cerrar navegador
driver.quit()

car_links = list(set(car_links))
print("Total Number: ", len(car_links))


# ----------- Collect Data -------------#

headers = {
    'User-Agent': 'Mozilla/5.0'
}

car_data = []

for url in car_links:
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.content, 'html.parser')

    info_auto = {}

    title_container = soup.find_all("h1")[0].get_text(strip=True).replace('\xa0', ' ')
    title_parts = re.search(r'^(?P<marca>\w+)\s+(?P<modelo>.+)\s+(?P<anio>\d{4})$', title_container)

    if title_parts:
        info_auto["Brand"] = title_parts.group("marca")
        info_auto["Model"] = title_parts.group("modelo")
        info_auto["Year"] = title_parts.group("anio")

    # ID
    info_auto["url"] = url

    # Price 
    price_crc = soup.find_all("h1")[1].get_text(strip=True)
    price_crc = int(re.sub(r'[^\d]', '', price_crc))
    info_auto["Price_CRC"] = price_crc

    # Data table processing
    tabla = soup.select_one("table.table-striped.mytext2")
    if tabla:
        filas = tabla.select("tr")
        for fila in filas:
            celdas = fila.select("td")
            if len(celdas) == 2:
                clave = celdas[0].get_text(strip=True)
                valor = celdas[1].get_text(strip=True)
                if clave:
                    info_auto[clave] = valor
            elif len(celdas) == 1:
                texto = celdas[0].get_text(strip=True)
                if "veces" in texto.lower():
                    # Visits
                    vistas = ''.join(filter(str.isdigit, texto))
                    info_auto["Vistas"] = int(vistas) if vistas else None
                else:
                    # Description
                    info_auto["Descripcion_extra"] = texto

    car_data.append(info_auto)

# Create Dataframe
df = pd.DataFrame(car_data)

#Take the link's id for interal reference
def get_linkID(url):
    match = re.search(r'c=(\d+)&', url)
    if match:
        num = match.group(1)
        return num
    else:
        return None

df["linkID"] = df['url'].apply(get_linkID)

# Sort columns names
cols = ['linkID','url', 'Brand', 'Model', 'Year', 'Price_CRC'] + [col for col in df.columns if col not in ['linkID','url', 'Brand', 'Model', 'Year', 'Price_CRC']]
df = df[cols]
df["Data Date"] = datetime.today()

#Fix the "Setiembre" typo

def fix_typo(date_str):
    if isinstance(date_str, str):
        return date_str.replace("Setiembre", "Septiembre")
    else:
        return date_str
    
df["Fecha de ingreso"] = df["Fecha de ingreso"].apply(fix_typo)

df["Fecha de ingreso"] = df["Fecha de ingreso"].apply(lambda x: datetime.strptime(x.strip(), "%d de %B del %Y"))

df["Price_CRC"] = df['Price_CRC'].apply(lambda x: x * 510 if len(str(x))<7 else x)

# Save
df.to_csv(f'SantaFe_{datetime.today().date()}.csv', index=False)