import requests
from bs4 import BeautifulSoup
import os
import re
import json
from datetime import datetime

# --- DATEN AUS GITHUB SECRETS ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

LIMIT_PERCENT = 0.5  
DB_FILE = "last_prices.json"

AKTIEN_DATEN = {
    "A1E0HS": ("Silber-ETC", "DE000A1E0HS6"),
    "A1E0HR": ("Gold-ETC", "DE000A1E0HR8"),
    "338643": ("Strategy", "US5949721099"),
    "918422": ("NVIDIA", "US67066G1040"),
    "906866": ("Amazon", "US0231351067"),
    "723610": ("Siemens", "DE0007236101"),
    "A0NC7B": ("Visa", "US92826C8394"),
    "581005": ("Deutsche Boerse", "DE0005810055"),
    "840400": ("Allianz", "DE0008404005"),
    "A3DCXB": ("Constellation Energy", "US21037T1097"),
    "LSOBTC": ("Bitcoin", "LS000LSOBTC1"),
    "870747": ("Microsoft", "US5949181045")
}

def load_old_prices():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_prices(prices):
    with open(DB_FILE, "w") as f:
        json.dump(prices, f)

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload, timeout=10)
    except:
        print("Fehler beim Senden an Telegram")

def get_numbers(soup):
    # Sucht in den typischen L&S Preis-Containern
    container = soup.select_one(".price, .mono, .instrument-price, #pro_kurs")
    if container:
        text = container.get_text(strip=True)
        # Regex sucht nach Zahlenformat: 1.234,56 oder 123,456
        # Wir entfernen Tausenderpunkte, falls vorhanden
        text = text.replace(".", "").replace(" ", "")
        match = re.search(r"(\d+,\d+)", text)
        if match:
            return match.group(1)
    return None

# --- MAIN ---
old_prices = load_old_prices()
new_prices = old_prices.copy()
zeit = datetime.now().strftime("%H:%M:%S")

print(f"🚀 Check gestartet um {zeit}...")

for wkn, info in AKTIEN_DATEN.items():
    name, isin = info
    kurs_gefunden = False
    
    # Probiere erst ISIN, dann WKN (US-Werte brauchen oft WKN, DE-Werte ISIN)
    for identifier in [isin, wkn]:
        url = f"https://www.ls-tc.de/de/aktie/{identifier}"
        try:
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                kurs_str = get_numbers(soup)
                
                if kurs_str:
                    aktueller_kurs = float(kurs_str.replace(",", "."))
                    letzter_alarm_kurs = old_prices.get(wkn)

                    if letzter_alarm_kurs is None:
                        new_prices[wkn] = aktueller_kurs
                        print(f"✅ Initialwert {name}: {aktueller_kurs} EUR")
                    else:
                        diff_prozent = ((aktueller_kurs - letzter_alarm_kurs) / letzter_alarm_kurs) * 100
                        print(f"📊 {name}: {aktueller_kurs} EUR ({diff_prozent:+.2f}%)")

                        if abs(diff_prozent) >= LIMIT_PERCENT:
                            emoji = "🚀" if diff_prozent > 0 else "⚠️"
                            nachricht = (f"{emoji} <b>MOMENTUM ALARM</b>\n\n"
                                         f"Aktie: <b>{name}</b>\n"
                                         f"Neuer Kurs: <b>{aktueller_kurs:.2f} EUR</b>\n"
                                         f"Änderung: <b>{diff_prozent:+.2f}%</b>")
                            send_telegram(nachricht)
                            new_prices[wkn] = aktueller_kurs
                    
                    kurs_gefunden = True
                    break # Identifier-Loop verlassen, da Kurs gefunden
        except Exception as e:
            continue
            
    if not kurs_gefunden:
        print(f"❌ Kurs für {name} ({wkn}) konnte nicht gefunden werden.")

save_prices(new_prices)
print("🏁 Check beendet.")
