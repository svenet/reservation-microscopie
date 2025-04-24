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
# Secrets SMTP (configurés via Streamlit Cloud Secrets)
SMTP_SERVER = st.secrets.get("SMTP_SERVER")
SMTP_PORT = int(st.secrets.get("SMTP_PORT", 587))
EMAIL_USER = st.secrets.get("EMAIL_USER")
EMAIL_PASSWORD = st.secrets.get("EMAIL_PASSWORD")

NEW_RESA_COLS = ["Début", "Fin", "Salle", "Utilisateur", "Timestamp_resa"]
NEW_HISTO_COLS = ["Action", "Début", "Fin", "Salle", "Utilisateur", "Timestamp_resa", "Timestamp_annulation"]

# Heures pleines autorisées (affichage "8h00"..."19h00")
HOUR_LABELS = [f"{h}h00" for h in range(8, 20)]
HOURS = list(range(8, 20))

# --- Init CSV ---
def init_files():
    # ... (inchangé) ...
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

# --- Email function with fallback SSL ---
def send_history_email():
    if not SMTP_SERVER or not EMAIL_USER or not EMAIL_PASSWORD:
        st.error("Les paramètres SMTP ne sont pas configurés. Définissez vos secrets dans Streamlit Cloud.")
        return
    try:
        with open(HISTORIQUE_FILE, "rb") as f:
            data = f.read()
        msg = EmailMessage()
        msg["Subject"] = "Historique des réservations microscopie"
        msg["From"] = EMAIL_USER
        msg["To"] = EMAIL_TO
        msg.set_content("Vous trouverez en pièce jointe l'historique des réservations et annulations.")
        msg.add_attachment(data, maintype="text", subtype="csv", filename=HISTORIQUE_FILE)
        context = ssl.create_default_context()
        # Choix du mode de connexion
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
            server.starttls(context=context)
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        st.success(f"Historique envoyé à {EMAIL_TO}")
    except ConnectionRefusedError:
        st.error("Connexion refusée : vérifiez SMTP_SERVER et SMTP_PORT.")
    except Exception as e:
        st.error(f"Échec de l'envoi de l'email : {e}")

# --- Affichage Calendrier ---
def display_weekly_calendar(start_week: date):
    # ... (inchangé) ...
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
                    slot_start = datetime.combine(d, time(h, 0)); slot_end = slot_start + timedelta(hours=1)
                    if start < slot_end and end > slot_start:
                        cal.at[h_lbl, label] = "Occupé"
        st.subheader(f"Disponibilités semaine ({day_labels[0]} - {day_labels[-1]}) - Salle {salle}")
        # Utiliser Styler.map au lieu de applymap
        styled = cal.style.map(lambda v: 'color:white;background-color:red' if v == 'Occupé' else '')
        st.dataframe(styled)

# --- Streamlit UI ---
init_files()
st.title("Réservation des salles de microscopie")
if st.button("Envoyer l'historique par email"):
    send_history_email()
# ... (le reste de l'UI reste inchangé) ...
