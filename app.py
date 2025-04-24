#!/usr/bin/python3

import streamlit as st
import pandas as pd
import os
from datetime import datetime

RESERVATION_FILE = "reservations.csv"
HISTORIQUE_FILE = "historique.csv"
SALLE_OPTIONS = ["Raman", "Fluorescence inversé"]

def init_files():
    if not os.path.exists(RESERVATION_FILE):
        pd.DataFrame(columns=["Début", "Fin", "Salle", "Utilisateur", "Timestamp_resa"]).to_csv(RESERVATION_FILE, index=False)
    if not os.path.exists(HISTORIQUE_FILE):
        pd.DataFrame(columns=["Action", "Début", "Fin", "Salle", "Utilisateur", "Timestamp_resa", "Timestamp_annulation"]).to_csv(HISTORIQUE_FILE, index=False)

def reserver(debut, fin, salle, utilisateur):
    df = pd.read_csv(RESERVATION_FILE)
    conflit = df[(df["Salle"] == salle) & (
        ((df["Début"] <= debut) & (df["Fin"] > debut)) |
        ((df["Début"] < fin) & (df["Fin"] >= fin)) |
        ((df["Début"] >= debut) & (df["Fin"] <= fin))
    )]
    if not conflit.empty:
        st.warning("Un conflit de réservation existe déjà pour cette salle à cette période.")
        return
    timestamp = datetime.now().isoformat()
    new_resa = pd.DataFrame([[debut, fin, salle, utilisateur, timestamp]], columns=df.columns)
    df = pd.concat([df, new_resa], ignore_index=True)
    df.to_csv(RESERVATION_FILE, index=False)
    histo = pd.read_csv(HISTORIQUE_FILE)
    histo = pd.concat([histo, pd.DataFrame([["Réservation", debut, fin, salle, utilisateur, timestamp, ""]], columns=histo.columns)], ignore_index=True)
    histo.to_csv(HISTORIQUE_FILE, index=False)
    st.success("Réservation enregistrée.")

def annuler(debut, fin, salle, utilisateur):
    df = pd.read_csv(RESERVATION_FILE)
    mask = (df["Début"] == debut) & (df["Fin"] == fin) & (df["Salle"] == salle) & (df["Utilisateur"] == utilisateur)
    if not mask.any():
        st.warning("Réservation non trouvée.")
        return
    df = df[~mask]
    df.to_csv(RESERVATION_FILE, index=False)
    timestamp = datetime.now().isoformat()
    histo = pd.read_csv(HISTORIQUE_FILE)
    histo = pd.concat([histo, pd.DataFrame([["Annulation", debut, fin, salle, utilisateur, "", timestamp]], columns=histo.columns)], ignore_index=True)
    histo.to_csv(HISTORIQUE_FILE, index=False)
    st.success("Réservation annulée.")

# Initialisation
init_files()
st.title("Réservation des salles de microscopie")

st.header("Nouvelle réservation")
with st.form("reservation_form"):
    utilisateur = st.text_input("Nom de l'utilisateur")
    debut = st.datetime_input("Début de la réservation")
    fin = st.datetime_input("Fin de la réservation")
    salle_raman = st.checkbox("Salle Raman")
    salle_fluo = st.checkbox("Salle Fluorescence inversé")
    submitted = st.form_submit_button("Réserver")
    if submitted and utilisateur:
        if salle_raman:
            reserver(str(debut), str(fin), "Raman", utilisateur)
        if salle_fluo:
            reserver(str(debut), str(fin), "Fluorescence inversé", utilisateur)

st.header("Annuler une réservation")
with st.form("annulation_form"):
    utilisateur = st.text_input("Nom de l'utilisateur pour annulation")
    debut = st.datetime_input("Début de la réservation à annuler", key="annul_debut")
    fin = st.datetime_input("Fin de la réservation à annuler", key="annul_fin")
    salle_raman = st.checkbox("Salle Raman", key="annul_raman")
    salle_fluo = st.checkbox("Salle Fluorescence inversé", key="annul_fluo")
    submitted = st.form_submit_button("Annuler")
    if submitted and utilisateur:
        if salle_raman:
            annuler(str(debut), str(fin), "Raman", utilisateur)
        if salle_fluo:
            annuler(str(debut), str(fin), "Fluorescence inversé", utilisateur)

st.header("Historique des réservations et annulations")
histo = pd.read_csv(HISTORIQUE_FILE)
st.dataframe(histo.sort_values(by=["Timestamp_resa", "Timestamp_annulation"], ascending=False))
