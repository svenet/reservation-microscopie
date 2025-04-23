!/usr/bin/python3
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, time
from st_aggrid import AgGrid
from streamlit_calendar import calendar

# --- Connexion à la base de données SQLite ---
conn = sqlite3.connect('reservations.db', check_same_thread=False)
c = conn.cursor()

# --- Création des tables si elles n'existent pas ---
c.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
""")

c.execute("""
    CREATE TABLE IF NOT EXISTS reservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER,
        start_date TEXT,
        end_date TEXT,
        start_time TEXT,
        end_time TEXT,
        user TEXT,
        project TEXT,
        status TEXT,
        initial_days INTEGER,
        actual_days INTEGER,
        created_at TEXT,
        cancelled_at TEXT,
        FOREIGN KEY (room_id) REFERENCES rooms(id)
    )
""")
conn.commit()

# --- Ajout des salles si la table est vide ---
c.execute("SELECT COUNT(*) FROM rooms")
if c.fetchone()[0] == 0:
    c.executemany("INSERT INTO rooms (name) VALUES (?)", [
        ("Salle Raman - Witec",),
        ("Salle microscope inversé - Nikon",)
    ])
    conn.commit()

# --- Fonction pour charger les réservations ---
@st.cache_data
def load_reservations():
    return pd.read_sql("SELECT * FROM reservations", conn,
                       parse_dates=['start_date', 'end_date', 'created_at', 'cancelled_at'])

# --- Menu latéral ---
st.sidebar.title("Menu")
choice = st.sidebar.radio("Navigation", ["Réserver", "Annuler", "Calendrier", "Récapitulatif"])

# --- Page de réservation ---
if choice == "Réserver":
    st.header("Réserver une salle")
    rooms_df = pd.read_sql("SELECT * FROM rooms", conn)
    room = st.selectbox("Salle", rooms_df['name'])
    user = st.text_input("Nom de l'utilisateur / Projet")
    start = st.date_input("Date de début", date.today())
    end = st.date_input("Date de fin", date.today())
    stime = st.time_input("Heure de début", time(8, 0))
    etime = st.time_input("Heure de fin", time(12, 0))
    if st.button("Réserver"):
        rid = rooms_df.loc[rooms_df['name'] == room, 'id'].iloc[0]
        days = (end - start).days + 1
        now = datetime.now().isoformat()
        c.execute("""
            INSERT INTO reservations (
                room_id, start_date, end_date, start_time, end_time,
                user, project, status, initial_days, actual_days,
                created_at, cancelled_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
        """, (
            rid, start.isoformat(), end.isoformat(),
            stime.strftime('%H:%M:%S'), etime.strftime('%H:%M:%S'),
            user, user, 'active', days, days, now
        ))
        conn.commit()
        st.success("✅ Réservation enregistrée")

# --- Page d'annulation ---
elif choice == "Annuler":
    st.header("Annuler une réservation")
    df = load_reservations()
    active = df[df.status == 'active']
    if active.empty:
        st.info("Aucune réservation active.")
    else:
        options = active.apply(lambda r: f"{r.id} – {r.user} ({r.start_date.date()} → {r.end_date.date()})", axis=1)
        selection = st.selectbox("Sélectionner une réservation", options)
        if selection and st.button("Annuler"):
            rid = int(selection.split(" –")[0])
            used = st.date_input("Date réelle d'arrêt", date.today())
            sd = datetime.fromisoformat(
                c.execute("SELECT start_date FROM reservations WHERE id = ?", (rid,)).fetchone()[0]
            ).date()
            actual = (used - sd).days + 1
            canc = datetime.now().isoformat()
            c.execute("""
                UPDATE reservations
                SET status = 'cancelled', actual_days = ?, cancelled_at = ?
                WHERE id = ?
            """, (actual, canc, rid))
            conn.commit()
            st.warning("⚠️ Réservation annulée")

# --- Page du calendrier ---
elif choice == "Calendrier":
    st.header("Disponibilités – Vue hebdomadaire (08h–12h & 14h–18h)")

    df = load_reservations()
    df = df[df.status == 'active']

    # Préparation des événements pour chaque salle
    events_by_room = {}
    rooms = pd.read_sql("SELECT id, name FROM rooms", conn)
    for rid, name in zip(rooms.id, rooms.name):
        events = []
        for _, r in df[df.room_id == rid].iterrows():
            events.append({
                "title": "Occupé",
                "start": f"{r.start_date.date().isoformat()}T{r.start_time}",
                "end": f"{r.end_date.date().isoformat()}T{r.end_time}"
            })
        events_by_room[rid] = events

    # Options du calendrier
    options = {
        "initialView": "timeGridWeek",
        "slotMinTime": "08:00:00",
        "slotMaxTime": "18:00:00",
        "slotDuration": "04:00:00",
        "slotLabelInterval": "04:00:00",
        "businessHours": [
            {"daysOfWeek": [1, 2, 3, 4, 5], "startTime": "08:00", "endTime": "12:00"},
            {"daysOfWeek": [1, 2, 3, 4, 5], "startTime": "14:00", "endTime": "18:00"}
        ],
        "allDaySlot": False,
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "timeGridWeek"
        }
    }

    # Affichage des calendriers empilés
    for rid in rooms.id:
        st.subheader(rooms.loc[rooms.id == rid, 'name'].iloc[0])
        calendar(events=events_by_room[rid], options=options)
 
