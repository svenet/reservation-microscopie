#!/usr/bin/python3

import streamlit as st
import pandas as pd
import os
from datetime import datetime, time, date, timedelta

RESERVATION_FILE = "reservations.csv"
HISTORIQUE_FILE = "historique.csv"
NEW_RESA_COLS = ["Début", "Fin", "Salle", "Utilisateur", "Timestamp_resa"]
NEW_HISTO_COLS = ["Action", "Début", "Fin", "Salle", "Utilisateur", "Timestamp_resa", "Timestamp_annulation"]

# Heures pleines autorisées
HOUR_LABELS = [f"{h}h00" for h in range(8, 20)]
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

# Réservation et annulation simple

def reserver(debut, fin, salle, utilisateur):
    df = pd.read_csv(RESERVATION_FILE)
    df["Début"] = pd.to_datetime(df["Début"])
    df["Fin"] = pd.to_datetime(df["Fin"])
    conflit = df[(df["Salle"] == salle) & (
        ((df["Début"] <= debut) & (df["Fin"] > debut)) |
        ((df["Début"] < fin) & (df["Fin"] >= fin))
    )]
    if not conflit.empty:
        st.warning(f"Conflit pour {salle}.")
        return
    timestamp = datetime.now().isoformat()
    entry = [debut.isoformat(), fin.isoformat(), salle, utilisateur, timestamp]
    df.loc[len(df)] = entry
    df.to_csv(RESERVATION_FILE, index=False)
    histo = pd.read_csv(HISTORIQUE_FILE)
    histo.loc[len(histo)] = ["Réservation", debut.isoformat(), fin.isoformat(), salle, utilisateur, timestamp, ""]
    histo.to_csv(HISTORIQUE_FILE, index=False)
    st.success("Réservé.")

def annuler(debut, fin, salle, utilisateur):
    df = pd.read_csv(RESERVATION_FILE)
    df["Début"] = pd.to_datetime(df["Début"])
    df["Fin"] = pd.to_datetime(df["Fin"])
    mask = (df["Salle"] == salle) & (df["Utilisateur"] == utilisateur) & (df["Début"] == debut) & (df["Fin"] == fin)
    if not mask.any():
        st.warning("Non trouvé.")
        return
    df = df[~mask]
    df.to_csv(RESERVATION_FILE, index=False)
    histo = pd.read_csv(HISTORIQUE_FILE)
    timestamp = datetime.now().isoformat()
    histo.loc[len(histo)] = ["Annulation", debut.isoformat(), fin.isoformat(), salle, utilisateur, "", timestamp]
    histo.to_csv(HISTORIQUE_FILE, index=False)
    st.success("Annulé.")

# Calendrier hebdo

def display_weekly_calendar(start_week: date):
    days = [start_week + timedelta(days=i) for i in range(7)]
    labels = [d.strftime('%a %d/%m') for d in days]
    df = pd.read_csv(RESERVATION_FILE)
    df['Début'] = pd.to_datetime(df['Début']); df['Fin'] = pd.to_datetime(df['Fin'])
    for salle in ["Raman", "Fluorescence inversé"]:
        cal = pd.DataFrame(index=HOUR_LABELS, columns=labels).fillna("Libre")
        for _, r in df[df['Salle']==salle].iterrows():
            for h, hl in zip(HOURS, HOUR_LABELS):
                for d, lbl in zip(days, labels):
                    start = datetime.combine(d, time(h,0)); end = start+timedelta(hours=1)
                    if r['Début']<end and r['Fin']>start:
                        cal.at[hl,lbl] = "Occupé"
        st.subheader(f"{salle}")
        st.dataframe(cal)

# App
init_files()
st.title("Microscopie")
week_start = st.date_input("Semaine du (lundi)", value=date.today()-timedelta(days=date.today().weekday()))
display_weekly_calendar(week_start)
st.header("Réserver")
with st.form("res"):
    u=st.text_input("User")
    d1=st.date_input("Début"); h1=st.selectbox("h Début",HOUR_LABELS)
    d2=st.date_input("Fin"); h2=st.selectbox("h Fin",HOUR_LABELS)
    c1=st.checkbox("Raman"); c2=st.checkbox("Fluo")
    if st.form_submit_button("Go") and u:
        dt1=datetime.combine(d1,time(int(h1.replace('h00','')),0))
        dt2=datetime.combine(d2,time(int(h2.replace('h00','')),0))
        if c1: reserver(dt1,dt2,"Raman",u)
        if c2: reserver(dt1,dt2,"Fluorescence inversé",u)
st.header("Annuler")
with st.form("ann"):
    u2=st.text_input("User ann",key="a")
    da1=st.date_input("Début a",key="da1"); ha1=st.selectbox("h Da1",HOUR_LABELS,key="ha1")
    da2=st.date_input("Fin a",key="da2"); ha2=st.selectbox("h Da2",HOUR_LABELS,key="ha2")
    cc1=st.checkbox("Raman a"); cc2=st.checkbox("Fluo a")
    if st.form_submit_button("Go ann") and u2:
        D1=datetime.combine(da1,time(int(ha1.replace('h00','')),0))
        D2=datetime.combine(da2,time(int(ha2.replace('h00','')),0))
        if cc1: annuler(D1,D2,"Raman",u2)
        if cc2: annuler(D1,D2,"Fluorescence inversé",u2)
