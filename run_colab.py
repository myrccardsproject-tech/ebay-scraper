import os
import time
import json
import smtplib
import ssl
from email.message import EmailMessage
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Načtení všech potřebných dat z GitHub Secrets (zůstává stejné) ---
COLAB_URL = os.environ.get('COLAB_URL')
COOKIES_JSON_STRING = os.environ.get('GOOGLE_COOKIES_JSON')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')
SENDER_APP_PASSWORD = os.environ.get('SENDER_APP_PASSWORD')
RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL')

# --- Funkce pro odeslání chybového emailu (zůstává stejná) ---
def send_email(subject, body):
    if not all([SENDER_EMAIL, SENDER_APP_PASSWORD, RECIPIENT_EMAIL]):
        print("⚠️ Chybí proměnné pro odeslání emailu, hlášení se neodešle.")
        return
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg.set_content(body)
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            server.send_message(msg)
        print(f"📧 Chybové hlášení odesláno na {RECIPIENT_EMAIL}")
    except Exception as e:
        print(f"❌ Nepodařilo se odeslat email: {e}")

# --- Nastavení prohlížeče pro běh na serveru (zůstává stejné) ---
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 30)

print("✅ Proces spuštěn, prohlížeč nastaven.")

try:
    # --- Přihlášení pomocí cookies ---
    print("⏳ Načítám cookies pro přihlášení...")
    driver.get("https://google.com")
    cookies = json.loads(COOKIES_JSON_STRING)
    for cookie in cookies:
        # Oprava pro 'sameSite' atribut
        if 'sameSite' in cookie and cookie['sameSite'] not in ["Strict", "Lax", "None"]:
            del cookie['sameSite']
        
        # FINÁLNÍ ZMĚNA ZDE: Přidáváme pouze cookies pro domény Google
        # Používáme .get() pro bezpečný přístup k klíči 'domain'
        if "google" in cookie.get('domain', ''):
            try:
                driver.add_cookie(cookie)
            except Exception as cookie_error:
                print(f"⚠️ Nepodařilo se přidat cookie: {cookie.get('name')}. Chyba: {cookie_error}")
        else:
            print(f"⏩ Přeskakuji cookie pro doménu: {cookie.get('domain', 'N/A')}")
    
    # --- Spuštění Colab notebooku ---
    print(f"⏳ Otevírám Colab notebook...")
    driver.get(COLAB_URL)

    print("⏳ Hledám tlačítka pro spuštění skriptu...")
    runtime_menu_xpath = "//div[@id='runtime-menu-button']"
    wait.until(EC.element_to_be_clickable((By.XPATH, runtime_menu_xpath))).click()

    run_all_xpath = "//div[@command='run-all']"
    wait.until(EC.element_to_be_clickable((By.XPATH, run_all_xpath))).click()
    print("✅ Příkaz 'Spustit vše' byl úspěšně proveden.")
    
    print("⏳ Čekám 30 minut na dokončení scraperu...")
    time.sleep(1800)
    print("✅ Čekání dokončeno, skript pravděpodobně doběhl úspěšně.")

except Exception as e:
    # --- Odeslání chybového hlášení ---
    print(f"❌ Vyskytla se kritická chyba: {e}")
    error_details = traceback.format_exc()
    error_body = f"Při běhu skriptu pro Colab notebook nastala chyba.\n\nURL: {COLAB_URL}\n\nDetaily chyby:\n{error_details}"
    send_email("❌ CHYBA: Colab Scraper Selhal!", error_body)
    raise e

finally:
    # --- Ukončení ---
    driver.quit()
    print("🏁 Proces dokončen.")
