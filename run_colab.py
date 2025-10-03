import os
import time
import smtplib
import ssl
from email.message import EmailMessage
import traceback
# ZMĚNA 1: Importujeme standardní selenium a novou knihovnu
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

# --- Načtení dat (beze změny) ---
COLAB_URL = os.environ.get('COLAB_URL')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')
SENDER_APP_PASSWORD = os.environ.get('SENDER_APP_PASSWORD')
RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL')

# --- Funkce send_email (beze změny) ---
def send_email(subject, body):
    if not all([SENDER_EMAIL, SENDER_APP_PASSWORD, RECIPIENT_EMAIL]):
        print("⚠️ Chybí proměnné pro odeslání emailu.")
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

# --- Nastavení prohlížeče s profilem ---
options = webdriver.ChromeOptions() # Použijeme ChromeOptions místo generických Options
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument("--user-data-dir=chrome-profile/Default")

# ZMĚNA 2: Spustíme prohlížeč přes undetected_chromedriver
driver = uc.Chrome(options=options, use_subprocess=True)
wait = WebDriverWait(driver, 60)

print("✅ Proces spuštěn ve stealth režimu, profil prohlížeče načten.")

try:
    print(f"⏳ Otevírám Colab notebook...")
    driver.get(COLAB_URL)

    print("⏳ Zavírám případná vyskakovací okna...")
    try:
        short_wait = WebDriverWait(driver, 10)
        close_button_xpath = "//colab-dialog//paper-button[text()='OK'] | //colab-dialog//paper-button[text()='No Thanks'] | //colab-dialog//paper-button[text()='Dismiss']"
        close_button = short_wait.until(EC.element_to_be_clickable((By.XPATH, close_button_xpath)))
        close_button.click()
        print("✅ Vyskakovací okno nalezeno a zavřeno.")
        time.sleep(2)
    except Exception:
        print("⏩ Žádné vyskakovací okno nenalezeno, pokračuji.")

    print("⏳ Čekám na plné načtení uživatelského rozhraní...")
    wait.until(EC.presence_of_element_located((By.ID, "main-toolbar")))
    
    print("⏳ Hledám tlačítka pro spuštění skriptu...")
    runtime_menu_xpath = "//div[@id='runtime-menu-button']"
    wait.until(EC.element_to_be_clickable((By.XPATH, runtime_menu_xpath))).click()

    run_all_xpath = "//div[@command='run-all']"
    wait.until(EC.element_to_be_clickable((By.XPATH, run_all_xpath))).click()
    print("✅ Příkaz 'Spustit vše' byl úspěšně proveden.")
    
    print("⏳ Čekám 30 minut na dokončení scraperu...")
    time.sleep(1800)
    print("✅ Čekání dokončeno, skript úspěšně doběhl.")

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
