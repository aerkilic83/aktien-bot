import requests
from bs4 import BeautifulSoup
import os
import re
import json
from datetime import datetime

# --- DATEN AUS GITHUB SECRETS ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Schwellenwert für Momentum (z.B. 0.5%)
LIMIT_PERCENT = 0.5  
DB_FILE = "last_prices.json"

AKTIEN_DATEN = {
    "A1E0HS": ("Silber-ETC", "DE000A1E0HS6"),
    "A1E0HR": ("Gold-ETC", "DE000A1E0HR8"),
    "338643": ("Strategy", "US5949721099"),
    "918422": ("NVIDIA", "US67066G1040"),
    "871460": ("Oracle", "US68389X1054"),
    "A2QA4J": ("Palantir", "US69608A1088"),
    "A0NC7B": ("Visa", "US92826C8394"),
    "581005": ("Deutsche Boerse", "DE0005810055") 
}

def load_old_prices():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_prices(prices):
    with open(DB_FILE, "w") as f:
        json.dump(prices, f)

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": msg, 
        "parse_mode": "HTML",
        "disable_notification": False 
    }
    requests.post(url, data=payload)

def get_numbers(soup):
    container = soup.select_one(".price, .mono, .instrument-price")
    if container:
        text = container.get_text(strip=True).replace("€", "").replace("%", "")
        text = re.sub(r'\.(?=\d+,\d+)', '', text)
        return re.findall(r"[+-]?\d+,\d+", text)
    return None

# 1. Alte Kurse laden
old_prices = load_old_prices()
new_prices = old_prices.copy()
zeit = datetime.now().strftime("%H:%M:%S")

print(f"🚀 Check gestartet um {zeit}...")

for wkn, info in AKTIEN_DATEN.items():
    name, isin = info
    url = f"https://www.ls-tc.de/de/aktie/{wkn}"
    
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        daten = get_numbers(soup)
        
        if daten and len(daten) >= 1:
            # Aktuellen Kurs extrahieren (Komma zu Punkt für Berechnung)
            aktueller_kurs = float(daten[0].replace(",", "."))
            letzter_alarm_kurs = old_prices.get(wkn)

            if letzter_alarm_kurs is None:
                # Erster Durchlauf für diese Aktie überhaupt
                new_prices[wkn] = aktueller_kurs
                print(f"Erster Wert für {name}: {aktueller_kurs} EUR")
            else:
                # Momentum Berechnung
                diff_prozent = ((aktueller_kurs - letzter_alarm_kurs) / letzter_alarm_kurs) * 100
                
                print(f"{name}: {aktueller_kurs} EUR (Diff zu letztem Alarm: {diff_prozent:+.2f}%)")

                if abs(diff_prozent) >= LIMIT_PERCENT:
                    emoji = "🚀" if diff_prozent > 0 else "⚠️"
                    nachricht = (f"{emoji} <b>MOMENTUM ALARM</b>\n\n"
                                 f"Aktie: <b>{name}</b>\n"
                                 f"Neuer Kurs: <b>{aktueller_kurs:.2f} EUR</b>\n"
                                 f"Änderung: <b>{diff_prozent:+.2f}%</b> seit letzter Meldung")
                    
                    send_telegram(nachricht)
                    # Neuen Referenzpunkt setzen
                    new_prices[wkn] = aktueller_kurs
                    print(f"🔔 Alarm gesendet für {name}")

    except Exception as e:
        print(f"Fehler bei {name}: {e}")

# 2. Neue Referenzwerte speichern
save_prices(new_prices)
