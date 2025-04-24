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
        st.warning(f"Un conflit de réservation existe déjà pour la salle {salle} à cette période.")
        return
    timestamp = datetime.now().isoformat()
    new_resa = pd.DataFrame([[debut, fin, salle, utilisateur, timestamp]], columns=df.columns)
    df = pd.concat([df, new_resa], ignore_index=True)
    df.to_csv(RESERVATION_FILE, index=False)
    histo = pd.read_csv(HISTORIQUE_FILE)
    histo = pd.concat([histo, pd.DataFrame([["Réservation", debut, fin, salle, utilisateur, timestamp, ""]], columns=histo.columns)], ignore_index=True)
    histo.to_csv(HISTORIQUE_FILE, index=False)
    st.success(f"Réservation enregistrée pour la salle {salle}.")

def annuler(debut, fin, salle, utilisateur):
    df = pd.read_csv(RESERVATION_FILE)
    mask = (df["Début"] == debut) & (df["Fin"] == fin) & (df["Salle"] == salle) & (df["Utilisateur"] == utilisateur)
    if not mask.any():
        st.warning(f"Réservation non trouvée pour la salle {salle}.")
        return
    df = df[~mask]
    df.to_csv(RESERVATION_FILE, index=False)
    timestamp = datetime.now().isoformat()
    histo = pd.read_csv(HISTORIQUE_FILE)
    histo = pd.concat([histo, pd.DataFrame([["Annulation", debut, fin, salle, utilisateur, "", timestamp]], columns=histo.columns)], ignore_index=True)
    histo.to_csv(HISTORIQUE_FILE, index=False)
    st.success(f"Réservation annulée pour la salle {salle}.")

# Initialisation
init_files()
st.title("Réservation des salles de microscopie")

st.header("Nouvelle réservation")
with st.form("reservation_form"):
    utilisateur_resa = st.text_input("Nom de l'utilisateur", key="resa_user")
    debut_resa = st.datetime_input("Début de la réservation", key="resa_debut")
    fin_resa = st.datetime_input("Fin de la réservation", key="resa_fin")
    salle_raman_resa = st.checkbox("Salle Raman", key="resa_raman")
    salle_fluo_resa = st.checkbox("Salle Fluorescence inversé", key="resa_fluo")
    submit_resa = st.form_submit_button("Réserver")
    if submit_resa and utilisateur_resa:
        if salle_raman_resa:
            reserver(str(debut_resa), str(fin_resa), "Raman", utilisateur_resa)
        if salle_fluo_resa:
            reserver(str(debut_resa), str(fin_resa), "Fluorescence inversé", utilisateur_resa)

st.header("Annuler une réservation")
with st.form("annulation_form"):
    utilisateur_annul = st.text_input("Nom de l'utilisateur pour annulation", key="annul_user")
    debut_annul = st.datetime_input("Début de la réservation à annuler", key="annul_debut")
    fin_annul = st.datetime_input("Fin de la réservation à annuler", key="annul_fin")
    salle_raman_annul = st.checkbox("Salle Raman", key="annul_raman")
    salle_fluo_annul = st.checkbox("Salle Fluorescence inversé", key="annul_fluo")
    submit_annul = st.form_submit_button("Annuler")
    if submit_annul and utilisateur_annul:
        if salle_raman_annul:
            annuler(str(debut_annul), str(fin_annul), "Raman", utilisateur_annul)
        if salle_fluo_annul:
            annuler(str(debut_annul), str(fin_annul), "Fluorescence inversé", utilisateur_annul)

st.header("Historique des réservations et annulations")
histo = pd.read_csv(HISTORIQUE_FILE)
st.dataframe(histo.sort_values(by=["Timestamp_resa", "Timestamp_annulation"], ascending=False))
