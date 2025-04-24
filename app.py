#!/usr/bin/python3

import streamlit as st
import pandas as pd
import os
from datetime import datetime, time, date, timedelta

RESERVATION_FILE = "reservations.csv"
HISTORIQUE_FILE = "historique.csv"
NEW_RESA_COLS = ["Début", "Fin", "Salle", "Utilisateur", "Timestamp_resa"]
NEW_HISTO_COLS = ["Action", "Début", "Fin", "Salle", "Utilisateur", "Timestamp_resa", "Timestamp_annulation"]

# Heures pleines autorisées (affichage en "8h00" etc.)
HOUR_LABELS = [f"{h}h00" for h in range(8, 20)]  # 8h00 à 19h00
HOURS = list(range(8, 20))

# Initialisation des fichiers CSV

def init_files():
    if os.path.exists(RESERVATION_FILE):
        df = pd.read_csv(RESERVATION_FILE)
        if not all(col in df.columns for col in NEW_RESA_COLS):
            pd.DataFrame(columns=NEW_RESA_COLS).to_csv(RESERVATION_FILE, index=False)
    else:
        pd.DataFrame(columns=NEW_RESA_COLS).to_csv(RESERVATION_FILE, index=False)

    if os.path.exists(HISTORIQUE_FILE):
        dfh = pd.read_csv(HISTORIQUE_FILE)
        if not all(col in dfh.columns for col in NEW_HISTO_COLS):
            pd.DataFrame(columns=NEW_HISTO_COLS).to_csv(HISTORIQUE_FILE, index=False)
    else:
        pd.DataFrame(columns=NEW_HISTO_COLS).to_csv(HISTORIQUE_FILE, index=False)

# Affichage des calendriers hebdomadaires pour une semaine donnée

def display_weekly_calendar(start_week: date):
    # calcul des jours de la semaine (lundi à dimanche)
    days = [start_week + timedelta(days=i) for i in range(7)]
    day_labels = [d.strftime('%a %d/%m') for d in days]

    # charger réservations
    df = pd.read_csv(RESERVATION_FILE)
    if not df.empty:
        df['Début'] = pd.to_datetime(df['Début'])
        df['Fin'] = pd.to_datetime(df['Fin'])

    for salle in ["Raman", "Fluorescence inversé"]:
        # initialiser matrice disponibilité
        cal = pd.DataFrame(index=HOUR_LABELS, columns=day_labels)
        cal.fillna("Libre", inplace=True)
        # marquer réservations
        df_s = df[df['Salle'] == salle]
        for _, row in df_s.iterrows():
            start = row['Début']
            end = row['Fin']
            for d, label in zip(days, day_labels):
                for h, h_lbl in zip(HOURS, HOUR_LABELS):
                    slot_start = datetime.combine(d, time(h, 0))
                    slot_end = slot_start + timedelta(hours=1)
                    if start < slot_end and end > slot_start:
                        cal.at[h_lbl, label] = "Occupé"
        st.subheader(f"Disponibilités semaine ({day_labels[0]} - {day_labels[-1]}) - Salle {salle}")
        st.table(cal)

# --- Application Streamlit ---
init_files()
st.title("Réservation des salles de microscopie")

# Sélecteur de semaine (date de début de semaine)
today = date.today()
default_monday = today - timedelta(days=today.weekday())
week_start = st.date_input("Semaine du (lundi)", value=default_monday, help="Choisissez le lundi de la semaine à afficher")

# afficher calendriers pour la semaine sélectionnée
display_weekly_calendar(week_start)

st.header("Nouvelle réservation")
with st.form("reservation_form"):
    utilisateur_resa = st.text_input("Nom de l'utilisateur", key="resa_user")
    date_debut = st.date_input("Date de début", key="resa_date_debut")
    heure_debut_lbl = st.selectbox("Heure de début", HOUR_LABELS, key="resa_h_debut")
    date_fin = st.date_input("Date de fin", key="resa_date_fin")
    heure_fin_lbl = st.selectbox("Heure de fin", HOUR_LABELS, key="resa_h_fin")
    salle_raman = st.checkbox("Salle Raman", key="resa_raman")
    salle_fluo = st.checkbox("Salle Fluorescence inversé", key="resa_fluo")
    submit_resa = st.form_submit_button("Réserver")
    if submit_resa and utilisateur_resa:
        debut_hour = int(heure_debut_lbl.replace('h00',''))
        fin_hour = int(heure_fin_lbl.replace('h00',''))
        debut_dt = datetime.combine(date_debut, time(debut_hour, 0))
        fin_dt = datetime.combine(date_fin, time(fin_hour, 0))
        if fin_dt <= debut_dt:
            st.error("La date/heure de fin doit être après la date/heure de début.")
        else:
            if salle_raman:
                reserver(debut_dt, fin_dt, "Raman", utilisateur_resa)
            if salle_fluo:
                reserver(debut_dt, fin_dt, "Fluorescence inversé", utilisateur_resa)

st.header("Annuler une réservation")
with st.form("annulation_form"):
    utilisateur_annul = st.text_input("Nom de l'utilisateur pour annulation", key="annul_user")
    date_debut_a = st.date_input("Date de début à annuler", key="annul_date_debut")
    heure_debut_lbl_a = st.selectbox("Heure de début à annuler", HOUR_LABELS, key="annul_h_debut")
    date_fin_a = st.date_input("Date de fin à annuler", key="annul_date_fin")
    heure_fin_lbl_a = st.selectbox("Heure de fin à annuler", HOUR_LABELS, key="annul_h_fin")
    salle_raman_a = st.checkbox("Salle Raman", key="annul_raman")
    salle_fluo_a = st.checkbox("Salle Fluorescence inversé", key="annul_fluo")
    submit_annul = st.form_submit_button("Annuler")
    if submit_annul and utilisateur_annul:
        debut_hour_a = int(heure_debut_lbl_a.replace('h00',''))
        fin_hour_a = int(heure_fin_lbl_a.replace('h00',''))
        debut_a = datetime.combine(date_debut_a, time(debut_hour_a, 0))
        fin_a = datetime.combine(date_fin_a, time(fin_hour_a, 0))
        if fin_a <= debut_a:
            st.error("La date/heure de fin doit être après la date/heure de début.")
        else:
            if salle_raman_a:
                annuler(debut_a, fin_a, "Raman", utilisateur_annul)
            if salle_fluo_a:
                annuler(debut_a, fin_a, "Fluorescence inversé", utilisateur_annul)

st.header("Historique des réservations et annulations")
histo = pd.read_csv(HISTORIQUE_FILE)
st.dataframe(histo.sort_values(by=["Timestamp_resa", "Timestamp_annulation"], ascending=False))
