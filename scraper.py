import requests
from bs4 import BeautifulSoup
import time
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse, ParseResult, quote_plus
import os
import json

creds_json = os.environ.get('GSHEETS_CREDS')

if not creds_json:
    raise EnvironmentError("❌ Proměnná prostředí 'GSHEETS_CREDS' nebyla načtena – zkontroluj Settings > Secrets > Actions.")

# vytvořit credentials.json
with open("credentials.json", "w") as f:
    f.write(creds_json)

print("✅ credentials.json vytvořen.")

try:
    json.loads(creds_json)
    print("✅ JSON loaded successfully")
except json.JSONDecodeError as e:
    print("❌ JSON decode error:", e)
    print("❌ Received string:", creds_json)
    raise

print("🟢 Spuštěn run_scraper()", flush=True)

# 📌 Klíčová slova
keywords = [
    'future watch auto',
    'o-pee-chee platinum rookie auto',
    'premier rookie auto patch',
    'the cup rookie auto',
    'ultimate rookie auto',
    'ultimate introduction',
    'splendor rookie',
    'ice premieres auto',
    'ice premieres 99',
    'aurum signatures rookie',
    'artifacts rookie',
    'subzero rookie auto'
]

# 🔐 Google Sheets přístup
def init_gspread():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    return client

# 🔄 Úprava URL – přidání keywordu do _nkw
def update_url_keyword(base_url, new_keyword):
    parsed = urlparse(base_url)
    query = parse_qs(parsed.query)
    query['_nkw'] = [new_keyword]
    new_query = urlencode(query, doseq=True)
    new_url = ParseResult(parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment)
    return urlunparse(new_url)

# 🧼 Název listu ze slova
def sanitize_keyword(keyword):
    return keyword.replace(" ", "_").replace("+", "_").lower()

# 🔎 Načtení existujících odkazů ze sloupce "Link"
def get_existing_links(sheet):
    try:
        data = sheet.get_all_values()
        links = set()
        for row in data[1:]:
            if len(row) > 3:
                link = row[3].strip()
                if link and link != 'N/A':
                    links.add(link)
        return links
    except Exception as e:
        print(f"⚠️ Chyba při načítání existujících dat: {e}")
        return set()

# 📄 Scrapování jednoho keywordu
def scrape_keyword(base_url, keyword, spreadsheet, max_empty_pages=2):
    print(f"\n🚀 Scrapování keywordu: {keyword}")
    url = update_url_keyword(base_url, keyword.replace(" ", "+"))
    page_number = 1
    print(f'🌐 URL: {url}')

    list_name = sanitize_keyword(keyword)
    try:
        sheet = spreadsheet.worksheet(list_name)
        print(f"📄 List '{list_name}' existuje – zapisujeme do něj")
    except gspread.exceptions.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=list_name, rows="1000", cols="10")
        print(f"📄 List '{list_name}' vytvořen")
        sheet.append_row(["Keyword", "Title", "Price", "Link", "End date"])

    existing_links = get_existing_links(sheet)
    print(f"🔎 Existující linky: {len(existing_links)}")

    empty_page_count = 0

    while True:
        print(f'\n🔎 Stránka {page_number} pro "{keyword}"')
        params = {'_pgn': page_number}

        try:
            response = requests.get(url, headers=HEADERS, params=params)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            print(f"❌ Chyba při načítání stránky: {e}")
            break

        items = soup.find_all('div', class_='su-card-container__content')
        print(f"📦 Nalezeno {len(items)} položek")

        page_items = []

        for item in items:
            try:
                title_tag = item.find('span', class_='su-styled-text primary default')
                title = title_tag.text.strip() if title_tag else 'N/A'

                price_tag = item.find('span', attrs={"class": lambda x: x and "s-card__price" in x})
                price = price_tag.text.strip() if price_tag else 'N/A'

                link_tag = item.find('a', class_='su-link')
                link = link_tag['href'].split('?')[0] if link_tag and link_tag.has_attr('href') else 'N/A'

                end_tag = item.find('span', class_='su-styled-text positive default')
                end_date = end_tag.text.strip() if end_tag else 'N/A'

                print(f"🔗 Link kandidát: {link}")

                if link not in existing_links and link != 'N/A':
                    row = [
                        keyword,
                        title,
                        price,
                        link,
                        end_date
                    ]
                    page_items.append(row)
                    existing_links.add(link)
            except Exception as e:
                print(f"⚠️ Chyba v položce: {e}")
                continue

        if page_items:
            try:
                sheet.append_rows(page_items, value_input_option='RAW')
                print(f"✅ Zapsáno {len(page_items)} nových řádků do listu '{list_name}'")
            except Exception as e:
                print(f"❌ Chyba při zápisu do Google Sheets: {e}")
            empty_page_count = 0
        else:
            empty_page_count += 1
            print(f"📭 Stránka bez nových položek ({empty_page_count}/{max_empty_pages})")

        # 🛑 Ukončení po X prázdných stránkách
        if empty_page_count >= max_empty_pages:
            print(f"⛔ {empty_page_count} po sobě prázdných stránek – končíme keyword '{keyword}'")
            break

        next_button = soup.find('a', class_='pagination__next icon-link')
        if not next_button:
            print(f"🏁 Konec pro keyword '{keyword}' – další stránka neexistuje.")
            break

        page_number += 1
        time.sleep(10)

# 🔁 Hlavní funkce
def run_scraper():
    client = init_gspread()
    try:
        spreadsheet = client.open("Ebay_scrape_vysledky")
    except gspread.exceptions.SpreadsheetNotFound:
        spreadsheet = client.create("Ebay_scrape_vysledky")
        print("🆕 Soubor 'Ebay_scrape_vysledky' byl vytvořen.")

    for keyword in keywords:
        scrape_keyword(BASE_URL, keyword, spreadsheet, max_empty_pages=2)
        wait = random.randint(60, 180)
        print(f"⏳ Pauza {wait} sekund před dalším keywordem...")
        time.sleep(wait)

# 🌐 BASE URL bez _nkw
BASE_URL = "https://www.ebay.com/sch/i.html?_in_kw=4&_sacat=0&LH_Complete=1&LH_Sold=1&_udlo=1&LH_Auction=1&LH_PrefLoc=2&_sop=-1&_ipg=240&Sport=Ice%2520Hockey&_dcat=261328"

# 🧠 Hlavičky (anti-bot)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.ebay.com/',
}

# ▶️ Spuštění
if __name__ == "__main__":

    run_scraper()






