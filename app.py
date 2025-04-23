#!/usr/bin/python3
import streamlit as st
import sqlite3
from st_aggrid import AgGrid
import pandas as pd
from datetime import datetime, date, time

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
conn.commit()

# --- Migration automatique du schéma existant ---------------
existing_cols = [row[1] for row in c.execute("PRAGMA table_info(reservations)").fetchall()]
if 'start_time'   not in existing_cols:
    c.execute("ALTER TABLE reservations ADD COLUMN start_time TEXT")
if 'end_time'     not in existing_cols:
    c.execute("ALTER TABLE reservations ADD COLUMN end_time TEXT")
if 'created_at'   not in existing_cols:
    c.execute("ALTER TABLE reservations ADD COLUMN created_at TEXT")
if 'cancelled_at' not in existing_cols:
    c.execute("ALTER TABLE reservations ADD COLUMN cancelled_at TEXT")
conn.commit()
# ------------------------------------------------------------

# --- Initialisation des salles si vide ---
c.execute("SELECT COUNT(*) FROM rooms")
if c.fetchone()[0] == 0:
    c.execute("INSERT INTO rooms (name) VALUES (?)", ("Salle Raman - Witec",))
    c.execute("INSERT INTO rooms (name) VALUES (?)", ("Salle microscope inversé - Nikon",))
    conn.commit()

# --- Navigation ---
st.sidebar.title("Menu")
pages = ["Réserver", "Annuler", "Calendrier", "Récapitulatif"]
choice = st.sidebar.radio("Navigation", pages)

# --- Chargement des réservations ---
@st.cache_data
def load_reservations():
    return pd.read_sql(
        "SELECT * FROM reservations",
        conn,
        parse_dates=['start_date', 'end_date', 'created_at', 'cancelled_at']
    )

# --- Page Réserver ---
if choice == "Réserver":
    st.header("Réserver une salle")
    rooms_df = pd.read_sql("SELECT * FROM rooms", conn)
    room = st.selectbox("Salle", rooms_df['name'])
    user = st.text_input("Nom utilisateur / projet")
    start = st.date_input("Date de début", date.today())
    end = st.date_input("Date de fin", date.today())
    start_time = st.time_input("Heure de début", time(9, 0))
    end_time = st.time_input("Heure de fin", time(17, 0))

    if st.button("Réserver"):
        rid = rooms_df.loc[rooms_df['name'] == room, 'id'].iloc[0]
        days = (end - start).days + 1
        created_at = datetime.now().isoformat()

        c.execute('''
            INSERT INTO reservations
              (room_id, start_date, end_date, start_time, end_time,
               user, project, status, initial_days, actual_days,
               created_at, cancelled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, NULL)
        ''', (
            rid,
            start.isoformat(),
            end.isoformat(),
            start_time.strftime('%H:%M:%S'),
            end_time.strftime('%H:%M:%S'),
            user,
            user,
            days,
            days,
            created_at
        ))
        conn.commit()
        st.success("✅ Réservation enregistrée")

# --- Page Annuler ---
elif choice == "Annuler":
    st.header("Annuler une réservation")
    df = load_reservations()
    df_active = df[df['status'] == 'active']
    if not df_active.empty:
        options = df_active.apply(
            lambda r: f"{r.id} – {r.user} ({r.start_date.date()}→{r.end_date.date()})",
            axis=1
        )
        sel = st.selectbox("Sélectionnez une réservation", options)
        if sel and st.button("Annuler"):
            res_id = int(sel.split(" –")[0])
            used = st.date_input("Date réelle d'arrêt", date.today())
            start_str = c.execute(
                "SELECT start_date FROM reservations WHERE id=?", (res_id,)
            ).fetchone()[0]
            start_dt = datetime.fromisoformat(start_str).date()
            actual = (used - start_dt).days + 1
            cancelled_at = datetime.now().isoformat()

            c.execute(
                "UPDATE reservations SET status='cancelled', actual_days=?, cancelled_at=? WHERE id=?",
                (actual, cancelled_at, res_id)
            )
            conn.commit()
            st.warning("⚠️ Réservation annulée")
    else:
        st.info("Aucune réservation active à annuler.")

# --- Page Calendrier (vue publique corrigée) ---
elif choice == "Calendrier":
    st.header("Calendrier des disponibilités (vue publique)")
    df = load_reservations()
    df_active = df[df['status'] == 'active']

    if df_active.empty:
        st.success("✅ Toutes les salles sont disponibles !")
    else:
        st.write("🟩 Libre / 🟥 Réservé")
        days_range = pd.date_range(start=date.today(), periods=30)
        rooms_list = pd.read_sql("SELECT * FROM rooms", conn)
        id2name = dict(zip(rooms_list['id'], rooms_list['name']))
        calendar_df = pd.DataFrame(
            index=days_range,
            columns=rooms_list['name']
        )
        calendar_df[:] = "🟩"

        # Remplissage sécurisé via mapping
        for _, row in df_active.iterrows():
            room_name = id2name.get(row['room_id'])
            if not room_name:
                continue
            for d in pd.date_range(start=row['start_date'], end=row['end_date']):
                if d in calendar_df.index:
                    calendar_df.at[d, room_name] = "🟥"

        st.dataframe(
            calendar_df.style.set_properties(**{'text-align': 'center'}),
            height=600
        )

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
