import re
import locale
locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

import time
from datetime import datetime

from bs4 import BeautifulSoup
import requests

import pandas as pd

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# 1. Navegación y filtros con Playwright

car_links = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)  # igual que headless en Selenium
    page = browser.new_page()

    page.goto("https://crautos.com/autosusados/index.cfm")

    # Esperar al select marca y filtrar por 'Eléctrico'
    #page.wait_for_selector('select[name="brand"]', timeout=10000)  # Ajustar selector acorde si es distinto
    
    # Seleccionar Combustible Eléctrico (value='4')
    page.locator('select[name="fuel"]').select_option(value='4')

    #page.locator('select[name="priceto"]').select_option(value='30000000') #Price limit

    # Clic en botón buscar
    page.locator('#searchform button[type="submit"]').click()

    # Esperar que cargue resultados - form con name="form"
    page.wait_for_selector('form[name="form"]', timeout=10000)

    # 3. Colectar links recorriendo todas las páginas
    while True:
        # Esperar que el formulario esté visible antes de buscar links
        form_locator = page.locator('form[name="form"][action="ucompare.cfm"]')
        form_locator.wait_for(state='visible', timeout=10000)

            # Obtener los enlaces en ese momento (locator fresco)
        link_elements = form_locator.locator('a[href*="cardetail.cfm?c="]')
        texts = link_elements.all()
        hrefs = []
        for element in texts:
            href = element.get_attribute('href')
            if href:
                # Normaliza URL relativa y verifica exclusions
                if not 'autosnuevos' in href.lower():
                    if href.startswith('http'):
                        full_url = href
                    else:
                        full_url = 'https://crautos.com/autosusados/' + href.lstrip('/')
                    hrefs.append(full_url)
        
        car_links.extend(hrefs)

        # Intentar click en siguiente página (li.page-item.page-next > a)
        try:
            next_button = page.locator('li.page-item.page-next a')
            if next_button.count() == 0 or not next_button.is_enabled():
                break
            next_button.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_selector('form[name="form"]', timeout=10000)
        except PlaywrightTimeoutError:
            # No existe botón siguiente o timeout esperando la nueva página: terminamos
            break

    browser.close()

car_links = list(set(car_links))
print("Total Number: ", len(car_links)) 


# ----------- Continúa igual tu scraping con requests + BeautifulSoup -----------

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

    info_auto["url"] = url

    price_crc = soup.find_all("h1")[1].get_text(strip=True)
    price_crc = int(re.sub(r'[^\d]', '', price_crc))
    info_auto["Price_CRC"] = price_crc

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
                    vistas = ''.join(filter(str.isdigit, texto))
                    info_auto["Vistas"] = int(vistas) if vistas else None
                else:
                    info_auto["Descripcion_extra"] = texto

    car_data.append(info_auto)


# Create DataFrame and process data = same as your original
df = pd.DataFrame(car_data)

def get_linkID(url):
    match = re.search(r'c=(\d+)&', url)
    if match:
        return match.group(1)
    else:
        return None

df["linkID"] = df['url'].apply(get_linkID)

cols = ['linkID', 'url', 'Brand', 'Model', 'Year', 'Price_CRC'] + [col for col in df.columns if col not in ['linkID', 'url', 'Brand', 'Model', 'Year', 'Price_CRC']]
df = df[cols]

df["Data Date"] = datetime.today()

def fix_typo(date_str):
    if isinstance(date_str, str):
        return date_str.replace("Setiembre", "Septiembre")
    else:
        return date_str

df["Fecha de ingreso"] = df["Fecha de ingreso"].apply(fix_typo)

df["Fecha de ingreso"] = df["Fecha de ingreso"].apply(lambda x: datetime.strptime(x.strip(), "%d de %B del %Y"))

df["Price_CRC"] = df['Price_CRC'].apply(lambda x: x * 510 if len(str(x)) < 7 else x)

# Save CSV
df.to_csv(f'EVs_{datetime.today().date()}.csv', index=False)