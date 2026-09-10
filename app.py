import streamlit as st
import PIL.Image
import io
from google import genai
import json
import fitz  # PyMuPDF
import time
from pathlib import Path

# Outils pour la génération de PDF natifs
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

# Configuration adaptée aux smartphones
st.set_page_config(page_title="CADS-UP Méthodes", page_icon="🏗️", layout="centered")

# =========================================================
# 1. SÉCURISATION DE L'ACCÈS
# =========================================================
def verifier_acces():
    if "authentifie" not in st.session_state:
        st.session_state.authentifie = False

    if not st.session_state.authentifie:
        st.subheader("🔒 Accès Restreint - CADS-UP")
        st.caption("Ingénierie des Méthodes & Planification")
        
        mot_de_passe_saisi = st.text_input("Mot de passe :", type="password")
        # Récupère le mot de passe depuis les secrets Streamlit
        mot_de_passe_attendu = st.secrets.get("APP_PASSWORD", "CADSUP2026")
        
        if st.button("Connexion", use_container_width=True):
            if mot_de_passe_saisi == mot_de_passe_attendu:
                st.session_state.authentifie = True
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")
        st.stop()

verifier_acces()

# Gestion de la sidebar
with st.sidebar:
    # Vérification stricte pour éviter l'erreur MediaFileStorageError
    if Path("logo_cads_up.png").is_file():
        st.image("logo_cads_up.png", use_container_width=True)
    st.write("**CADS-UP Méthodes**")
    if st.button("Se déconnecter"):
        st.session_state.authentifie = False
        st.rerun()

