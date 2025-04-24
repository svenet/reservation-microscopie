#!/usr/bin/python3

import streamlit as st
import pandas as pd
import os
import smtplib
import ssl
from email.message import EmailMessage
from datetime import datetime, time, date, timedelta

# --- Config ---
RESERVATION_FILE = "reservations.csv"
HISTORIQUE_FILE = "historique.csv"
EMAIL_TO = "pomisop@univ-pau.fr"
# Variables d'environnement pour SMTP (configurées via Streamlit Cloud Secrets)
SMTP_SERVER = os.getenv("SMTP_SERVER")  # ex. "smtp.gmail.com"
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

NEW_RESA_COLS = ["Début", "Fin", "Salle", "Utilisateur", "Timestamp_resa"]
NEW_HISTO_COLS = ["Action", "Début", "Fin", "Salle", "Utilisateur", "Timestamp_resa", "Timestamp_annulation"]

# Heures pleines autorisées (affichage "8h00"..."19h00")
HOUR_LABELS = [f"{h}h00" for h in range(8, 20)]
HOURS = list(range(8, 20))

# --- Init CSV ---
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

# --- Email function ---
def send_history_email():
    with open(HISTORIQUE_FILE, "rb") as f:
        data = f.read()
    msg = EmailMessage()
    msg["Subject"] = "Historique des réservations microscopie"
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO
    msg.set_content("Vous trouverez en pièce jointe l'historique des réservations et annulations.")
    msg.add_attachment(data, maintype="text", subtype="csv", filename=HISTORIQUE_FILE)
    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
    st.success(f"Historique envoyé à {EMAIL_TO}")

# --- Réservation / Annulation ---
def reserver(debut, fin, salle, utilisateur):
    df = pd.read_csv(RESERVATION_FILE)
    df["Début"] = pd.to_datetime(df["Début"])
    df["Fin"] = pd.to_datetime(df["Fin"])
    conflit = df[(df["Salle"] == salle) & (
        ((df["Début"] <= debut) & (df["Fin"] > debut)) |
        ((df["Début"] < fin) & (df["Fin"] >= fin)) |
        ((df["Début"] >= debut) & (df["Fin"] <= fin))
    )]
    if not conflit.empty:
        st.warning(f"Un conflit de réservation existe déjà pour la salle {salle} à cette période.")
        return
    timestamp = datetime.now().isoformat()
    new_resa = pd.DataFrame([[debut.isoformat(), fin.isoformat(), salle, utilisateur, timestamp]], columns=NEW_RESA_COLS)
    df_out = pd.concat([df, new_resa], ignore_index=True)
    df_out["Début"] = df_out["Début"].astype(str)
    df_out["Fin"] = df_out["Fin"].astype(str)
    df_out.to_csv(RESERVATION_FILE, index=False)
    histo = pd.read_csv(HISTORIQUE_FILE)
    entry = ["Réservation", debut.isoformat(), fin.isoformat(), salle, utilisateur, timestamp, ""]
    histo = pd.concat([histo, pd.DataFrame([entry], columns=NEW_HISTO_COLS)], ignore_index=True)
    histo.to_csv(HISTORIQUE_FILE, index=False)
    st.success(f"Réservation enregistrée pour la salle {salle}.")

def annuler(debut, fin, salle, utilisateur):
    df = pd.read_csv(RESERVATION_FILE)
    df["Début"] = pd.to_datetime(df["Début"])
    df["Fin"] = pd.to_datetime(df["Fin"])
    mask_user = (df["Salle"] == salle) & (df["Utilisateur"] == utilisateur)
    to_process = df[mask_user]
    updated = []
    removed = []
    for _, row in to_process.iterrows():
        r_start, r_end = row["Début"], row["Fin"]
        if fin <= r_start or debut >= r_end:
            updated.append(row)
            continue
        if debut <= r_start and fin >= r_end:
            removed.append((r_start, r_end)); continue
        if debut <= r_start < fin < r_end:
            updated.append({"Début": fin, "Fin": r_end, "Salle": salle, "Utilisateur": utilisateur, "Timestamp_resa": row["Timestamp_resa"]})
            removed.append((r_start, fin)); continue
        if r_start < debut < r_end <= fin:
            updated.append({"Début": r_start, "Fin": debut, "Salle": salle, "Utilisateur": utilisateur, "Timestamp_resa": row["Timestamp_resa"]})
            removed.append((debut, r_end)); continue
        if r_start < debut and fin < r_end:
            updated.append({"Début": r_start, "Fin": debut, "Salle": salle, "Utilisateur": utilisateur, "Timestamp_resa": row["Timestamp_resa"]})
            updated.append({"Début": fin, "Fin": r_end, "Salle": salle, "Utilisateur": utilisateur, "Timestamp_resa": row["Timestamp_resa"]})
            removed.append((debut, fin))
    others = df[~mask_user]
    if updated:
        df_updated = pd.DataFrame(updated)
        df_updated["Début"] = df_updated["Début"].astype(str)
        df_updated["Fin"] = df_updated["Fin"].astype(str)
        df_out = pd.concat([others, df_updated], ignore_index=True)
    else:
        df_out = others.copy()
    df_out.to_csv(RESERVATION_FILE, index=False)
    histo = pd.read_csv(HISTORIQUE_FILE)
    timestamp = datetime.now().isoformat()
    for rem in removed:
        entry = ["Annulation partielle", rem[0].isoformat(), rem[1].isoformat(), salle, utilisateur, "", timestamp]
        histo = pd.concat([histo, pd.DataFrame([entry], columns=NEW_HISTO_COLS)], ignore_index=True)
    histo.to_csv(HISTORIQUE_FILE, index=False)
    st.success(f"Annulation effectuée pour l'intervalle spécifié sur la salle {salle}.")

