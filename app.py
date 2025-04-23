import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# Connexion à la base de données
conn = sqlite3.connect('reservations.db', check_same_thread=False)
c = conn.cursor()

# Création des tables si elles n'existent pas
c.execute('''
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS reservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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

# Insérer les salles si elles n'existent pas
c.execute("SELECT COUNT(*) FROM rooms")
if c.fetchone()[0] == 0:
    c.execute("INSERT INTO rooms (name) VALUES ('Salle 1'), ('Salle 2')")
    conn.commit()

st.title("Système de réservation de salles de microscopie")

menu = ["Réserver une salle", "Annuler une réservation", "Voir les réservations", "Statistiques"]
choice = st.sidebar.selectbox("Menu", menu)

# Récupérer les salles depuis la base de données
c.execute("SELECT * FROM rooms")
rooms = c.fetchall()
room_dict = {name: id for id, name in rooms}

if choice == "Réserver une salle":
    st.subheader("Réserver une salle")

    room_name = st.selectbox("Choisir une salle", list(room_dict.keys()))
    start_date = st.date_input("Date de début")
    end_date = st.date_input("Date de fin")
    user = st.text_input("Nom de l'utilisateur")
    project = st.text_input("Nom du projet")

    if st.button("Réserver"):
        room_id = room_dict[room_name]
        initial_days = (end_date - start_date).days + 1
        c.execute('''
            INSERT INTO reservations (room_id, start_date, end_date, user, project, status, initial_days, actual_days)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (room_id, start_date.isoformat(), end_date.isoformat(), user, project, 'active', initial_days, initial_days))
        conn.commit()
        st.success("Réservation effectuée avec succès.")

elif choice == "Annuler une réservation":
    st.subheader("Annuler une réservation")

    c.execute("SELECT id, user, project, start_date, end_date FROM reservations WHERE status = 'active'")
    reservations = c.fetchall()
    reservation_options = [f"{id} - {user} - {project} ({start_date} à {end_date})" for id, user, project, start_date, end_date in reservations]
    selected = st.selectbox("Sélectionner une réservation à annuler", reservation_options)

    if selected:
        res_id = int(selected.split(" - ")[0])
        used_end_date = st.date_input("Date réelle d'utilisation")

        # Récupérer la date de début
        c.execute("SELECT start_date FROM reservations WHERE id = ?", (res_id,))
        start_date_str = c.fetchone()[0]
        start_date = datetime.fromisoformat(start_date_str).date()
        actual_days = (used_end_date - start_date).days + 1

        if st.button("Annuler la réservation"):
            c.execute('''
                UPDATE reservations
                SET status = ?, actual_days = ?
                WHERE id = ?
            ''', ('cancelled', actual_days, res_id))
            conn.commit()
            st.success("Réservation annulée avec succès.")

elif choice == "Voir les réservations":
    st.subheader("Liste des réservations")

    c.execute('''
        SELECT r.id, rm.name, r.start_date, r.end_date, r.user,
