#!/usr/bin/python3
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, time
from st_aggrid import AgGrid
from streamlit_calendar import calendar

# ---  SQLITE : connexion + schéma + migration automatique ---
conn = sqlite3.connect('reservations.db', check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)""")
c.execute("""CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY,
                room_id INTEGER, start_date TEXT, end_date TEXT,
                user TEXT, project TEXT, status TEXT,
                initial_days INTEGER, actual_days INTEGER,
                FOREIGN KEY(room_id) REFERENCES rooms(id)
            )""")
conn.commit()
# migration pour colonnes horaires et timestamps
existing = [col[1] for col in c.execute("PRAGMA table_info(reservations)") ]
for col in ['start_time','end_time','created_at','cancelled_at']:
    if col not in existing:
        c.execute(f"ALTER TABLE reservations ADD COLUMN {col} TEXT")
conn.commit()
# init salles si vide
c.execute("SELECT COUNT(*) FROM rooms")
if c.fetchone()[0]==0:
    c.executemany("INSERT INTO rooms(name) VALUES(?)",
                  [("Salle Raman - Witec",),("Salle microscope inversé - Nikon",)])
    conn.commit()

# --- Chargement des réservations ---
@st.cache_data
def load_reservations():
    return pd.read_sql("SELECT * FROM reservations", conn,
                       parse_dates=['start_date','end_date','created_at','cancelled_at'])

# --- Menu ---
st.sidebar.title("Menu")
choice = st.sidebar.radio("Navigation", ["Réserver","Annuler","Calendrier","Récapitulatif"])

# --- Pages Réserver / Annuler (identique à avant) ---
if choice=="Réserver":
    st.header("Réserver une salle")
    rooms_df = pd.read_sql("SELECT * FROM rooms", conn)
    room = st.selectbox("Salle", rooms_df['name'])
    user = st.text_input("Nom utilisateur / projet")
    start = st.date_input("Date de début", date.today())
    end   = st.date_input("Date de fin",   date.today())
    stime = st.time_input("Heure de début", time(9,0))
    etime = st.time_input("Heure de fin",   time(17,0))
    if st.button("Réserver"):
        rid = rooms_df.loc[rooms_df['name']==room,'id'].iloc[0]
        days = (end-start).days+1
        now = datetime.now().isoformat()
        c.execute("""INSERT INTO reservations
                     (room_id,start_date,end_date,start_time,end_time,
                      user,project,status,initial_days,actual_days,
                      created_at,cancelled_at)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,NULL)""",
                  (rid, start.isoformat(), end.isoformat(),
                   stime.strftime('%H:%M:%S'), etime.strftime('%H:%M:%S'),
                   user, user, 'active', days, days, now))
        conn.commit()
        st.success("✅ Réservation enregistrée")

elif choice=="Annuler":
    st.header("Annuler une réservation")
    df = load_reservations()
    act = df[df.status=='active']
    if act.empty:
        st.info("Aucune réservation active.")
    else:
        opts = act.apply(lambda r: f"{r.id} – {r.user} ({r.start_date.date()}→{r.end_date.date()})", axis=1)
        sel = st.selectbox("Choisir", opts)
        if sel and st.button("Annuler"):
            rid = int(sel.split(" –")[0])
            used = st.date_input("Date réelle d'arrêt", date.today())
            sd = datetime.fromisoformat(
                c.execute("SELECT start_date FROM reservations WHERE id=?", (rid,)).fetchone()[0]
            ).date()
            actual = (used-sd).days+1
            canc = datetime.now().isoformat()
            c.execute("""UPDATE reservations
                         SET status='cancelled', actual_days=?, cancelled_at=?
                         WHERE id=?""", (actual,canc,rid))
            conn.commit()
            st.warning("⚠️ Réservation annulée")

# --- Page CALENDRIER : vue hebdo ½-journées ---
elif choice=="Calendrier":
    st.header("Disponibilités – vue semaine (08h-12h & 14h-18h)")

    df = load_reservations()
    df = df[df.status=='active']

    # Prépare les events FullCalendar
    events_by_room = {}
    rooms = pd.read_sql("SELECT id,name FROM rooms", conn)
    for rid,name in zip(rooms.id, rooms.name):
        evs = []
        for _, r in df[df.room_id==rid].iterrows():
            evs.append({
                "title":"Occupé",
                "start": f"{r.start_date.date().isoformat()}T{r.start_time}",
                "end":   f"{r.end_date.date().isoformat()}T{r.end_time}"
            })
        events_by_room[rid] = evs

    # Options FullCalendar – vue hebdo, créneaux 4h, businessHours en 8-12 & 14-18
    options = {
      "initialView":    "timeGridWeek",          # vue semaine :contentReference[oaicite:1]{index=1}
      "slotMinTime":    "08:00:00",              # début plage :contentReference[oaicite:2]{index=2}
      "slotMaxTime":    "18:00:00",              # fin plage :contentReference[oaicite:3]{index=3}
      "slotDuration":   "04:00:00",              # créneaux de 4h :contentReference[oaicite:4]{index=4}
      "slotLabelInterval":"04:00:00",            # label chaque 4h :contentReference[oaicite:5]{index=5}
      "businessHours":[                          # met en évidence ½-journées :contentReference[oaicite:6]{index=6}
         {"daysOfWeek":[1,2,3,4,5],"startTime":"08:00","endTime":"12:00"},
         {"daysOfWeek":[1,2,3,4,5],"startTime":"14:00","endTime":"18:00"}
      ],
      "allDaySlot": False,
      "headerToolbar":{"left":"prev,next today","center":"title","right":"timeGridWeek"}
    }

    # Deux colonnes – une par salle :contentReference[oaicite:7]{index=7}
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(rooms.loc[rooms.id==1,'name'].iloc[0])
        calendar(events=events_by_room[1], options=options)
    with col2:
        st.subheader(rooms.loc[rooms.id==2,'name'].iloc[0])
        calendar(events=events_by_room[2], options=options)

# --- Page RÉCAPITULATIF (identique) ---
elif choice=="Récapitulatif":
    st.header("📋 Récapitulatif des réservations")
    df = load_reservations()
    mapping = dict(zip(*pd.read_sql("SELECT id,name FROM rooms",conn).values.T))
    df['Salle'] = df.room_id.map(mapping)
    df = df.rename(columns={
      'user':'Utilisateur','project':'Projet',
      'start_date':'Début','end_date':'Fin',
      'start_time':'Heure début','end_time':'Heure fin',
      'status':'Statut','created_at':'Réservé le','cancelled_at':'Annulé le'
    })
    AgGrid(df[[
      'Salle','Utilisateur','Projet','Début','Fin',
      'Heure début','Heure fin','Statut','Réservé le','Annulé le'
    ]].sort_values('Début',ascending=False), height=500)
