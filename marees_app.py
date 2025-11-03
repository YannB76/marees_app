import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
from math import sin, cos, pi
import io
from PIL import Image
import streamlit as st

# -----------------------------------------------------
# 🔧 CONFIGURATION
# -----------------------------------------------------
LAT, LON = 49.4938, 0.1077  # Le Havre

st.set_page_config(
    page_title="🌊 Marées, Soleil, Météo & Lune - Le Havre",
    page_icon="🌊",
    layout="wide"
)

st.title("🌅 Prévisions Marées, Soleil, Météo & Lune - Le Havre")
st.caption(f"Prévisions sur 3 jours – {datetime.now().strftime('%d/%m/%Y')}")


# -----------------------------------------------------
# 🧭 SCRAPER MAREE.INFO (corrigé)
# -----------------------------------------------------
def scrape_maree_le_havre():
    url = "https://maree.info/19"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")

    table = next((t for t in soup.find_all("table") if "Date" in t.get_text() and "Heure" in t.get_text()), None)
    if not table:
        return {}

    results, current_date = {}, None
    for row in table.find_all("tr"):
        cols = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
        if not cols:
            continue
        # Ignore les en-têtes
        if "Date" in cols[0] and "Heure" in " ".join(cols):
            continue

        # Nouvelle date
        if cols[0]:
            current_date = cols[0].strip()
            results[current_date] = []

        # Données horaires
        if len(cols) >= 4 and current_date:
            heures = re.findall(r"\d{2}h\d{2}", cols[1])
            hauteurs = re.findall(r"\d,\d+m", cols[2])
            coeffs = re.findall(r"\d{2,3}", cols[3])
            for i in range(max(len(heures), len(hauteurs))):
                heure = heures[i] if i < len(heures) else "?"
                hauteur = hauteurs[i] if i < len(hauteurs) else "?"
                coeff = coeffs[i] if i < len(coeffs) else ""
                type_maree = "Pleine mer" if i % 2 else "Basse mer"
                results[current_date].append((heure, hauteur, coeff, type_maree))

    # ✅ Correction : gestion du mois + limite à 3 jours
    today = datetime.now().date()
    final_results = {}
    mois_noms = ["janv", "févr", "mars", "avril", "mai", "juin",
                 "juil", "août", "sept", "oct", "nov", "déc"]
    for d, v in results.items():
        match = re.search(r"(\d{1,2})\s+([A-Za-zéû]+)", d)
        if match:
            jour = int(match.group(1))
            mois_str = match.group(2).lower()
            mois_num = next((i + 1 for i, m in enumerate(mois_noms) if m in mois_str), None)
            if mois_num:
                date_obj = datetime(today.year, mois_num, jour).date()
                if 0 <= (date_obj - today).days <= 2:
                    final_results[d] = v
    return final_results


# -----------------------------------------------------
# 🌤️ MÉTÉO + SOLEIL + VENT
# -----------------------------------------------------
def get_forecasts(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        "&daily=weathercode,temperature_2m_max,temperature_2m_min,"
        "sunrise,sunset,windspeed_10m_max,winddirection_10m_dominant"
        "&forecast_days=3&timezone=Europe/Paris"
    )
    data = requests.get(url).json()
    res = []
    for i, day in enumerate(data["daily"]["time"]):
        res.append({
            "date": day,
            "sunrise": data["daily"]["sunrise"][i].split("T")[1],
            "sunset": data["daily"]["sunset"][i].split("T")[1],
            "tmax": data["daily"]["temperature_2m_max"][i],
            "tmin": data["daily"]["temperature_2m_min"][i],
            "code": data["daily"]["weathercode"][i],
            "wind": data["daily"]["windspeed_10m_max"][i],
            "dir": data["daily"]["winddirection_10m_dominant"][i],
        })
    return res


# -----------------------------------------------------
# 🌕 LUNE (calcul local + image réaliste)
# -----------------------------------------------------
def get_moon_data():
    def moon_phase(date):
        diff = date - datetime(2001, 1, 1)
        days = diff.days + (diff.seconds / 86400)
        lunations = 0.20439731 + (days * 0.03386319269)
        return lunations % 1

    today = datetime.now().date()
    moon_data = {}
    for i in range(3):
        d = today + timedelta(days=i)
        phase = moon_phase(datetime.combine(d, datetime.min.time()))
        luminance = round(100 * (1 - cos(2 * pi * phase)) / 2, 1)
        moon_data[d.isoformat()] = (phase, luminance)
    return moon_data


