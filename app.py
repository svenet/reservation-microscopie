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
    df["Début"] = pd.to_datetime(df["Début"], errors='coerce')
    df["Fin"] = pd.to_datetime(df["Fin"], errors='coerce')
    df = df.dropna(subset=["Début", "Fin"]).reset_index(drop=True)
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
    df_out.to_csv(RESERVATION_FILE, index=False)
    histo = pd.read_csv(HISTORIQUE_FILE)
    entry = ["Réservation", debut.isoformat(), fin.isoformat(), salle, utilisateur, timestamp, ""]
    histo = pd.concat([histo, pd.DataFrame([entry], columns=NEW_HISTO_COLS)], ignore_index=True)
    histo.to_csv(HISTORIQUE_FILE, index=False)
    st.success(f"Réservation enregistrée pour la salle {salle}.")


def annuler(debut, fin, salle, utilisateur):
    # ... (inchangé) ...
    df = pd.read_csv(RESERVATION_FILE)
    df["Début"] = pd.to_datetime(df["Début"], errors='coerce')
    df["Fin"] = pd.to_datetime(df["Fin"], errors='coerce')
    df = df.dropna(subset=["Début", "Fin"]).reset_index(drop=True)
    mask_user = (df["Salle"] == salle) & (df["Utilisateur"] == utilisateur)
    to_process = df[mask_user]
    updated, removed = [], []
    for _, row in to_process.iterrows():
        r_start, r_end = row["Début"], row["Fin"]
        # ... logique inchangée ...
        if fin <= r_start or debut >= r_end:
            updated.append(row)
        elif debut <= r_start and fin >= r_end:
            removed.append((r_start, r_end))
        elif debut <= r_start < fin < r_end:
            updated.append({"Début": fin, "Fin": r_end, "Salle": salle, "Utilisateur": utilisateur, "Timestamp_resa": row["Timestamp_resa"]})
            removed.append((r_start, fin))
        elif r_start < debut < r_end <= fin:
            updated.append({"Début": r_start, "Fin": debut, "Salle": salle, "Utilisateur": utilisateur, "Timestamp_resa": row["Timestamp_resa"]})
            removed.append((debut, r_end))
        elif r_start < debut and fin < r_end:
            updated.append({"Début": r_start, "Fin": debut, "Salle": salle, "Utilisateur": utilisateur, "Timestamp_resa": row["Timestamp_resa"]})
            updated.append({"Début": fin, "Fin": r_end, "Salle": salle, "Utilisateur": utilisateur, "Timestamp_resa": row["Timestamp_resa"]})
            removed.append((debut, fin))
    others = df[~mask_user]
    df_out = pd.concat([others, pd.DataFrame(updated)], ignore_index=True) if updated else others
    df_out.to_csv(RESERVATION_FILE, index=False)
    histo = pd.read_csv(HISTORIQUE_FILE)
    timestamp = datetime.now().isoformat()
    for rem in removed:
        histo = pd.concat([histo, pd.DataFrame([["Annulation", rem[0].isoformat(), rem[1].isoformat(), salle, utilisateur, "", timestamp]], columns=NEW_HISTO_COLS)], ignore_index=True)
    histo.to_csv(HISTORIQUE_FILE, index=False)
    st.success(f"Annulation effectuée pour la salle {salle}.")

# Affichage des calendriers hebdomadaires
def display_weekly_calendar(start_week: date):
    days = [start_week + timedelta(days=i) for i in range(7)]
    day_labels = [d.strftime('%a %d/%m') for d in days]
    df = pd.read_csv(RESERVATION_FILE)
    if not df.empty:
        df['Début'] = pd.to_datetime(df['Début'], errors='coerce')
        df['Fin'] = pd.to_datetime(df['Fin'], errors='coerce')
        df = df.dropna(subset=['Début', 'Fin']).reset_index(drop=True)
    for salle in ["Raman", "Fluorescence inversé"]:
        cal = pd.DataFrame(index=HOUR_LABELS, columns=day_labels).fillna("Libre")
        for _, row in df[df['Salle']==salle].iterrows():
            for d, label in zip(days, day_labels):
                for h, h_lbl in zip(HOURS, HOUR_LABELS):
                    slot_start = datetime.combine(d, time(h,0)); slot_end = slot_start+timedelta(hours=1)
                    if row['Début']<slot_end and row['Fin']>slot_start:
                        cal.at[h_lbl,label]="Occupé"
        st.subheader(f"Disponibilités ({day_labels[0]} - {day_labels[-1]}) - {salle}")
        styled = cal.style.applymap(lambda v: 'color:white; background:red' if v=='Occupé' else '')
        st.write(styled)  # preserve styling

# Excel: générer et télécharger en un seul bouton
def generate_summary_excel(df_resa, start_date, end_date):
    df_resa['Début'] = pd.to_datetime(df_resa['Début'], errors='coerce')
    df_resa['Fin'] = pd.to_datetime(df_resa['Fin'], errors='coerce')
    df_resa = df_resa.dropna(subset=['Début','Fin'])
    mask = (df_resa['Début'].dt.date>=start_date)&(df_resa['Fin'].dt.date<=end_date)
    df_period = df_resa[mask].copy()
    df_period['Durée_h']=(df_period['Fin']-df_period['Début']).dt.total_seconds()/3600
    summary=df_period.groupby(['Utilisateur','Salle'])['Durée_h'].sum().reset_index().rename(columns={'Durée_h':'Total_Heures'})
    out=BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as w: summary.to_excel(w,index=False,sheet_name='Résumé')
    return out.getvalue()

# --- Application Streamlit ---
init_files()
st.title("Réservation des salles de microscopie")

# Calendrier
week_start=st.date_input("Semaine du",value=date.today()-timedelta(days=date.today().weekday()))
display_weekly_calendar(week_start)

# Réservation & annulation (inchangés)
st.header("Nouvelle réservation")
# ... code forms ...

# Export Excel
st.header("Rapport de réservations Excel")
col1,col2=st.columns(2)
with col1: rs=st.date_input("Début",value=date.today()-timedelta(days=7))
with col2: re=st.date_input("Fin",value=date.today())
download_data=generate_summary_excel(pd.read_csv(RESERVATION_FILE),rs,re)
st.download_button("Télécharger .xlsx",data=download_data,file_name=f"rapports_{rs}_{re}.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# Historique
st.header("Historique")
st.dataframe(pd.read_csv(HISTORIQUE_FILE).sort_values(["Timestamp_resa","Timestamp_annulation"],ascending=False))
