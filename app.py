import streamlit as st
from pathlib import Path
import PIL.Image
import io
from google import genai
import json
import fitz  
import time  

# ==========================================
# 1. INITIALISATION DE LA MÉMOIRE & API
# ==========================================
if 'pic_anomalies' not in st.session_state:
    st.session_state.pic_anomalies = None
if 'cctp_contraintes' not in st.session_state:
    st.session_state.cctp_contraintes = None
if 'cadrage_resultat' not in st.session_state:
    st.session_state.cadrage_resultat = None
if 'rapport_audit' not in st.session_state:
    st.session_state.rapport_audit = None

try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except FileNotFoundError:
    st.error("⚠️ Fichier secrets.toml introuvable. Avez-vous créé le dossier .streamlit ?")
    st.stop()

st.set_page_config(
    page_title="Agent Méthodes - CADS-UP", 
    page_icon="logo_cads_up.png",
    layout="wide"
)

# ==========================================
# BARRE LATÉRALE (BRANDING ENTREPRISE)
# ==========================================
with st.sidebar:
    try:
        st.image("logo_cads_up.png", use_container_width=True)
    except FileNotFoundError:
        st.error("⚠️ Placez votre image 'logo_cads_up.png' dans le dossier principal.")
    
    st.markdown("### CADS-UP")
    st.markdown("**Ingénierie des Méthodes & Planification**")
    st.markdown("📍 *[36, Rue Victor Basch 91300 MASSY]*")
    st.markdown("---")
    st.info("🤖 Agent IA d'Assistance Méthodes")
    st.caption("Modules actifs : PIC, CCTP, Cadrage, Audit, E-mail.")

st.title("🏗️ Assistant IA - Ingénierie Méthodes")

dossier_analyse = Path("repertoire_analyse")
dossier_analyse.mkdir(parents=True, exist_ok=True)

extensions_valides = ['.jpg', '.jpeg', '.png', '.pdf']
fichiers_a_traiter = [f for f in dossier_analyse.iterdir() if f.is_file() and f.suffix.lower() in extensions_valides]

# Création des 5 Onglets
onglet_pic, onglet_cctp, onglet_cadrage, onglet_audit, onglet_email = st.tabs([
    "🗺️ Analyse PIC", 
    "📄 Analyse CCTP", 
    "📐 Cadrage Avant-Projet",
    "⚖️ Audit Croisé", 
    "✉️ Assistant E-mail"
])

# ==========================================
# ONGLET 1 : ANALYSE VISUELLE (PIC)
# ==========================================
with onglet_pic:
    st.header("Analyse Visuelle de Plans d'Installation")
    if not fichiers_a_traiter:
        st.warning("Le dossier de dépôt est vide.")
    else:
        noms_fichiers = [f.name for f in fichiers_a_traiter]
        fichier_selectionne = st.selectbox("Sélectionnez le plan à analyser :", noms_fichiers, key="select_pic")
        chemin_complet = dossier_analyse / fichier_selectionne
        
        if fichier_selectionne.lower().endswith('.pdf'):
            document_pdf = fitz.open(chemin_complet)
            page_choisie = st.number_input(f"Ce PDF contient {len(document_pdf)} page(s). Laquelle analyser ?", min_value=1, max_value=len(document_pdf), value=1)
            pix = document_pdf.load_page(page_choisie - 1).get_pixmap(dpi=300)
            image_plan = PIL.Image.open(io.BytesIO(pix.tobytes("png")))
            st.image(image_plan, caption=f"Aperçu PDF - Page {page_choisie}", use_container_width=True)
        else:
            image_plan = PIL.Image.open(chemin_complet)
            st.image(image_plan, caption=f"Plan en cours d'analyse : {fichier_selectionne}", use_container_width=True)

        prompt_systeme_pic = """
        Tu es un ingénieur méthodes. Analyse ce PIC sur 4 critères: Clôtures, Flux, Levage, Signalétique.
        RÈGLE ABSOLUE : Réponds UNIQUEMENT au format JSON.
        [
          {"Critère": "...", "Anomalie": "...", "Risque": "CRITIQUE, MAJEUR, MINEUR", "Action_Corrective": "..."}
        ]
        """

        if st.button("Scanner le plan et générer le tableau de bord"):
            with st.spinner("Analyse technique en cours..."):
                for tentative in range(3):
                    try:
                        response = client.models.generate_content(model='gemini-3.6-flash', contents=[image_plan, prompt_systeme_pic])
                        texte_nettoye = response.text.replace('```json', '').replace('```', '').strip()
                        donnees_json = json.loads(texte_nettoye)
                        st.session_state.pic_anomalies = donnees_json
                        break
                    except Exception as e:
                        if "503" in str(e) and tentative < 2:
                            time.sleep(3)
                        elif tentative == 2:
                            st.error("L'API est saturée après 3 tentatives.")
                        else:
                            st.error(f"Erreur technique : {e}")
                            break

        # AFFICHAGE PERSISTANT (Reste visible même en changeant d'onglet)
        if st.session_state.pic_anomalies is not None:
            st.subheader("📊 Tableau de Bord des Anomalies (En mémoire)")
            if st.session_state.pic_anomalies:
                st.dataframe(st.session_state.pic_anomalies, use_container_width=True)
            else:
                st.success("Aucune anomalie détectée.")