def moon_phase_text(phase):
    if phase < 0.03 or phase > 0.97:
        return "🌑 Nouvelle lune"
    elif 0.03 <= phase < 0.25:
        return "🌒 Lune croissante"
    elif 0.25 <= phase < 0.48:
        return "🌓 Premier quartier"
    elif 0.48 <= phase < 0.52:
        return "🌕 Pleine lune"
    elif 0.52 <= phase < 0.75:
        return "🌖 Gibbeuse décroissante"
    elif 0.75 <= phase < 0.97:
        return "🌗 Dernier quartier"
    else:
        return "🌘 Phase inconnue"


import io
import requests
from PIL import Image, ImageEnhance

def generate_moon_image(luminance):
    """Retourne une image réaliste de la lune éclairée selon le pourcentage"""
    try:
        # Téléchargement sécurisé de l'image de base
        url = "https://upload.wikimedia.org/wikipedia/commons/5/56/Moon.jpg"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        img_data = io.BytesIO(response.content)
        moon = Image.open(img_data).convert("RGB").resize((100, 100))

        # Ajuster la luminosité selon l’illumination
        enhancer = ImageEnhance.Brightness(moon)
        brightness = 0.4 + (luminance / 100) * 0.6
        moon_img = enhancer.enhance(brightness)

        return moon_img
    except Exception as e:
        print(f"Erreur chargement image lune : {e}")
        # Image de secours en cas d’erreur
        fallback = Image.new("RGB", (100, 100), color=(30, 30, 30))
        return fallback



# -----------------------------------------------------
# 🧭 UTILITAIRES
# -----------------------------------------------------
def get_weather_text(code):
    if code in [0]: return "☀️ Ensoleillé"
    elif code in [1, 2, 3]: return "🌤️ Partiellement nuageux"
    elif code in [45, 48]: return "🌫️ Brouillard"
    elif code in [51, 53, 55, 56, 57]: return "🌦️ Bruine"
    elif code in [61, 63, 65, 80, 81, 82]: return "🌧️ Pluie"
    elif code in [66, 67, 71, 73, 75, 77, 85, 86]: return "❄️ Neige"
    elif code in [95, 96, 99]: return "⛈️ Orage"
    else: return "❔"


def direction_to_cardinal(deg):
    dirs = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
    return dirs[int((deg + 22.5) / 45) % 8]


# -----------------------------------------------------
# 🚀 AFFICHAGE STREAMLIT
# -----------------------------------------------------
forecast = get_forecasts(LAT, LON)
moon_data = get_moon_data()
marees = scrape_maree_le_havre()

cols = st.columns(3)
for i, day in enumerate(forecast):
    with cols[i]:
        date_str = datetime.strptime(day["date"], "%Y-%m-%d").strftime("%A %d/%m")
        st.subheader(date_str)

        # Soleil
        st.write("🌞 **Lever du soleil :**", day["sunrise"])
        st.write("🌇 **Coucher du soleil :**", day["sunset"])

        st.divider()

        # Lune
        phase_value, luminance = moon_data.get(day["date"], (0, 0))
        moon_text = moon_phase_text(phase_value)
        st.write(f"🌕 **{moon_text} – {luminance:.0f}% éclairée**")
        st.image(generate_moon_image(luminance))

        st.divider()

        # Météo
        weather_text = get_weather_text(day["code"])
        st.write(weather_text)
        st.write(f"🌡️ {day['tmin']}°C – {day['tmax']}°C")
        st.write(f"💨 {day['wind']} km/h ({direction_to_cardinal(day['dir'])})")

        st.divider()

        # Marées
        maree_keys = list(marees.keys())
        if i < len(maree_keys):
            for (h, ht, cf, t) in marees[maree_keys[i]]:
                st.write(f"{t} à {h} → {ht} (Coeff {cf})")
        else:
            st.info("🌊 Données marées indisponibles.")
