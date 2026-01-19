import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import re
import os

# --- DEINE DATEN HIER EINTRAGEN ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

LIMIT_PERCENT = 0.5  # Schwellenwert für Alarm (z.B. 5%)

AKTIEN_DATEN = {
    "A1E0HS": ("Silber-ETC", "DE000A1E0HS6"),
    "A1E0HR": ("Gold-ETC", "DE000A1E0HR8"),
    "338643": ("Strategy", "US5949721099"),
    "918422": ("NVIDIA", "US67066G1040"),
    "871460": ("Oracle", "US68389X1054"),
    "A2QA4J": ("Palantir", "US69608A1088"),
    "A0NC7B": ("Visa", "US92826C8394")
}

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": msg, 
        "parse_mode": "HTML",
        "disable_notification": False  # Das erzwingt den Ton
    }
    requests.post(url, data=payload)

def get_numbers(soup):
    """Extrahiert Kursdaten sicher (auch für Strategy)"""
    container = soup.select_one(".price, .mono, .instrument-price")
    if container:
        text = container.get_text(strip=True).replace("€", "").replace("%", "")
        text = re.sub(r'\.(?=\d+,\d+)', '', text)
        return re.findall(r"[+-]?\d+,\d+", text)
    return None

# Speicher, um nicht jede Minute bei Alarm zugespamt zu werden
# (Speichert: WKN : Letztes Alarm-Datum)
last_alerts = {}

print("🚀 Ticker gestartet. Alarme werden per Telegram gesendet.")

zeit = datetime.now().strftime("%H:%M:%S")
heute = datetime.now().date()

for wkn, info in AKTIEN_DATEN.items():
    name, isin = info
    url = f"https://www.ls-tc.de/de/aktie/{wkn}" # Direkter Weg über WKN
    
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        daten = get_numbers(soup)
        
        if daten and len(daten) >= 3:
            p, a, pct = daten[0], daten[1], daten[2]
            
            # Prozentwert für Vergleich umwandeln (Komma zu Punkt)
            pct_val = abs(float(pct.replace(",", ".")))
            
            print(f"[{zeit}] {name}: {p} EUR ({pct}%)")
            
            # ALARM-LOGIK
            if pct_val >= LIMIT_PERCENT:
                    # Prüfen, ob wir für heute schon für diese Aktie gemeldet haben
                if last_alerts.get(wkn) != heute:
                    nachricht = (f"🚨 <b>AKTIEN ALARM</b>\n\n"
                                    f"Die Aktie <b>{name}</b> hat sich bewegt!\n"
                                    f"Kurs: {p} EUR\n"
                                    f"Änderung: <b>{pct}%</b>")
                    send_telegram(nachricht)
                    last_alerts[wkn] = heute
                    print(f"🔔 Telegram Alarm an dich gesendet!")
        
    except Exception as e:
        print(f"Fehler bei {name}: {e}")