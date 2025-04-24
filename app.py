#!/usr/bin/python3

import streamlit as st
import pandas as pd
import os
from datetime import datetime, time, date, timedelta
from io import BytesIO

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

# Fonctions de gestion des réservations
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
        r_start = row["Début"]
        r_end = row["Fin"]
        if fin <= r_start or debut >= r_end:
            updated.append(row)
            continue
        if debut <= r_start and fin >= r_end:
            removed.append((r_start, r_end))
            continue
        if debut <= r_start < fin < r_end:
            updated.append({"Début": fin, "Fin": r_end, "Salle": salle, "Utilisateur": utilisateur, "Timestamp_resa": row["Timestamp_resa"]})
            removed.append((r_start, fin))
            continue
        if r_start < debut < r_end <= fin:
            updated.append({"Début": r_start, "Fin": debut, "Salle": salle, "Utilisateur": utilisateur, "Timestamp_resa": row["Timestamp_resa"]})
            removed.append((debut, r_end))
            continue
        if r_start < debut and fin < r_end:
            updated.append({"Début": r_start, "Fin": debut, "Salle": salle, "Utilisateur": utilisateur, "Timestamp_resa": row["Timestamp_resa"]})
            updated.append({"Début": fin, "Fin": r_end, "Salle": salle, "Utilisateur": utilisateur, "Timestamp_resa": row["Timestamp_resa"]})
            removed.append((debut, fin))
            continue
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
        entry = ["Annulation", rem[0].isoformat(), rem[1].isoformat(), salle, utilisateur, "", timestamp]
        histo = pd.concat([histo, pd.DataFrame([entry], columns=NEW_HISTO_COLS)], ignore_index=True)
    histo.to_csv(HISTORIQUE_FILE, index=False)
    st.success(f"Annulation effectuée pour l'intervalle spécifié sur la salle {salle}.")

# --- Nouvelle fonctionnalité : export Excel des durées réservées ---

def generate_summary_excel(df_resa, start_date, end_date):
    # Filtrer selon la période
    df_resa['Début'] = pd.to_datetime(df_resa['Début'])
    df_resa['Fin'] = pd.to_datetime(df_resa['Fin'])
    mask = (df_resa['Début'].dt.date >= start_date) & (df_resa['Fin'].dt.date <= end_date)
    df_period = df_resa.loc[mask].copy()
    # Calcul de la durée en heures
    df_period['Durée_h'] = (df_period['Fin'] - df_period['Début']).dt.total_seconds() / 3600
    # Agrégation par utilisateur et salle
    summary = df_period.groupby(['Utilisateur', 'Salle'])['Durée_h'].sum().reset_index()
    summary = summary.rename(columns={'Durée_h': 'Total_Heures'})
    # Création d'un fichier Excel en mémoire
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        summary.to_excel(writer, index=False, sheet_name='Résumé')
    processed_data = output.getvalue()
    return processed_data

# --- Application Streamlit ---
init_files()
st.title("Réservation des salles de microscopie")

# Sélecteur de période pour le rapport Excel
st.header("Rapport de réservations Excel")
col1, col2 = st.columns(2)
with col1:
    report_start = st.date_input("Date de début du rapport", value=date.today() - timedelta(days=7))
with col2:
    report_end = st.date_input("Date de fin du rapport", value=date.today())

if st.button("Générer et télécharger le rapport Excel"):
    df_resa = pd.read_csv(RESERVATION_FILE)
    excel_data = generate_summary_excel(df_resa, report_start, report_end)
    st.download_button(
        label="Télécharger le rapport .xlsx",
        data=excel_data,
        file_name=f"rapport_reservations_{report_start}_{report_end}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Affichage de l'historique existant
st.header("Historique des réservations et annulations")
histo = pd.read_csv(HISTORIQUE_FILE)
st.dataframe(histo.sort_values(by=["Timestamp_resa", "Timestamp_annulation"], ascending=False))
