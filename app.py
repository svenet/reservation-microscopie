#!/usr/bin/python3
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, time

# --- Connexion base de données ---
conn = sqlite3.connect('reservations.db', check_same_thread=False)
c = conn.cursor()

# --- Création tables ---
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

# --- Ajout salles si vide ---
c.execute("SELECT COUNT(*) FROM rooms")
if c.fetchone()[0] == 0:
    c.executemany("INSERT INTO rooms (name) VALUES (?)", [
        ("Salle Raman - Witec",),
        ("Salle microscope inversé - Nikon",)
    ])
    conn.commit()

# --- Charger les réservations ---
@st.cache_data
def load_reservations():
    return pd.read_sql("SELECT * FROM reservations", conn,
                       parse_dates=['start_date', 'end_date', 'created_at', 'cancelled_at'])

# --- Vérification conflits ---
def check_conflict(room_id, start_date, start_time, end_date, end_time):
    c.execute("""
        SELECT * FROM reservations
        WHERE room_id = ? AND status = 'active' AND (
            (start_date <= ? AND end_date >= ? AND start_time < ? AND end_time > ?)
        )
    """, (room_id, end_date, start_date, end_time, start_time))
    return c.fetchall()

# --- Menu ---
st.sidebar.title("Menu")
choice = st.sidebar.radio("Navigation", ["Réserver", "Annuler", "Calendrier", "Récapitulatif"])

# --- Réservation ---
if choice == "Réserver":
    st.header("Réserver une salle")
    rooms_df = pd.read_sql("SELECT * FROM rooms", conn)
    room = st.selectbox("Salle", rooms_df['name'])
    user = st.text_input("Nom de l'utilisateur / Projet")
    start = st.date_input("Date de début", date.today())
    stime = st.time_input("Heure de début", time(8, 0))
    end = st.date_input("Date de fin", date.today())
    etime = st.time_input("Heure de fin", time(18, 0))

    if st.button("Réserver"):
        rid = rooms_df.loc[rooms_df['name'] == room, 'id'].iloc[0]
        if check_conflict(rid, start.isoformat(), stime.strftime('%H:%M:%S'), end.isoformat(), etime.strftime('%H:%M:%S')):
            st.error("❌ Ce créneau est déjà réservé.")
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

# --- Annulation ---
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
            actual_end_date = st.date_input("Date réelle d'arrêt", date.today())
            sd = datetime.fromisoformat(c.execute("SELECT start_date FROM reservations WHERE id = ?", (rid,)).fetchone()[0]).date()
            actual_days = (actual_end_date - sd).days + 1
            canc = datetime.now().isoformat()
            c.execute("""
                UPDATE reservations
                SET status = 'cancelled', actual_days = ?, cancelled_at = ?
                WHERE id = ?
            """, (actual_days, canc, rid))
            conn.commit()
            st.warning("⚠️ Réservation annulée avec succès.")

