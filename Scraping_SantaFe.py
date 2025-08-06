import re
import locale
locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

import time
from datetime import datetime

from bs4 import BeautifulSoup
import requests

import pandas as pd

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

import Utils as utils

#Utils



def santaFe_Scraping():
    # 1. Navegación y filtros con Playwright

    car_links = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://crautos.com/autosusados/index.cfm")
        page.locator('select[name="brand"]').select_option(value='16')
        page.locator('select[name="yearfrom"]').select_option(value='2007')
        page.locator('select[name="yearto"]').select_option(value='2014')
        page.locator('input[name="modelstr"]').fill('Santa fe')
        page.locator('#searchform button[type="submit"]').click()
        page.wait_for_selector('form[name="form"]', timeout=10000)

        while True:
            try:
                time.sleep(1)  # Pequeña pausa para estabilizar la carga

                form_locator = page.locator('form[name="form"][action="ucompare.cfm"]')
                form_locator.wait_for(state='visible', timeout=10000)

                link_elements = form_locator.locator('a[href*="cardetail.cfm?c="]')
                count = link_elements.count()
                print(f"Número de links detectados: {count}")
                if count == 0:
                    print("No se encontraron links.")
                    break

                texts = link_elements.all()
                hrefs = []
                for element in texts:
                    href = element.get_attribute('href')
                    if href and 'autosnuevos' not in href.lower():
                        if href.startswith('http'):
                            full_url = href
                        else:
                            full_url = 'https://crautos.com/autosusados/' + href.lstrip('/')
                        hrefs.append(full_url)
                car_links.extend(hrefs)

                next_button = page.locator('li.page-item.page-next a')
                if next_button.count() == 0 or not next_button.is_enabled():
                    print("No hay botón siguiente o está deshabilitado. Terminado.")
                    break

                next_button.scroll_into_view_if_needed()
                next_button.click()

                page.wait_for_load_state('load')
                page.wait_for_selector('form[name="form"]', timeout=10000)

            except PlaywrightTimeoutError:
                break
            except Exception as e:
                print("Error inesperado, reintentando:", e)
                time.sleep(2)
                continue

        browser.close()

    car_links = list(set(car_links))
    print("Total Number: ", len(car_links)) 


    # 2. ----------- Continua scraping con requests + BeautifulSoup, luego modificando el dataframe final-----------

    df = utils.CRAUTOS_get_linksInfo(car_links)

    df = utils.dataframe_Transform(df)

    # 3. Save CSV
    name = f'SantaFe_{datetime.today().date()}'
    utils.save_DF(df, name)

    # 4. Return the DF to main py function

    return df , name