import webbrowser
import pyautogui
import tkinter as tk
import time
import requests
import json
import sys


import pandas as pd
import numpy as np


# Set file parameters
NAME_PARAMETER = []
FILE_PARAMETER = open('PARAMETERS.txt', 'r')
for LINE in FILE_PARAMETER:
    LINE = LINE.strip()
    LINE = LINE.replace('\n', '')

    NAME_PARAMETER.append(LINE)

FILENAME = NAME_PARAMETER[0]  # Naming the output file
STATE = NAME_PARAMETER[1]  # Enable filter
FILE_PARAMETER.close()


# Setup tkinker. Used for clipboard feature.
root = tk.Tk()
root.withdraw()


# Location for parse.
# Value is from F12 Source -> Network -> locationsmap file
# Edit when new map location is needed
loc_lst = []
LOC_PARAMETER = open('LOCATION.txt', 'r')
for loc in LOC_PARAMETER:
    loc = loc.strip()
    loc = loc.replace('\n', '')

    loc_lst.append(loc)

LOC_PARAMETER.close()

# Search Parameters
LIMIT = '2000'  # Return searches, max:2000
REMOVE_LEVEL = '1,2'  # Remove level 1 and 2 chargers from search
REMOVE_CONNECTOR = '7'  # Remove Tesla connector

# Build our url
parameter = f'&limit={LIMIT}&key=olitest&remove_networks=&remove_levels={REMOVE_LEVEL}&remove_connectors={REMOVE_CONNECTOR}&remove_other=&above_power='
start_url = 'https://apiv2.chargehub.com/api/locationsmap?'
url_lst = [f'{start_url}{loc}{parameter}' for loc in loc_lst]


def open_web(_url):
    """
    Open web browser (Google Chrome) in incognito mode.
    Used to open site for front-end web scraping.
    :param _url: url of EV Station from chargehub.com
    :return: None
    """
    chrome_path = 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe %s --incognito'
    webbrowser.get(chrome_path).open_new(_url)


def close_web():
    pyautogui.hotkey('ctrl', 'w')


def front_end_scrape():
    """
    Get all front-end text.
    :return: Copy clipboard information.
    """
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(1.5)

    pyautogui.hotkey('ctrl', 'c')
    time.sleep(1.5)

    return root.clipboard_get()


def filter_data(raw_data):
    """
    Input: Raw data
    Output:
      - STATION_NAME
      - ADDRESS
      - CITY
      - STATE
      - ZIP
      - NETWORK
      - PRICE_RAW
      - CHRAGE_SPEED
    """
    raw_data = raw_data.split('\n')

    result = []
    for idx, readline in enumerate(raw_data):
        # STATION_NAME
        if 'General Information' in readline:
            result.append(raw_data[idx - 1].strip())
        # EV_NETWORK
        if 'Station Information' in readline:
            result.append(raw_data[idx + 1].strip())

        if 'Address' in readline:
            # ADDRESS
            result.append(raw_data[idx + 1].strip())

            # CITY, STATE
            city_state = raw_data[idx + 2].split(',')

            result.append(city_state[0].strip())
            result.append(city_state[1].strip())

            # ZIP_CODE
            result.append(raw_data[idx + 3].strip())

        if 'Cost' in readline:
            # PRICE_RAW
            result.append(readline)

            # CHARGE_SPEED
            result.append(raw_data[idx - 1].strip())
            break

    return result


def get_all_locid(_url_lst):
    id_lst = []
    for _url in _url_lst:
        r = requests.get(_url)
        data = r.json()

        for i in data:
            locid = i['LocID']
            if locid not in id_lst:
                id_lst.append(locid)

    return id_lst


def rebuild_df_index(_df, _index):
    _station_lst = []
    _network_lst = []
    _address_lst = []
    _city_lst = []
    _state_lst = []
    _zip_lst = []
    _charge_speed_lst = []
    _price_raw_lst = []

    for i in _index:
        _station_lst.append(_df['STATION'][i])
        _network_lst.append(_df['NETWORK'][i])
        _address_lst.append(_df['ADDRESS'][i])
        _city_lst.append(_df['CITY'][i])
        _state_lst.append(_df['STATE'][i])
        _zip_lst.append(_df['ZIP'][i])
        _charge_speed_lst.append(_df['CHARGE_SPEED'][i])
        _price_raw_lst.append(_df['PRICE_RAW'][i])

    new_df = pd.DataFrame({'STATION': _station_lst,
                           'NETWORK': _network_lst,
                           'ADDRESS': _address_lst,
                           'CITY': _city_lst,
                           'STATE': _state_lst,
                           'ZIP': _zip_lst,
                           'CHARGE_SPEED': _charge_speed_lst,
                           'PRICE_RAW': _price_raw_lst})

    return new_df


# Clean data
station_lst = []
network_lst = []
address_lst = []
city_lst = []
state_lst = []
zip_lst = []
charge_speed_lst = []
price_raw_lst = []

success_count = 0
error_count = 0

base_url = 'https://chargehub.com/en/full-details-page.html?locId='
station_id_lst = get_all_locid(url_lst)

print(len(station_id_lst), station_id_lst)  # Check id count to gauge how long the runtime

for station_id in station_id_lst:
    url = f'{base_url}{station_id}'

    open_web(url)
    time.sleep(6.5)  # Loading time

    front_end_info = front_end_scrape()

    try:
        station, address, city, state, zip_code, network, price_raw, charge_speed = filter_data(front_end_info)

        # Load
        station_lst.append(station)
        network_lst.append(network)
        address_lst.append(address)
        city_lst.append(city)
        state_lst.append(state)
        zip_lst.append(zip_code)
        price_raw_lst.append(price_raw)
        charge_speed_lst.append(charge_speed)

        success_count += 1
    except:
        print(f'error: {url}')
        error_count += 1

    close_web()
    time.sleep(2)  # Closing time


df = pd.DataFrame({'STATION': station_lst,
                   'NETWORK': network_lst,
                   'ADDRESS': address_lst,
                   'CITY': city_lst,
                   'STATE': state_lst,
                   'ZIP': zip_lst,
                   'CHARGE_SPEED': charge_speed_lst,
                   'PRICE_RAW': price_raw_lst})


df = df.drop_duplicates()  # Ensure no duplicates
df = df[df['STATE'] == STATE]

# Handle any naming issue before saving.
try:
    df.to_csv(f'{FILENAME}_output_raw.csv', index=False)
except:
    df.to_csv('naming_error_raw_df.csv', index=False)

# Output outcome message
print(f'Successful scraped: {success_count}')
print(f'Error occur: {error_count}')

# Need to manually fix some data records before splitting the charge speed into different category
'''# Get the charging speed into different category
idx = 0
end_idx = len(df)

unknown_idx = []
slow_idx = []
fast_idx = []
ultra_fast_idx = []

# Split df into categories: unknown, slow, fast, ultra-fast charging
while idx < end_idx:
    charge_speed = df['CHARGE_SPEED'][idx]
    a, kw = charge_speed.split(',')

    kw = kw.replace('kW', '')
    kw = kw.replace(' ', '')

    if '?' in kw:
        unknown_idx.append(idx)
    elif float(kw) >= 125:
        ultra_fast_idx.append(idx)
    elif float(kw) >= 50:
        fast_idx.append(idx)
    else:
        slow_idx.append(idx)

    idx += 1

df_fc = rebuild_df_index(df, fast_idx)
df_fc.to_csv(f'{FILENAME}_fc.csv', index=False)

df_ufc = rebuild_df_index(df, ultra_fast_idx)
df_ufc.to_csv(f'{FILENAME}_ufc.csv', index=False)'''