# ==========================================
# ONGLET 2 : ANALYSE DOCUMENTAIRE (CCTP)
# ==========================================
with onglet_cctp:
    st.header("Extraction de données depuis CCTP / PGC")
    fichiers_pdf = [f for f in fichiers_a_traiter if f.name.lower().endswith('.pdf')]
    if not fichiers_pdf:
        st.info("Déposez un PDF textuel dans le dossier.")
    else:
        pdf_selectionne = st.selectbox("Sélectionnez le document à lire :", [f.name for f in fichiers_pdf], key="select_cctp")
        
        if st.button("Lire le document et extraire les contraintes"):
            with st.spinner("Lecture en cours..."):
                texte_complet = "".join([page.get_text() for page in fitz.open(dossier_analyse / pdf_selectionne)])
                prompt_cctp = "Extrais en liste à puces : 1. Phasage/Délai 2. Matériaux imposés 3. Contraintes d'installation de chantier. Sois très concis."
                
                for tentative in range(3):
                    try:
                        response = client.models.generate_content(model='gemini-3.6-flash', contents=[f"{prompt_cctp}\n\n{texte_complet}"])
                        st.session_state.cctp_contraintes = response.text
                        break
                    except Exception as e:
                        if "503" in str(e) and tentative < 2:
                            time.sleep(3)
                        elif tentative == 2:
                            st.error("L'API est saturée après 3 tentatives.")
                        else:
                            st.error(f"Erreur : {e}")
                            break

        # AFFICHAGE PERSISTANT
        if st.session_state.cctp_contraintes:
            st.subheader("📄 Contraintes CCTP (En mémoire)")
            st.write(st.session_state.cctp_contraintes)

# ==========================================
# ONGLET 3 : CADRAGE AVANT-PROJET
# ==========================================
with onglet_cadrage:
    st.header("📐 Note de Cadrage Logistique (Avant-Projet)")
    st.write("Génère les directives de dimensionnement à partir des contraintes du CCTP.")
    
    if st.session_state.cctp_contraintes:
        st.success("✅ Contraintes du CCTP chargées en mémoire.")
        effectif_estime = st.number_input("Effectif maximum estimé en pointe :", min_value=1, value=20)
        
        if st.button("Générer la Note de Cadrage pour le Projeteur"):
            with st.spinner("Génération des directives de dimensionnement..."):
                prompt_cadrage = f"""
                Tu es l'ingénieur méthodes principal. Rédige une "Note de Cadrage PIC" formelle destinée au projeteur.
                Voici les contraintes du CCTP : {st.session_state.cctp_contraintes}
                L'effectif pointe estimé est de {effectif_estime} compagnons.
                Structure avec : 1. DIMENSIONNEMENT BASE VIE, 2. STRATÉGIE DE LEVAGE, 3. ZONAGE ET FLUX. Directif et concis.
                """
                for tentative in range(3):
                    try:
                        reponse_cadrage = client.models.generate_content(model='gemini-3.6-flash', contents=[prompt_cadrage])
                        st.session_state.cadrage_resultat = reponse_cadrage.text
                        break
                    except Exception as e:
                        if "503" in str(e) and tentative < 2:
                            time.sleep(3)
                        elif tentative == 2:
                            st.error("L'API est saturée après 3 tentatives.")
                        else:
                            st.error(f"Erreur : {e}")
                            break

        # AFFICHAGE PERSISTANT
        if st.session_state.cadrage_resultat:
            st.subheader("📋 Note de Cadrage (En mémoire)")
            st.markdown(st.session_state.cadrage_resultat)
    else:
        st.warning("⚠️ Action impossible. Extrayez d'abord un CCTP dans l'onglet 'Analyse CCTP'.")

