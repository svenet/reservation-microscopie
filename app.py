#!/usr/bin/python3

import streamlit as st
import pandas as pd
import os
from datetime import datetime, time, date

RESERVATION_FILE = "reservations.csv"
HISTORIQUE_FILE = "historique.csv"
NEW_RESA_COLS = ["Début", "Fin", "Salle", "Utilisateur", "Timestamp_resa"]
NEW_HISTO_COLS = ["Action", "Début", "Fin", "Salle", "Utilisateur", "Timestamp_resa", "Timestamp_annulation"]

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
    # Sélectionner les réservations de l'utilisateur et de la salle
    mask_user = (df["Salle"] == salle) & (df["Utilisateur"] == utilisateur)
    to_process = df[mask_user]
    updated = []
    removed = []
    for _, row in to_process.iterrows():
        r_start = row["Début"]
        r_end = row["Fin"]
        # aucun chevauchement
        if fin <= r_start or debut >= r_end:
            updated.append(row)
            continue
        # annulation recouvre tout
        if debut <= r_start and fin >= r_end:
            removed.append((r_start, r_end))
            continue
        # annulation en début de réservation
        if debut <= r_start < fin < r_end:
            new_start = fin
            updated.append({"Début": new_start, "Fin": r_end, "Salle": salle, "Utilisateur": utilisateur, "Timestamp_resa": row["Timestamp_resa"]})
            removed.append((r_start, fin))
            continue
        # annulation en fin de réservation
        if r_start < debut < r_end <= fin:
            new_end = debut
            updated.append({"Début": r_start, "Fin": new_end, "Salle": salle, "Utilisateur": utilisateur, "Timestamp_resa": row["Timestamp_resa"]})
            removed.append((debut, r_end))
            continue
        # annulation au milieu -> split en deux
        if r_start < debut and fin < r_end:
            updated.append({"Début": r_start, "Fin": debut, "Salle": salle, "Utilisateur": utilisateur, "Timestamp_resa": row["Timestamp_resa"]})
            updated.append({"Début": fin, "Fin": r_end, "Salle": salle, "Utilisateur": utilisateur, "Timestamp_resa": row["Timestamp_resa"]})
            removed.append((debut, fin))
            continue
    # Reconstruire df
    others = df[~mask_user]
    # préparer updated dataframe
    if updated:
        df_updated = pd.DataFrame(updated)
        df_updated["Début"] = df_updated["Début"].astype(str)
        df_updated["Fin"] = df_updated["Fin"].astype(str)
        df_out = pd.concat([others, df_updated], ignore_index=True)
    else:
        df_out = others.copy()
    df_out.to_csv(RESERVATION_FILE, index=False)
    # Historique des annulations partielles
    histo = pd.read_csv(HISTORIQUE_FILE)
    timestamp = datetime.now().isoformat()
    for rem in removed:
        entry = ["Annulation partielle", rem[0].isoformat(), rem[1].isoformat(), salle, utilisateur, "", timestamp]
        histo = pd.concat([histo, pd.DataFrame([entry], columns=NEW_HISTO_COLS)], ignore_index=True)
    histo.to_csv(HISTORIQUE_FILE, index=False)
    st.success(f"Annulation effectuée pour l'intervalle spécifié sur la salle {salle}.")

# --- Application Streamlit ---
init_files()
st.title("Réservation des salles de microscopie")

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

st.header("Historique des réservations et annulations")
histo = pd.read_csv(HISTORIQUE_FILE)
st.dataframe(histo.sort_values(by=["Timestamp_resa", "Timestamp_annulation"], ascending=False))
