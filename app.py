#!/usr/bin/python3
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
from streamlit_calendar import calendar

# --- Connexion à la base de données ---
conn = sqlite3.connect('reservations.db', check_same_thread=False)
c = conn.cursor()

# --- Création des tables si besoin ---
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

# --- Initialisation des salles si vide ---
c.execute("SELECT COUNT(*) FROM rooms")
if c.fetchone()[0] == 0:
    c.execute("INSERT INTO rooms (name) VALUES (?)", ("Salle Raman - Witec",))
    c.execute("INSERT INTO rooms (name) VALUES (?)", ("Salle microscope inversé - Nikon",))
conn.commit()

# --- Menu de navigation ---
st.sidebar.title("Menu")
pages = ["Réserver", "Annuler", "Calendrier", "Statistiques (admin)"]
choice = st.sidebar.radio("Navigation", pages)

# --- Fonction utilitaire : chargement des réservations ---
@st.cache_data
def load_reservations():
    return pd.read_sql("SELECT * FROM reservations", conn, parse_dates=['start_date', 'end_date'])

# --- Page Réserver ---
if choice == "Réserver":
    st.header("Réserver une salle")
    rooms = pd.read_sql("SELECT * FROM rooms", conn)
    room = st.selectbox("Salle", rooms['name'])
    user = st.text_input("Nom utilisateur / projet")
    start = st.date_input("Date de début", date.today())
    end = st.date_input("Date de fin", date.today())

    if st.button("Réserver"):
        rid = rooms.loc[rooms['name'] == room, 'id'].iloc[0]
        days = (end - start).days + 1
        c.execute('''
            INSERT INTO reservations
            (room_id, start_date, end_date, user, project, status, initial_days, actual_days)
            VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
        ''', (rid, start.isoformat(), end.isoformat(), user, user, days, days))
        conn.commit()
        st.success("✅ Réservation enregistrée")

# --- Page Annuler ---
elif choice == "Annuler":
    st.header("Annuler une réservation")
    df = load_reservations()
    df_active = df[df['status'] == 'active']
    if not df_active.empty:
        options = df_active.apply(lambda r: f"{r.id} – {r.user} ({r.start_date.date()}→{r.end_date.date()})", axis=1)
        sel = st.selectbox("Sélectionnez une réservation", options)
        if sel:
            res_id = int(sel.split(" –")[0])
            used = st.date_input("Date réelle d'arrêt", date.today())
            start_str = c.execute("SELECT start_date FROM reservations WHERE id=?", (res_id,)).fetchone()[0]
            start_dt = datetime.fromisoformat(start_str).date()
            actual = (used - start_dt).days + 1
            c.execute("UPDATE reservations SET status='cancelled', actual_days=? WHERE id=?", (actual, res_id))
            conn.commit()
            st.warning("⚠️ Réservation annulée")
    else:
        st.info("Aucune réservation active à annuler.")

# --- Page Calendrier ---
elif choice == "Calendrier":
    st.header("Calendrier des réservations")
    df = load_reservations()
    rooms = pd.read_sql("SELECT * FROM rooms", conn)
    events = []

    for _, r in df.iterrows():
        room_name = rooms[rooms.id == r.room_id].name.values[0]
        events.append({
            'title': f"{r.project} ({room_name})",
            'start': r.start_date.date().isoformat(),
            'end': (r.end_date + pd.Timedelta(days=1)).date().isoformat(),
            'color': '#28a745' if r.status == 'active' else '#6c757d'
        })

    calendar(events=events, height=600)

# --- Page Statistiques admin ---
elif choice == "Statistiques (admin)":
    st.header("Statistiques d’occupation (admin)")

    # Authentification simple
    pwd = st.text_input("Mot de passe admin", type="password")
    if pwd != "WeierStrass_!1":
        st.error("🔒 Accès refusé")
        st.stop()

    df = load_reservations()
    stats = df.groupby(['room_id', 'status']).agg({
        'initial_days': 'sum',
        'actual_days': 'sum'
    }).reset_index()

    rooms = pd.read_sql("SELECT * FROM rooms", conn)
    for rid, grp in stats.groupby('room_id'):
        name_room = rooms.loc[rooms.id == rid, 'name'].iloc[0]
        init = int(grp['initial_days'].sum())
        used = int(grp['actual_days'].sum())
        rate = used / init * 100 if init > 0 else 0

        st.subheader(name_room)
        st.write(f"- Jours réservés initiaux : {init}")
        st.write(f"- Jours réellement utilisés : {used}")
        st.write(f"- Taux d’occupation : {rate:.1f}%")
