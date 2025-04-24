#!/usr/bin/python3

import streamlit as st
import pandas as pd
import os
from datetime import datetime

RESERVATION_FILE = "reservations.csv"
HISTORIQUE_FILE = "historique.csv"
SALLE_OPTIONS = ["Raman", "Fluorescence inversé"]
CRENEAUX = ["08h-10h", "10h-12h", "13h-15h", "15h-17h", "17h-19h"]

def init_files():
    if not os.path.exists(RESERVATION_FILE):
        pd.DataFrame(columns=["Date", "Salle", "Créneau", "Utilisateur", "Timestamp_resa"]).to_csv(RESERVATION_FILE, index=False)
    if not os.path.exists(HISTORIQUE_FILE):
        pd.DataFrame(columns=["Action", "Date", "Salle", "Créneau", "Utilisateur", "Timestamp_resa", "Timestamp_annulation"]).to_csv(HISTORIQUE_FILE, index=False)

def reserver(date, salle, creneau, utilisateur):
    df = pd.read_csv(RESERVATION_FILE)
    if ((df["Date"] == date) & (df["Salle"] == salle) & (df["Créneau"] == creneau)).any():
        st.warning("Ce créneau est déjà réservé.")
        return
    timestamp = datetime.now().isoformat()
    new_resa = pd.DataFrame([[date, salle, creneau, utilisateur, timestamp]], columns=df.columns)
    df = pd.concat([df, new_resa], ignore_index=True)
    df.to_csv(RESERVATION_FILE, index=False)
    histo = pd.read_csv(HISTORIQUE_FILE)
    histo = pd.concat([histo, pd.DataFrame([["Réservation", date, salle, creneau, utilisateur, timestamp, ""]], columns=histo.columns)], ignore_index=True)
    histo.to_csv(HISTORIQUE_FILE, index=False)
    st.success("Réservation enregistrée.")

def annuler(date, salle, creneau, utilisateur):
    df = pd.read_csv(RESERVATION_FILE)
    mask = (df["Date"] == date) & (df["Salle"] == salle) & (df["Créneau"] == creneau) & (df["Utilisateur"] == utilisateur)
    if not mask.any():
        st.warning("Réservation non trouvée.")
        return
    df = df[~mask]
    df.to_csv(RESERVATION_FILE, index=False)
    timestamp = datetime.now().isoformat()
    histo = pd.read_csv(HISTORIQUE_FILE)
    histo = pd.concat([histo, pd.DataFrame([["Annulation", date, salle, creneau, utilisateur, "", timestamp]], columns=histo.columns)], ignore_index=True)
    histo.to_csv(HISTORIQUE_FILE, index=False)
    st.success("Réservation annulée.")

# Initialisation
init_files()
st.title("Réservation des salles de microscopie")

st.header("Nouvelle réservation")
with st.form("reservation_form"):
    utilisateur = st.text_input("Nom de l'utilisateur")
    date = st.date_input("Date de réservation")
    salle = st.selectbox("Salle", SALLE_OPTIONS)
    creneau = st.selectbox("Créneau horaire", CRENEAUX)
    submitted = st.form_submit_button("Réserver")
    if submitted and utilisateur:
        reserver(str(date), salle, creneau, utilisateur)

st.header("Annuler une réservation")
with st.form("annulation_form"):
    utilisateur = st.text_input("Nom de l'utilisateur pour annulation")
    date = st.date_input("Date à annuler", key="annul_date")
    salle = st.selectbox("Salle", SALLE_OPTIONS, key="annul_salle")
    creneau = st.selectbox("Créneau horaire", CRENEAUX, key="annul_creneau")
    submitted = st.form_submit_button("Annuler")
    if submitted and utilisateur:
        annuler(str(date), salle, creneau, utilisateur)

st.header("Historique des réservations et annulations")
histo = pd.read_csv(HISTORIQUE_FILE)
st.dataframe(histo.sort_values(by="Timestamp_resa", ascending=False))