# --- Affichage Calendrier ---
def display_weekly_calendar(start_week: date):
    days = [start_week + timedelta(days=i) for i in range(7)]
    day_labels = [d.strftime('%a %d/%m') for d in days]
    df = pd.read_csv(RESERVATION_FILE)
    if not df.empty:
        df['Début'] = pd.to_datetime(df['Début']); df['Fin'] = pd.to_datetime(df['Fin'])
    for salle in ["Raman", "Fluorescence inversé"]:
        cal = pd.DataFrame(index=HOUR_LABELS, columns=day_labels).fillna("Libre")
        df_s = df[df['Salle'] == salle]
        for _, row in df_s.iterrows():
            start, end = row['Début'], row['Fin']
            for d, label in zip(days, day_labels):
                for h, h_lbl in zip(HOURS, HOUR_LABELS):
                    slot_start = datetime.combine(d, time(h,0)); slot_end = slot_start + timedelta(hours=1)
                    if start < slot_end and end > slot_start:
                        cal.at[h_lbl, label] = "Occupé"
        st.subheader(f"Disponibilités semaine ({day_labels[0]} - {day_labels[-1]}) - Salle {salle}")
        styled = cal.style.applymap(lambda v: 'color:white;background-color:red' if v=='Occupé' else '')
        st.dataframe(styled)

# --- Streamlit UI ---
init_files()
st.title("Réservation des salles de microscopie")

if st.button("Envoyer l'historique par email"):
    send_history_email()

# Sélecteur de semaine
week_start = st.date_input("Semaine du (lundi)", value=date.today() - timedelta(days=date.today().weekday()))

# Afficher calendriers
display_weekly_calendar(week_start)

# Formulaire réservation
st.header("Nouvelle réservation")
with st.form("reservation_form"):
    user = st.text_input("Nom de l'utilisateur", key="resa_user")
    d1 = st.date_input("Date de début", key="resa_date_debut")
    h1 = st.selectbox("Heure de début", HOUR_LABELS, key="resa_h_debut")
    d2 = st.date_input("Date de fin", key="resa_date_fin")
    h2 = st.selectbox("Heure de fin", HOUR_LABELS, key="resa_h_fin")
    cb1 = st.checkbox("Salle Raman", key="resa_raman")
    cb2 = st.checkbox("Salle Fluorescence inversé", key="resa_fluo")
    if st.form_submit_button("Réserver") and user:
        dt1 = datetime.combine(d1, time(int(h1.replace('h00','')),0))
        dt2 = datetime.combine(d2, time(int(h2.replace('h00','')),0))
        if dt2 <= dt1:
            st.error("Fin doit être après début.")
        else:
            if cb1:
                reserver(dt1, dt2, "Raman", user)
            if cb2:
                reserver(dt1, dt2, "Fluorescence inversé", user)

# Formulaire annulation
st.header("Annuler une réservation")
with st.form("annulation_form"):
    user2 = st.text_input("Nom de l'utilisateur pour annulation", key="annul_user")
    da1 = st.date_input("Date de début à annuler", key="annul_date_debut")
    ha1 = st.selectbox("Heure de début à annuler", HOUR_LABELS, key="annul_h_debut")
    da2 = st.date_input("Date de fin à annuler", key="annul_date_fin")
    ha2 = st.selectbox("Heure de fin à annuler", HOUR_LABELS, key="annul_h_fin")
    cb3 = st.checkbox("Salle Raman", key="annul_raman")
    cb4 = st.checkbox("Salle Fluorescence inversé", key="annul_fluo")
    if st.form_submit_button("Annuler") and user2:
        dtA1 = datetime.combine(da1, time(int(ha1.replace('h00','')),0))
        dtA2 = datetime.combine(da2, time(int(ha2.replace('h00','')),0))
        if dtA2 <= dtA1:
            st.error("Fin doit être après début.")
        else:
            if cb3:
                annuler(dtA1, dtA2, "Raman", user2)
            if cb4:
                annuler(dtA1, dtA2, "Fluorescence inversé", user2)
