import streamlit as st
import requests
from datetime import date
from pathlib import Path

st.set_page_config(
    page_title="VoyagePlus - Planificateur Intelligent",
    page_icon="✈️",
    layout="wide"
)

st.markdown("""
<style>
.stApp { background-color: #F7EBDD; }
header {visibility: hidden;}
.main-container { padding: 0px 5% 50px 5%; }

.logo-container {
    padding: 20px 0;
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 24px;
    font-weight: 800;
    color: #2B2B2B;
}

.title {
    font-size: 52px;
    font-weight: 900;
    line-height: 1.1;
    color: #2B2B2B;
    margin-bottom: 20px;
}

.subtitle {
    font-size: 19px;
    color: #7A7A7A;
    margin-bottom: 40px;
    max-width: 500px;
    line-height: 1.5;
}

[data-testid="stVerticalBlock"] > div:has(div.form-card) {
    background-color: white;
    padding: 40px;
    border-radius: 25px;
    box-shadow: 0px 20px 40px rgba(0,0,0,0.05);
}

div[data-testid="stTextInput"] input,
div[data-testid="stDateInput"] input,
div[data-testid="stNumberInput"] input {
    background-color: #F8F9FA !important;
    border: 1px solid #E0E0E0 !important;
    border-radius: 12px !important;
    height: 48px;
}

.stButton > button {
    background-color: #FF9800 !important;
    color: white !important;
    font-size: 18px !important;
    font-weight: 700 !important;
    border-radius: 15px !important;
    padding: 25px !important;
    width: 100% !important;
    border: none !important;
    margin-top: 20px;
}

.stButton > button:hover {
    background-color: #FB8C00 !important;
    box-shadow: 0px 5px 15px rgba(255, 152, 0, 0.4);
}

[data-testid="stImage"] img { border-radius: 30px; }

.result-card {
    background-color: white;
    padding: 22px;
    border-radius: 18px;
    margin-bottom: 15px;
    box-shadow: 0px 4px 15px rgba(0,0,0,0.05);
}

.section-separator {
    background-color: white;
    height: 15px;
    margin: 40px -10% 40px -10%;
    border-top: 1px solid #EEE;
    border-bottom: 1px solid #EEE;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="logo-container">💼 VoyagePlus</div>', unsafe_allow_html=True)

st.markdown('<div class="main-container">', unsafe_allow_html=True)
col_left, col_right = st.columns([1.2, 1], gap="large")

with col_left:
    st.markdown('<div class="title">Planificateur de<br>voyage intelligent</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Créez votre voyage sur mesure en quelques clics. Laissez-nous vous accompagner dans l’organisation de vos plus belles aventures.</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        origin = st.text_input("Ville de départ", placeholder="Ex: Paris", value="Paris")
        destination = st.text_input("Destination", placeholder="Ex: Rome", value="Rome")

        c1, c2 = st.columns(2)
        with c1:
            start_date = st.date_input("Date de départ", value=date.today())
        with c2:
            end_date = st.date_input("Date de retour", value=date.today())

        budget = st.number_input("Budget total (€)", min_value=100, value=1500, step=50)
        search = st.button("Planifier mon voyage ✈️")
        st.markdown('</div>', unsafe_allow_html=True)

with col_right:
    st.image(str(Path(__file__).parent / "image" / "logo_PFE.jpg"), width="stretch")

st.markdown('</div>', unsafe_allow_html=True)

# =========================
# ACTION : RECHERCHE
# =========================
if search:
    payload = {
        "origin": origin,
        "destination": destination,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "budget": budget
    }

    with st.spinner("🔍 Analyse de votre demande et recherche des meilleures offres..."):
        try:
            response = requests.post("http://localhost:8000/run", json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()

            # =========================
            # DEBUG / ERREUR FLIGHT
            # =========================
            if data.get("error"):
                st.error(f"✈️ Flight error: {data['error']}")
                with st.expander("Voir la réponse complète (debug)"):
                    st.json(data)

            # =========================
            # VOL
            # =========================
            st.markdown(
                f'<div class="title" style="font-size:35px;">✈️ Vols pour {destination}</div>',
                unsafe_allow_html=True
            )

            flights = data.get("flights")
            if not isinstance(flights, dict):
                st.warning("Réponse 'flights' absente ou invalide.")
                with st.expander("Debug JSON"):
                    st.json(data)
            else:
                col_a, col_r = st.columns(2)

                with col_a:
                    st.markdown("### 🛫 Aller")
                    vols_aller = flights.get("aller", [])
                    if not vols_aller:
                        st.info("Aucun vol trouvé.")
                    for f in vols_aller:
                        st.markdown(f"""
                            <div class="result-card" style="border-left: 8px solid #FF9800;">
                                <div style="font-weight: 800; color: #FF9800; font-size: 1.1rem;">{f.get('airline', 'Compagnie')}</div>
                                <div style="color: #444; margin: 5px 0;">🕒 {f.get('departure_time')} → {f.get('arrival_time')}</div>
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
                                    <span style="font-size: 0.9rem; color: #777;">⏱️ {f.get('duration')}</span>
                                    <span style="font-weight: 700; font-size: 1.2rem; color: #2B2B2B;">{f.get('price')} EUR</span>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)

                with col_r:
                    st.markdown("### 🛬 Retour")
                    vols_retour = flights.get("retour", [])
                    if not vols_retour:
                        st.info("Aucun vol trouvé.")
                    for f in vols_retour:
                        st.markdown(f"""
                            <div class="result-card" style="border-left: 8px solid #2B2B2B;">
                                <div style="font-weight: 800; color: #2B2B2B; font-size: 1.1rem;">{f.get('airline', 'Compagnie')}</div>
                                <div style="color: #444; margin: 5px 0;">🕒 {f.get('departure_time')} → {f.get('arrival_time')}</div>
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
                                    <span style="font-size: 0.9rem; color: #777;">⏱️ {f.get('duration')}</span>
                                    <span style="font-weight: 700; font-size: 1.2rem; color: #2B2B2B;">{f.get('price')} EUR</span>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)

            # =========================
            # STAY
            # =========================
            st.markdown(
                f'<div class="title" style="font-size:35px;">🏨 Hébergements à {destination}</div>',
                unsafe_allow_html=True
            )

            stay_raw = data.get("stay", {})
            if isinstance(stay_raw, str):
                st.info(stay_raw)
                stays = []
            elif isinstance(stay_raw, dict):
                stays = stay_raw.get("stays", [])
            else:
                stays = stay_raw if isinstance(stay_raw, list) else []

            if stays:
                col_s1, col_s2 = st.columns(2)
                for idx, s in enumerate(stays):
                    col = col_s1 if idx % 2 == 0 else col_s2
                    with col:
                        stay_type = str(s.get('type', 'hotel')).replace('_', ' ').capitalize()
                        st.markdown(f"""
                            <div class="result-card" style="border-left: 8px solid #FF9800; min-height: 190px; display: flex; flex-direction: column; justify-content: space-between;">
                                <div>
                                    <div style="font-weight: 800; color: #2B2B2B; font-size: 1.2rem; margin-bottom: 2px;">{s.get('name', 'Hébergement')}</div>
                                    <div style="color: #FF9800; font-weight: 600; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 8px;">✨ {stay_type}</div>
                                    <div style="color: #7A7A7A; font-size: 0.9rem; line-height: 1.4;">📍 {s.get('address', 'Adresse en cours...')}</div>
                                </div>
                                <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-top: 15px;">
                                    <div style="color: #7A7A7A; font-size: 0.85rem;">{s.get('price_per_night_eur', 0)}€ / nuit</div>
                                    <div style="background-color: #FFF3E0; padding: 5px 15px; border-radius: 10px; border: 1px solid #FF9800;">
                                        <span style="font-weight: 800; font-size: 1.1rem; color: #E65100;">Total : {s.get('total_price_eur', 0)} EUR</span>
                                    </div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("Aucun hébergement trouvé dans ce budget.")

            # =========================
            # ACTIVITIES
            # =========================
            st.markdown(
                f'<div class="title" style="font-size:35px;">🎡 Activités à {destination}</div>',
                unsafe_allow_html=True
            )

            activities = data.get("activities", [])
            if isinstance(activities, list) and len(activities) > 0:
                ca1, ca2 = st.columns(2)
                for idx, a in enumerate(activities):
                    with (ca1 if idx % 2 == 0 else ca2):
                        disp_addr = a.get('address')
                        if not disp_addr or disp_addr == '—':
                            disp_addr = f"Centre-ville de {destination}"

                        st.markdown(f"""
                            <div class="result-card" style="border-left: 8px solid #FF9800; min-height: 180px; display: flex; flex-direction: column; justify-content: space-between;">
                                <div>
                                    <div style="font-weight: 800; color: #2B2B2B; font-size: 1.2rem;">{a.get('name')}</div>
                                    <div style="color: #FF9800; font-weight: 600; font-size: 0.85rem; text-transform: uppercase;">🎭 {a.get('category')}</div>
                                    <div style="color: #7A7A7A; font-size: 0.9rem;">📍 {disp_addr}</div>
                                </div>
                                <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-top:10px;">
                                    <span style="font-size: 0.8rem; color: #7A7A7A;">📏 {a.get('distance_km')} km</span>
                                    <div style="background-color: #FFF3E0; padding: 3px 10px; border-radius: 8px; border: 1px solid #FF9800; font-weight: 800; color: #E65100;">⭐ {a.get('score')}</div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
            else:
                st.warning("⚠️ Les services de localisation sont trop lents. Réessayez pour charger les adresses.")

            # =========================
            # WEATHER
            # =========================
            st.markdown(f'<div class="title" style="font-size:35px;">🌦️ Météo </div>', unsafe_allow_html=True)

            weather_data = data.get("weather", {}).get("weather", {}) if "weather" in data.get("weather", {}) else data.get("weather", {})
            if weather_data.get("error"):
                st.warning(weather_data["error"])
            elif weather_data:
                st.markdown(f"""
                    <div style="background-color: white; padding: 40px; border-radius: 25px; box-shadow: 0px 10px 30px rgba(0,0,0,0.05); display: flex; justify-content: space-around; align-items: center; flex-wrap: wrap;">
                        <div style="text-align: center;">
                            <div style="color: #7A7A7A; font-size: 0.9rem;">Température</div>
                            <div style="font-size: 3rem; font-weight: 900; color: #2B2B2B;">{weather_data.get('temperature', 'N/A')}</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="color: #7A7A7A; font-size: 0.9rem;">Humidité</div>
                            <div style="font-size: 3rem; font-weight: 900; color: #2B2B2B;">{weather_data.get('humidity', 'N/A')}</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="color: #7A7A7A; font-size: 0.9rem;">Condition</div>
                            <div style="font-size: 2rem; font-weight: 700; color: #FF9800;">{str(weather_data.get('condition', 'N/A')).capitalize()}</div>
                        </div>
                        <div style="max-width: 350px; background-color: #FFF3E0; padding: 25px; border-radius: 20px; border: 2px solid #FF9800;">
                            <b style="color: #E65100; font-size: 1.1rem;">💡 Conseil :</b><br>
                            <span style="font-size: 1.05rem; color: #444; line-height: 1.4;">{weather_data.get('tip', 'Bon voyage !')}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"❌ Erreur serveur : {e}. Le backend est peut-être saturé.")

st.markdown('</div>', unsafe_allow_html=True)