# ==========================================
# ONGLET 4 : AUDIT CROISÉ
# ==========================================
with onglet_audit:
    st.header("⚖️ Audit de Conformité : PIC vs CCTP")
    
    if st.session_state.pic_anomalies and st.session_state.cctp_contraintes:
        st.success("✅ Données du PIC et du CCTP disponibles en mémoire.")
        
        if st.button("Lancer la confrontation PIC / CCTP"):
            with st.spinner("Audit croisé en cours..."):
                prompt_audit = f"""
                Confronte le plan d'installation (PIC) aux exigences du cahier des charges (CCTP).
                Anomalies du PIC : {json.dumps(st.session_state.pic_anomalies, ensure_ascii=False)}
                Exigences du CCTP : {st.session_state.cctp_contraintes}
                Dresse un bilan critique : 1. Conflits directs 2. Oublis. Sois factuel, chirurgical et direct. Puces.
                """
                for tentative in range(3):
                    try:
                        reponse_audit = client.models.generate_content(model='gemini-3.6-flash', contents=[prompt_audit])
                        st.session_state.rapport_audit = reponse_audit.text
                        break
                    except Exception as e:
                        if "503" in str(e) and tentative < 2:
                            time.sleep(3)
                        elif tentative == 2:
                            st.error("L'API est saturée après 3 tentatives.")
                        else:
                            st.error(f"Erreur : {e}")
                            break

        # AFFICHAGE PERSISTANT
        if st.session_state.rapport_audit:
            st.subheader("📊 Rapport d'Audit Croisé (En mémoire)")
            st.markdown(st.session_state.rapport_audit)
    else:
        st.warning("⚠️ Analysez un PIC (Onglet 1) ET un CCTP (Onglet 2) pour activer l'audit.")

# ==========================================
# ONGLET 5 : ASSISTANT EMAIL
# ==========================================
with onglet_email:
    st.header("✉️ Assistant de Rédaction Professionnelle")
    
    col1, col2 = st.columns(2)
    with col1:
        destinataire = st.selectbox("À qui s'adresse cet e-mail ?", [
            "Équipe interne / Projeteur", 
            "Sous-traitant / Fournisseur", 
            "Maîtrise d'Œuvre / Architecte"
        ])
    
    source_donnees = st.radio("Sur quoi porte cet e-mail ?", [
        "Transmettre l'Audit de Conformité (PIC vs CCTP)",
        "Transmettre le rapport brut d'anomalies du PIC",
        "Saisir des notes libres"
    ])
    
    donnees_prompt = ""
    if source_donnees == "Saisir des notes libres":
        donnees_prompt = st.text_area("Vos mots-clés :", height=100)
    elif source_donnees == "Transmettre le rapport brut d'anomalies du PIC":
        if st.session_state.pic_anomalies:
            donnees_prompt = json.dumps(st.session_state.pic_anomalies, ensure_ascii=False)
        else:
            st.warning("⚠️ Aucun rapport PIC en mémoire.")
    elif source_donnees == "Transmettre l'Audit de Conformité (PIC vs CCTP)":
        if st.session_state.rapport_audit:
            donnees_prompt = st.session_state.rapport_audit
        else:
            st.warning("⚠️ Aucun rapport d'audit croisé en mémoire.")

    if st.button("Rédiger l'e-mail"):
        if not donnees_prompt.strip():
            st.error("Erreur : Aucune information à rédiger.")
        else:
            with st.spinner("Rédaction en cours..."):
                prompt_email = f"""
                Tu es ingénieur méthodes. Rédige un e-mail professionnel basé sur : {donnees_prompt}.
                Destinataire : {destinataire}. Ton froid, direct, exigeant des actions correctives. Objet inclus.
                """
                for tentative in range(3):
                    try:
                        response_email = client.models.generate_content(model='gemini-3.6-flash', contents=[prompt_email])
                        st.text_area("Résultat :", response_email.text, height=300)
                        break
                    except Exception as e:
                        if "503" in str(e) and tentative < 2:
                            time.sleep(3)
                        elif tentative == 2:
                            st.error("L'API est saturée après 3 tentatives.")
                        else:
                            st.error(f"Erreur : {e}")
                            break