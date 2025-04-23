#!/usr/bin/python3
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
        start_time TEXT,      
        end_date TEXT,
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

# --- Fonction de vérification des conflits de réservation ---
def check_conflict(room_id, start_date, start_time, end_date, end_time):
    c.execute("""
        SELECT * FROM reservations
        WHERE room_id = ? AND status = 'active' AND (
            (start_date = ? AND start_time < ? AND end_time > ?) OR
            (end_date = ? AND start_time < ? AND end_time > ?) OR
            (start_date > ? AND end_date < ?)
        )
    """, (room_id, start_date, start_time, start_time, end_date, start_time, end_time, start_date, end_date))
    return c.fetchall()

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
    stime = st.time_input("Heure de début", time(8, 0), step=3600)
    end = st.date_input("Date de fin", date.today())
    etime = st.time_input("Heure de fin", time(18, 0), step=3600)

    if st.button("Réserver"):
        rid = rooms_df.loc[rooms_df['name'] == room, 'id'].iloc[0]
        if check_conflict(rid, start.isoformat(), stime.strftime('%H:%M:%S'), end.isoformat(), etime.strftime('%H:%M:%S')):
            st.error("❌ Ce créneau est déjà réservé. Veuillez choisir un autre horaire.")
        else:
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

        if selection:
            rid = int(selection.split(" –")[0])
            rinfo = active[active.id == rid].iloc[0]
            actual_end_date = st.date_input("Date réelle d'arrêt", date.today(), min_value=rinfo.start_date.date(), max_value=rinfo.end_date.date())

            full_cancel = st.checkbox("Annuler la totalité de la réservation")

            if st.button("Annuler"):
                if full_cancel or actual_end_date == rinfo.start_date.date():
                    canc = datetime.now().isoformat()
                    c.execute("""
                        UPDATE reservations
                        SET status = 'cancelled', actual_days = 0, cancelled_at = ?
                        WHERE id = ?
                    """, (canc, rid))
                else:
                    # Mise à jour pour la partie maintenue
                    actual_days = (actual_end_date - rinfo.start_date.date()).days + 1
                    c.execute("""
                        UPDATE reservations
                        SET end_date = ?, actual_days = ?, cancelled_at = ?, status = 'cancelled'
                        WHERE id = ?
                    """, (actual_end_date.isoformat(), actual_days, datetime.now().isoformat(), rid))

                conn.commit()
                st.success("⚠️ Réservation mise à jour.")

# --- Page du calendrier ---
elif choice == "Calendrier":
    st.header("Disponibilités – Vue hebdomadaire (08h–12h & 14h–18h)")

    df = load_reservations()
    df = df[df.status == 'active']

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

    options = {
        "initialView": "timeGridWeek",
        "locale": "fr",
        "firstDay": 1,
        "slotMinTime": "08:00:00",
        "slotMaxTime": "18:00:00",
        "slotDuration": "05:00:00",
        "slotLabelInterval": "05:00:00",
        "slotLabelFormat": {
            "hour": "2-digit",
            "minute": "2-digit",
            "omitZeroMinute": False,
            "meridiem": False,
            "hour12": False
        },
        "businessHours": [
            {"daysOfWeek": [1, 2, 3, 4, 5, 6, 7], "startTime": "08:00", "endTime": "13:00"},
            {"daysOfWeek": [1, 2, 3, 4, 5, 6, 7], "startTime": "13:00", "endTime": "18:00"}
        ],
        "allDaySlot": False,
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "timeGridWeek"
        }
    }

    for rid in rooms.id:
        st.subheader(rooms.loc[rooms.id == rid, 'name'].iloc[0])
        calendar(events=events_by_room[rid], options=options)

# --- Page Récapitulatif ---
elif choice == "Récapitulatif":
    st.header("📋 Récapitulatif des réservations")
    df = load_reservations()
    rooms_df = pd.read_sql("SELECT * FROM rooms", conn)
    df['Salle'] = df['room_id'].map(dict(zip(rooms_df['id'], rooms_df['name'])))

    df_display = df[[
        'Salle', 'user', 'project', 'start_date', 'end_date',
        'start_time', 'end_time', 'status', 'created_at', 'cancelled_at'
    ]]
    df_display = df_display.rename(columns={
        'user': 'Utilisateur',
        'project': 'Projet',
        'start_date': 'Début',
        'end_date': 'Fin',
        'start_time': 'Heure début',
        'end_time': 'Heure fin',
        'status': 'Statut',
        'created_at': 'Réservé le',
        'cancelled_at': 'Annulé le'
    })

    AgGrid(
        df_display.sort_values(by='Début', ascending=False),
        height=500,
        fit_columns_on_grid_load=True
    )
