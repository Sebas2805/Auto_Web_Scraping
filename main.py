import pandas as pd
import numpy as np

import time
from datetime import datetime

from Scraping_SantaFe import santaFe_Scraping
from Scraping_EVs import EVs_Scraping
from Scraping_Lexus import Lexus_Scraping
from Scraping_Mazda import Mazda_Scraping

from email_sender import send_email

#Generate all the files
try:
    SantaFe_DF, SantaFe_Name = santaFe_Scraping()
    print(SantaFe_Name)
except Exception as err:
    print('Run of Santa Fe script was not successfull, error: ', err)

try:
    EVs_DF, EV_name = EVs_Scraping()
except Exception as err:
    print('Run of EV script was not successfull, error: ', err)

try:
    LexusDF, lexus_name = Lexus_Scraping()
except Exception as err:
    print('Run of Lexus script was not successfull, error: ', err)

try:
    Mazda_DF, Mazda_name= Mazda_Scraping()
except Exception as err:
    print('Run of Mazda script was not successfull, error: ', err)

#Concat all results in the same Dataframe

fullReport_name = f'Full_Scraping_Report-{datetime.today().date()}.xlsx'

with pd.ExcelWriter(fullReport_name, engine='openpyxl') as writer:
    SantaFe_DF.to_excel(writer, sheet_name=SantaFe_Name, index=False)
    EVs_DF.to_excel(writer, sheet_name=EV_name, index=False)
    LexusDF.to_excel(writer, sheet_name=lexus_name, index=False)
    Mazda_DF.to_excel(writer, sheet_name=Mazda_name, index=False)


#Send email

send_email(
    fullReport_name
)

print('Success')