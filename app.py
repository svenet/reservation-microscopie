#!/usr/bin/python3
import streamlit as st
import sqlite3
import pandas as pd
import yaml
import streamlit_authenticator as stauth
from datetime import datetime, date
from streamlit_calendar import calendar  # Composant FullCalendar

# --- 1. Authentification admin uniquement ---
with open('config.yaml') as f:
    config = yaml.safe_load(f)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# --- 2. Initialisation de la base SQLite ---
conn = sqlite3.connect('reservations.db', check_same_thread=False)
c = conn.cursor()
# Création des tables si nécessaire
c.execute('''
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE
    )
''')
c.execute('''
    CREATE TABLE IF NOT EXISTS reservations (
        id INTEGER PRIMARY KEY,
        room_id INTEGER,
        start_date TEXT,
        end_date TEXT,
        user TEXT,
        project TEXT,
        status TEXT,
        initial_days INTEGER,
        actual_days INTEGER,
        FOREIGN KEY(room_id) REFERENCES rooms(id)
    )
''')

# Insérer ou renommer les salles
c.execute("SELECT COUNT(*) FROM rooms")
if c.fetchone()[0] == 0:
    c.execute("INSERT INTO rooms (name) VALUES (?)", ("Salle Raman - Witec",))
    c.execute("INSERT INTO rooms (name) VALUES (?)", ("Salle microscope inversé - Nikon",))
else:
    c.execute("UPDATE rooms SET name=? WHERE id=1", ("Salle Raman - Witec",))
    c.execute("UPDATE rooms SET name=? WHERE id=2", ("Salle microscope inversé - Nikon",))
conn.commit()

# --- 3. Navigation multi-pages ---
st.sidebar.title("Menu")
pages = ["Réserver", "Annuler", "Calendrier", "Statistiques"]
choice = st.sidebar.selectbox("", pages)

# Fonction utilitaire : lire les réservations en DataFrame
@st.cache_data
def load_reservations():
    df = pd.read_sql("SELECT * FROM reservations", conn, parse_dates=['start_date','end_date'])
    return df

# --- 4. Pages accessibles sans authentification ---
if choice in ["Réserver", "Annuler", "Calendrier"]:
    if choice == "Réserver":
        st.header("Réserver une salle")
        # Chargement des salles
        rooms = pd.read_sql("SELECT * FROM rooms", conn)
        room = st.selectbox("Salle", rooms['name'])
        user = st.text_input("Nom utilisateur / projet")
        start = st.date_input("Date de début", date.today())
        end = st.date_input("Date de fin", date.today())
        if st.button("Réserver"):
            rid = rooms.loc[rooms['name']==room, 'id'].iloc[0]
            days = (end - start).days + 1
            c.execute('''
                INSERT INTO reservations
                (room_id, start_date, end_date, user, project, status, initial_days, actual_days)
                VALUES (?,?,?,?,?,'active',?,?)
            ''', (rid, start.isoformat(), end.isoformat(), user, user, days, days))
            conn.commit()
            st.success("✅ Réservation enregistrée")

    elif choice == "Annuler":
        st.header("Annuler une réservation")
        df_actives = load_reservations()[lambda d: d.status=='active']
        if df_actives.empty:
            st.info("Aucune réservation active à annuler.")
        else:
            options = df_actives.apply(lambda r: f"{r.id} – {r.user} ({r.start_date.date()}→{r.end_date.date()})", axis=1)
            sel = st.selectbox("Sélectionnez", options)
            if sel:
                res_id = int(sel.split(" –")[0])
                used = st.date_input("Date réelle d'arrêt", date.today())
                if st.button("Annuler"):
                    start_str = c.execute("SELECT start_date FROM reservations WHERE id=?", (res_id,)).fetchone()[0]
                    start_dt = datetime.fromisoformat(start_str).date()
                    actual = (used - start_dt).days + 1
                    c.execute("UPDATE reservations SET status='cancelled', actual_days=? WHERE id=?", (actual, res_id))
                    conn.commit()
                    st.warning("⚠️ Réservation annulée")

    elif choice == "Calendrier":
        st.header("Calendrier des réservations")
        df = load_reservations()
        events = []
        for _, r in df.iterrows():
            color = '#d9534f' if r.status=='active' else '#5bc0de'
            events.append({
                'id': r.id,
                'title': f"{r.project} ({r.status})",
                'start': r.start_date.date().isoformat(),
                'end': (r.end_date + pd.Timedelta(days=1)).date().isoformat(),
                'eventBackgroundColor': color,
                'eventBorderColor': color
            })
        calendar(events, height=600)

# --- 5. Page Statistiques (admin uniquement) ---
elif choice == "Statistiques":
    authenticator.login('Login', 'sidebar')
    if st.session_state.get("authentication_status") is True:
        st.sidebar.write(f"Bienvenue, {st.session_state['name']}")
        authenticator.logout('Déconnexion', 'sidebar')
        st.header("Statistiques d’occupation")
        df = load_reservations()
        stats = df.groupby(['room_id','status']).agg({
            'initial_days':'sum', 'actual_days':'sum'
        }).reset_index()
        rooms = pd.read_sql("SELECT id,name FROM rooms", conn)
        for rid, grp in stats.groupby('room_id'):
            name_room = rooms.loc[rooms.id==rid,'name'].
::contentReference[oaicite:6]{index=6}
 
