import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
from math import cos, pi

LAT, LON = 49.4938, 0.1077  # Le Havre

# --- Configuration page ---
st.set_page_config(
    page_title="🌊 Marées, Soleil, Météo & Lune - Le Havre",
    page_icon="🌕",
    layout="wide"
)

st.title("🌊 Prévisions Marées, Soleil, Météo & Lune - Le Havre")
st.caption(f"Prévisions sur 3 jours – {datetime.now().strftime('%d/%m/%Y')}")


# --- Fonction météo ---
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


# --- Fonction marées ---
def scrape_maree_le_havre():
    url = "https://maree.info/19"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")
    table = next((t for t in soup.find_all("table") if "Date" in t.text and "Heure" in t.text), None)
    if not table:
        return {}

    results, current_date = {}, None
    for row in table.find_all("tr"):
        cols = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
        if not cols:
            continue
        if cols[0]:
            current_date = cols[0].replace(" ", "")
            results[current_date] = []
        if len(cols) >= 4:
            heures = re.findall(r"\d{2}h\d{2}", cols[1])
            hauteurs = re.findall(r"\d,\d+m", cols[2])
            coeffs = re.findall(r"\d{2,3}", cols[3])
            for i in range(max(len(heures), len(hauteurs))):
                heure = heures[i] if i < len(heures) else "?"
                hauteur = hauteurs[i] if i < len(hauteurs) else "?"
                coeff = coeffs[i] if i < len(coeffs) else ""
                type_maree = "Pleine mer" if i % 2 else "Basse mer"
                results[current_date].append((heure, hauteur, coeff, type_maree))
    today = datetime.now().day
    return {d: v for d, v in results.items() if re.search(r"\d+", d) and 0 <= int(re.findall(r'\d+', d)[0]) - today <= 2}


# --- Phase de la Lune ---
def get_moon_data():
    def moon_phase(date):
        diff = date - datetime(2001, 1, 1)
        days = diff.days + (diff.seconds / 86400)
        lunations = 0.20439731 + (days * 0.03386319269)
        return lunations % 1

    today = datetime.now().date()
    data = {}
    for i in range(3):
        d = today + timedelta(days=i)
        phase = moon_phase(datetime.combine(d, datetime.min.time()))
        luminance = round(100 * (1 - cos(2 * pi * phase)) / 2, 1)
        data[d.isoformat()] = (phase, luminance)
    return data


def moon_phase_text(phase):
    if phase < 0.03 or phase > 0.97:
        return "🌑 Nouvelle lune"
    elif 0.03 <= phase < 0.22:
        return "🌒 Croissante"
    elif 0.22 <= phase < 0.27:
        return "🌓 Premier quartier"
    elif 0.27 <= phase < 0.47:
        return "🌔 Gibbeuse croissante"
    elif 0.47 <= phase < 0.53:
        return "🌕 Pleine lune"
    elif 0.53 <= phase < 0.73:
        return "🌖 Gibbeuse décroissante"
    elif 0.73 <= phase < 0.78:
        return "🌗 Dernier quartier"
    else:
        return "🌘 Décroissante"


# --- Traduction météo ---
def get_weather_icon(code):
    if code in [0]: return "☀️ Ciel clair"
    elif code in [1, 2, 3]: return "🌤️ Partiellement nuageux"
    elif code in [45, 48]: return "🌫️ Brouillard"
    elif code in [51, 53, 55, 56, 57]: return "🌦️ Bruine"
    elif code in [61, 63, 65, 80, 81, 82]: return "🌧️ Pluie"
    elif code in [66, 67, 71, 73, 75, 77, 85, 86]: return "❄️ Neige"
    elif code in [95, 96, 99]: return "⛈️ Orage"
    else: return "❔"


# --- Données ---
forecast = get_forecasts(LAT, LON)
marees = scrape_maree_le_havre()
moon_data = get_moon_data()

cols = st.columns(3)
for i, day in enumerate(forecast):
    with cols[i]:
        date_str = datetime.strptime(day["date"], "%Y-%m-%d").strftime("%A %d/%m")
        st.subheader(date_str)
        st.image("https://cdn-icons-png.flaticon.com/512/869/869869.png", width=60)
        st.write(f"**Lever du soleil :** {day['sunrise']}  \n**Coucher du soleil :** {day['sunset']}")

        # Lune
        phase_value, luminance = moon_data.get(day["date"], (0, 0))
        st.markdown("---")
        st.write(f"{moon_phase_text(phase_value)} – **{luminance:.0f}% éclairée**")
        st.image("https://upload.wikimedia.org/wikipedia/commons/e/e1/FullMoon2010.jpg", width=90)

        # Météo
        st.markdown("---")
        st.write(get_weather_icon(day["code"]))
        st.write(f"🌡️ {day['tmin']}°C – {day['tmax']}°C")
        st.write(f"💨 {day['wind']} km/h")

        # Marées
        st.markdown("---")
        maree_keys = list(marees.keys())
        if i < len(maree_keys):
            for (h, ht, cf, t) in marees[maree_keys[i]]:
                st.write(f"• {t} à {h} → {ht} (Coeff {cf})" if cf else f"• {t} à {h} → {ht}")
        else:
            st.info("Données marées indisponibles.")
