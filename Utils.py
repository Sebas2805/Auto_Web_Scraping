import re
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import requests

import time
from datetime import datetime

Currency_CRC_Multiplier = 510 #Multiplier for USD/CRC convertion

def get_linkID(url):
    match = re.search(r'c=(\d+)&', url)
    if match:
        return match.group(1)
    else:
        return None

def fix_typo(date_str):
    if isinstance(date_str, str):
        return date_str.replace("Setiembre", "Septiembre")
    else:
        return date_str
    
def CRAUTOS_get_linksInfo(car_links):
    
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

    df = pd.DataFrame(car_data)

    return df


def dataframe_Transform(df):
    df["linkID"] = df['url'].apply(get_linkID)

    cols = ['linkID', 'url', 'Brand', 'Model', 'Year', 'Price_CRC'] + [col for col in df.columns if col not in ['linkID', 'url', 'Brand', 'Model', 'Year', 'Price_CRC']]
    df = df[cols]

    df["Data Date"] = datetime.today()

    df["Fecha de ingreso"] = df["Fecha de ingreso"].apply(fix_typo)

    df["Fecha de ingreso"] = df["Fecha de ingreso"].apply(lambda x: datetime.strptime(x.strip(), "%d de %B del %Y"))

    df["Price_CRC"] = df['Price_CRC'].apply(lambda x: x * Currency_CRC_Multiplier if len(str(x)) < 7 else x)

    return df

def save_DF(df, name):
    df.to_csv('outputs/'+name+".csv", index=False)