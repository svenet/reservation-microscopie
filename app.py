#!/usr/bin/python3

import streamlit as st
import pandas as pd
import os
from datetime import datetime, time, date

RESERVATION_FILE = "reservations.csv"
HISTORIQUE_FILE = "historique.csv"
NEW_RESA_COLS = ["Début", "Fin", "Salle", "Utilisateur", "Timestamp_resa"]
NEW_HISTO_COLS = ["Action", "Début", "Fin", "Salle", "Utilisateur", "Timestamp_resa", "Timestamp_annulation"]

# Initialisation des fichiers CSV avec migration si ancien format détecté

def init_files():
    # Réservations
    if os.path.exists(RESERVATION_FILE):
        df = pd.read_csv(RESERVATION_FILE)
        # Si colonnes anciennes ou manquantes, réinitialiser
        if not all(col in df.columns for col in NEW_RESA_COLS):
            st.warning("Ancien fichier de réservations détecté : réinitialisation du fichier.")
            pd.DataFrame(columns=NEW_RESA_COLS).to_csv(RESERVATION_FILE, index=False)
    else:
        pd.DataFrame(columns=NEW_RESA_COLS).to_csv(RESERVATION_FILE, index=False)

    # Historique
    if os.path.exists(HISTORIQUE_FILE):
        dfh = pd.read_csv(HISTORIQUE_FILE)
        if not all(col in dfh.columns for col in NEW_HISTO_COLS):
            st.warning("Ancien fichier d'historique détecté : réinitialisation du fichier.")
            pd.DataFrame(columns=NEW_HISTO_COLS).to_csv(HISTORIQUE_FILE, index=False)
    else:
        pd.DataFrame(columns=NEW_HISTO_COLS).to_csv(HISTORIQUE_FILE, index=False)


def reserver(debut, fin, salle, utilisateur):
    df = pd.read_csv(RESERVATION_FILE)
    # Vérification de conflit
    conflit = df[(df["Salle"] == salle) & (
        ((pd.to_datetime(df["Début"]) <= debut) & (pd.to_datetime(df["Fin"]) > debut)) |
        ((pd.to_datetime(df["Début"]) < fin) & (pd.to_datetime(df["Fin"]) >= fin)) |
        ((pd.to_datetime(df["Début"]) >= debut) & (pd.to_datetime(df["Fin"]) <= fin))
    )]
    if not conflit.empty:
        st.warning(f"Un conflit de réservation existe déjà pour la salle {salle} à cette période.")
        return
    # Enregistrement
    timestamp = datetime.now().isoformat()
    new_resa = pd.DataFrame([[debut.isoformat(), fin.isoformat(), salle, utilisateur, timestamp]], columns=NEW_RESA_COLS)
    df = pd.concat([df, new_resa], ignore_index=True)
    df.to_csv(RESERVATION_FILE, index=False)
    # Historique
    histo = pd.read_csv(HISTORIQUE_FILE)
    entry = ["Réservation", debut.isoformat(), fin.isoformat(), salle, utilisateur, timestamp, ""]
    histo = pd.concat([histo, pd.DataFrame([entry], columns=NEW_HISTO_COLS)], ignore_index=True)
    histo.to_csv(HISTORIQUE_FILE, index=False)
    st.success(f"Réservation enregistrée pour la salle {salle}.")


def annuler(debut, fin, salle, utilisateur):
    df = pd.read_csv(RESERVATION_FILE)
    mask = (df["Début"] == debut.isoformat()) & (df["Fin"] == fin.isoformat()) & (df["Salle"] == salle) & (df["Utilisateur"] == utilisateur)
    if not mask.any():
        st.warning(f"Réservation non trouvée pour la salle {salle}.")
        return
    df = df[~mask]
    df.to_csv(RESERVATION_FILE, index=False)
    timestamp = datetime.now().isoformat()
    histo = pd.read_csv(HISTORIQUE_FILE)
    entry = ["Annulation", debut.isoformat(), fin.isoformat(), salle, utilisateur, "", timestamp]
    histo = pd.concat([histo, pd.DataFrame([entry], columns=NEW_HISTO_COLS)], ignore_index=True)
    histo.to_csv(HISTORIQUE_FILE, index=False)
    st.success(f"Réservation annulée pour la salle {salle}.")

# --- Application Streamlit ---
init_files()
st.title("Réservation des salles de microscopie")

# Formulaire de réservation
st.header("Nouvelle réservation")
with st.form("reservation_form"):
    utilisateur_resa = st.text_input("Nom de l'utilisateur", key="resa_user")
    date_debut = st.date_input("Date de début", key="resa_date_debut")
    heure_debut = st.time_input("Heure de début", key="resa_time_debut")
    date_fin = st.date_input("Date de fin", key="resa_date_fin")
    heure_fin = st.time_input("Heure de fin", key="resa_time_fin")
    salle_raman = st.checkbox("Salle Raman", key="resa_raman")
    salle_fluo = st.checkbox("Salle Fluorescence inversé", key="resa_fluo")
    submit_resa = st.form_submit_button("Réserver")
    if submit_resa and utilisateur_resa:
        debut_dt = datetime.combine(date_debut, heure_debut)
        fin_dt = datetime.combine(date_fin, heure_fin)
        if fin_dt <= debut_dt:
            st.error("La date/heure de fin doit être après la date/heure de début.")
        else:
            if salle_raman:
                reserver(debut_dt, fin_dt, "Raman", utilisateur_resa)
            if salle_fluo:
                reserver(debut_dt, fin_dt, "Fluorescence inversé", utilisateur_resa)

# Formulaire d'annulation
st.header("Annuler une réservation")
with st.form("annulation_form"):
    utilisateur_annul = st.text_input("Nom de l'utilisateur pour annulation", key="annul_user")
    date_debut_a = st.date_input("Date de début à annuler", key="annul_date_debut")
    heure_debut_a = st.time_input("Heure de début à annuler", key="annul_time_debut")
    date_fin_a = st.date_input("Date de fin à annuler", key="annul_date_fin")
    heure_fin_a = st.time_input("Heure de fin à annuler", key="annul_time_fin")
    salle_raman_a = st.checkbox("Salle Raman", key="annul_raman")
    salle_fluo_a = st.checkbox("Salle Fluorescence inversé", key="annul_fluo")
    submit_annul = st.form_submit_button("Annuler")
    if submit_annul and utilisateur_annul:
        debut_a = datetime.combine(date_debut_a, heure_debut_a)
        fin_a = datetime.combine(date_fin_a, heure_fin_a)
        if fin_a <= debut_a:
            st.error("La date/heure de fin doit être après la date/heure de début.")
        else:
            if salle_raman_a:
                annuler(debut_a, fin_a, "Raman", utilisateur_annul)
            if salle_fluo_a:
                annuler(debut_a, fin_a, "Fluorescence inversé", utilisateur_annul)

# Affichage de l'historique
st.header("Historique des réservations et annulations")
histo = pd.read_csv(HISTORIQUE_FILE)
st.dataframe(histo.sort_values(by=["Timestamp_resa", "Timestamp_annulation"], ascending=False))