# =========================================================
# 2. FONCTION UTILITAIRE : GÉNÉRATION DU RAPPORT PDF
# =========================================================
def creer_rapport_pdf(titre_document, section_nom, contenu_texte, tableau_donnees=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    elements = []
    styles = getSampleStyleSheet()

    style_titre = ParagraphStyle('TitreCADS', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor("#1A365D"), spaceAfter=10)
    style_sous_titre = ParagraphStyle('SousTitreCADS', parent=styles['Heading2'], fontSize=13, leading=16, textColor=colors.HexColor("#2B6CB0"), spaceAfter=12)
    style_corps = ParagraphStyle('CorpsCADS', parent=styles['Normal'], fontSize=10, leading=14, textColor=colors.HexColor("#2D3748"))

    elements.append(Paragraph("CADS-UP - INGÉNIERIE MÉTHODES", style_titre))
    elements.append(Paragraph(f"<b>Rapport :</b> {titre_document}", style_sous_titre))
    elements.append(Paragraph(f"<i>Édité le : {time.strftime('%d/%m/%Y à %H:%M')}</i>", style_corps))
    elements.append(Spacer(1, 15))

    if tableau_donnees and len(tableau_donnees) > 0:
        elements.append(Paragraph("<b>Tableau des Anomalies & Actions Correctives</b>", style_sous_titre))
        en_tetes = [Paragraph(f"<b>{k}</b>", style_corps) for k in tableau_donnees[0].keys()]
        lignes = [en_tetes]
        
        for item in tableau_donnees:
            ligne = [Paragraph(str(v), style_corps) for v in item.values()]
            lignes.append(ligne)
            
        t = Table(lignes, colWidths=[100, 150, 90, 180])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#718096")),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 15))

    if contenu_texte:
        elements.append(Paragraph(f"<b>{section_nom}</b>", style_sous_titre))
        for ligne in contenu_texte.split("\n"):
            if ligne.strip():
                elements.append(Paragraph(ligne.strip(), style_corps))
                elements.append(Spacer(1, 4))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# =========================================================
# 3. INITIALISATION DE L'AGENT IA & SESSION
# =========================================================
if 'pic_anomalies' not in st.session_state: st.session_state.pic_anomalies = None
if 'cctp_contraintes' not in st.session_state: st.session_state.cctp_contraintes = None
if 'cadrage_resultat' not in st.session_state: st.session_state.cadrage_resultat = None
if 'rapport_audit' not in st.session_state: st.session_state.rapport_audit = None

try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error("⚠️ Clé GEMINI_API_KEY introuvable dans les secrets Streamlit.")
    st.stop()

def appeler_gemini(contenu, tentative_max=3):
    for i in range(tentative_max):
        try:
            # Remplacement strict par gemini-3.6-flash
            return client.models.generate_content(model='gemini-3.6-flash', contents=contenu)
        except Exception as e:
            if "503" in str(e) and i < tentative_max - 1:
                time.sleep(2)
            else:
                st.error(f"Erreur technique : {e}")
                return None

st.title("🏗️ CADS-UP Mobile")

onglet_pic, onglet_cctp, onglet_cadrage, onglet_audit, onglet_email, onglet_3d = st.tabs([
    "🗺️ PIC", "📄 CCTP", "📐 Cadrage", "⚖️ Audit", "✉️ E-mail", "🧊 3D"
])

# =========================================================
# ONGLET 1 : PIC
# =========================================================
with onglet_pic:
    st.subheader("Analyse Visuelle de Plan (PIC)")
    mode_acquisition = st.radio("Source de l'image :", ["📸 Appareil photo", "📁 Fichier (PDF / Image)"], horizontal=True)
    image_plan = None

    if mode_acquisition == "📸 Appareil photo":
        photo_capturee = st.camera_input("Prendre une photo")
        if photo_capturee:
            image_plan = PIL.Image.open(photo_capturee)
    else:
        fichier_importe = st.file_uploader("Sélectionner un plan :", type=['png', 'jpg', 'jpeg', 'pdf'])
        if fichier_importe:
            if fichier_importe.name.lower().endswith('.pdf'):
                doc = fitz.open(stream=fichier_importe.read(), filetype="pdf")
                p_num = st.number_input("Page :", min_value=1, max_value=len(doc), value=1)
                pix = doc.load_page(p_num - 1).get_pixmap(dpi=200)
                image_plan = PIL.Image.open(io.BytesIO(pix.tobytes("png")))
            else:
                image_plan = PIL.Image.open(fichier_importe)

    if image_plan:
        st.image(image_plan, caption="Plan prêt pour analyse", use_container_width=True)
        if st.button("Scanner le plan", use_container_width=True):
            with st.spinner("Analyse des contraintes..."):
                prompt = """
                Tu es un ingénieur méthodes. Analyse ce PIC sur 4 critères : Clôtures, Flux, Levage, Signalétique.
                RÈGLE ABSOLUE : Réponds UNIQUEMENT au format JSON strict, sans backticks markdown.
                [{"Critère": "...", "Anomalie": "...", "Risque": "CRITIQUE/MAJEUR/MINEUR", "Action_Corrective": "..."}]
                """
                rep = appeler_gemini([image_plan, prompt])
                if rep:
                    texte = rep.text.replace('```json', '').replace('```', '').strip()
                    try:
                        st.session_state.pic_anomalies = json.loads(texte)
                    except json.JSONDecodeError:
                        st.error("Format de réponse non conforme. Veuillez relancer l'analyse.")

    if st.session_state.pic_anomalies:
        st.write("### 📊 Anomalies Détectées")
        st.dataframe(st.session_state.pic_anomalies, use_container_width=True)
        pdf_pic = creer_rapport_pdf("Audit Visuel du PIC", "Synthèse", "Rapport d'anomalies détectées automatiquement.", st.session_state.pic_anomalies)
        st.download_button("📥 Télécharger le rapport PIC", data=pdf_pic, file_name=f"PIC_{time.strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)

# =========================================================
# ONGLET 2 : CCTP
# =========================================================
with onglet_cctp:
    st.subheader("Extraction de CCTP / PGC")
    fichier_cctp = st.file_uploader("Déposer le document contractuel :", type=['pdf'])
    if fichier_cctp:
        if st.button("Extraire les contraintes", use_container_width=True):
            with st.spinner("Lecture et extraction..."):
                doc = fitz.open(stream=fichier_cctp.read(), filetype="pdf")
                texte_cctp = "".join([page.get_text() for page in doc])
                rep = appeler_gemini([f"Extrais en liste à puces : 1. Phasage/Délai 2. Matériaux imposés 3. Contraintes chantier. Concis.\n\n{texte_cctp}"])
                if rep: st.session_state.cctp_contraintes = rep.text

    if st.session_state.cctp_contraintes:
        st.write("### 📄 Contraintes identifiées")
        st.write(st.session_state.cctp_contraintes)

# =========================================================
# ONGLET 3 : CADRAGE
# =========================================================
with onglet_cadrage:
    st.subheader("Note de Cadrage Logistique")
    if not st.session_state.cctp_contraintes:
        st.info("⚠️ Analysez un CCTP d'abord (Onglet 2).")
    else:
        effectif = st.number_input("Effectif en pointe :", min_value=1, value=20)
        if st.button("Générer la Note", use_container_width=True):
            with st.spinner("Rédaction des directives..."):
                rep = appeler_gemini([f"Rédige une Note de Cadrage PIC. Contraintes : {st.session_state.cctp_contraintes}. Effectif : {effectif}. Structure: 1. DIMENSIONNEMENT BASE VIE, 2. LEVAGE, 3. ZONAGE ET FLUX. Sois directif."])
                if rep: st.session_state.cadrage_resultat = rep.text

    if st.session_state.cadrage_resultat:
        st.markdown(st.session_state.cadrage_resultat)
        pdf_cadrage = creer_rapport_pdf("Note de Cadrage Logistique", "Directives", st.session_state.cadrage_resultat)
        st.download_button("📥 Télécharger la Note", data=pdf_cadrage, file_name=f"Cadrage_{time.strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)

# =========================================================
# ONGLET 4 : AUDIT
# =========================================================
with onglet_audit:
    st.subheader("Conformité : PIC vs CCTP")
    if not (st.session_state.pic_anomalies and st.session_state.cctp_contraintes):
        st.info("⚠️ Chargez un PIC (Onglet 1) et un CCTP (Onglet 2).")
    else:
        if st.button("Lancer l'audit croisé", use_container_width=True):
            with st.spinner("Confrontation des données..."):
                rep = appeler_gemini([f"Confronte ce PIC aux exigences contractuelles. Anomalies PIC : {json.dumps(st.session_state.pic_anomalies, ensure_ascii=False)}. CCTP : {st.session_state.cctp_contraintes}. Dresse un bilan critique : 1. Conflits 2. Oublis. Sois factuel et chirurgical."])
                if rep: st.session_state.rapport_audit = rep.text

    if st.session_state.rapport_audit:
        st.markdown(st.session_state.rapport_audit)
        pdf_audit = creer_rapport_pdf("Audit de Conformité", "Synthèse de l'Audit", st.session_state.rapport_audit)
        st.download_button("📥 Télécharger l'Audit", data=pdf_audit, file_name=f"Audit_{time.strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)

# =========================================================
# ONGLET 5 : EMAIL
# =========================================================
with onglet_email:
    st.subheader("Rédaction d'E-mail Professionnel")
    destinataire = st.selectbox("Destinataire :", ["Équipe interne / Projeteur", "Sous-traitant / Fournisseur", "Maîtrise d'Œuvre / Architecte"])
    source = st.radio("Base de la rédaction :", ["Audit de Conformité", "Anomalies PIC", "Notes libres"])
    
    donnees = st.text_area("Notes :", height=100) if source == "Notes libres" else (st.session_state.rapport_audit if source == "Audit de Conformité" else json.dumps(st.session_state.pic_anomalies, ensure_ascii=False))

    if st.button("Rédiger l'e-mail", use_container_width=True):
        if not donnees:
            st.error("Aucune donnée à traiter.")
        else:
            with st.spinner("Rédaction du brouillon..."):
                rep = appeler_gemini([f"Tu es ingénieur méthodes. Rédige un e-mail pro basé sur : {donnees}. Destinataire : {destinataire}. Ton froid, direct, exigeant des actions correctives. Objet inclus."])
                if rep: st.text_area("Résultat :", rep.text, height=250)

# =========================================================
# ONGLET 6 : RENDU 3D
# =========================================================
with onglet_3d:
    st.subheader("Génération de Vue 3D Isométrique (Intention)")
    st.warning("⚠️ Outil de visualisation conceptuelle. Ce modèle ne génère pas de géométrie à l'échelle pour la DAO.")
    
    fichier_plan_3d = st.file_uploader("Importer le plan 2D (Image) :", type=['png', 'jpg', 'jpeg'], key="upload_3d")

    if fichier_plan_3d:
        image_2d = PIL.Image.open(fichier_plan_3d)
        st.image(image_2d, caption="Plan 2D source", use_container_width=True)

        if st.button("Générer l'illustration 3D", use_container_width=True):
            with st.spinner("Étape 1/2 : Analyse spatiale du plan (Gemini)..."):
                prompt_analyse = """
                Analyse ce plan d'installation de chantier. Rédige un prompt (en anglais) très détaillé pour un générateur d'images IA.
                Décris précisément : les positions relatives, la grue, la base vie, les accès, les zones de stockage.
                Demande ce style exact : "Isometric 3D architectural render, construction site layout, highly detailed, realistic materials, clean lighting, white background, tilt-shift photography, unreal engine 5 render."
                Ne renvoie QUE le texte du prompt en anglais, aucune autre phrase.
                """
                rep_description = appeler_gemini([image_2d, prompt_analyse])
            
            if rep_description and rep_description.text:
                st.info("Description générée. Étape 2/2 : Lancement du rendu (Imagen 3)...")
                with st.spinner("Génération de l'image (peut prendre 10 à 20 secondes)..."):
                    try:
                        resultat_image = client.models.generate_images(
                            model='imagen-3.0-generate-001',
                            prompt=rep_description.text.strip(),
                            config=dict(number_of_images=1, output_mime_type="image/jpeg", aspect_ratio="16:9")
                        )
                        for img in resultat_image.generated_images:
                            st.image(PIL.Image.open(io.BytesIO(img.image.image_bytes)), caption="Rendu 3D conceptuel généré", use_container_width=True)
                    except Exception as e:
                        st.error(f"❌ Échec du rendu. Le modèle Imagen 3 n'est potentiellement pas activé sur ta clé API. Détail : {e}")
