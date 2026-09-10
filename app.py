import streamlit as st
import PIL.Image
import io
from google import genai
import json
import fitz  # PyMuPDF
import time

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
        
        # Récupération du mot de passe configuré dans secrets.toml
        mot_de_passe_attendu = st.secrets.get("APP_PASSWORD", "CADSUP2026")
        
        if st.button("Connexion", use_container_width=True):
            if mot_de_passe_saisi == mot_de_passe_attendu:
                st.session_state.authentifie = True
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")
        st.stop()

verifier_acces()

# Bouton de déconnexion dans la barre latérale
with st.sidebar:
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
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    elements = []
    styles = getSampleStyleSheet()

    # Styles personnalisés
    style_titre = ParagraphStyle(
        'TitreCADS',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1A365D"),
        spaceAfter=10
    )
    style_sous_titre = ParagraphStyle(
        'SousTitreCADS',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#2B6CB0"),
        spaceAfter=12
    )
    style_corps = ParagraphStyle(
        'CorpsCADS',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2D3748")
    )

    # Entête
    elements.append(Paragraph("CADS-UP - INGÉNIERIE MÉTHODES", style_titre))
    elements.append(Paragraph(f"<b>Rapport :</b> {titre_document}", style_sous_titre))
    elements.append(Paragraph(f"<i>Édité le : {time.strftime('%d/%m/%Y à %H:%M')}</i>", style_corps))
    elements.append(Spacer(1, 15))

    # Tableau (cas des anomalies PIC)
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

    # Contenu textuel
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
except Exception as e:
    st.error("⚠️ Clé GEMINI_API_KEY introuvable dans secrets.toml.")
    st.stop()

def appeler_gemini(contenu, tentative_max=3):
    for i in range(tentative_max):
        try:
            return client.models.generate_content(model='gemini-3.6-flash', contents=contenu)
        except Exception as e:
            if "503" in str(e) and i < tentative_max - 1:
                time.sleep(2)
            else:
                st.error(f"Erreur technique : {e}")
                return None

st.title("🏗️ CADS-UP Mobile")

# =========================================================
# ONGLET 6 : RENDU 3D CONCEPTUEL
# =========================================================
with onglet_3d:
    st.subheader("Génération de Vue 3D Isométrique (Intention)")
    st.warning("⚠️ L'IA génère une illustration visuelle conceptuelle. Ce n'est en aucun cas une maquette BIM précise ou à l'échelle.")

    fichier_plan_3d = st.file_uploader("Importer le plan 2D (Image) :", type=['png', 'jpg', 'jpeg'], key="upload_3d")

    if fichier_plan_3d:
        image_2d = PIL.Image.open(fichier_plan_3d)
        st.image(image_2d, caption="Plan 2D source", use_container_width=True)

        if st.button("Générer l'illustration 3D", use_container_width=True):
            with st.spinner("Étape 1/2 : Analyse spatiale du plan par l'IA..."):
                # 1. Gemini traduit le plan 2D en description textuelle détaillée
                prompt_analyse = """
                Analyse ce plan d'installation de chantier. Rédige un prompt (en anglais) très détaillé pour un générateur d'images IA.
                Décris précisément : les positions relatives, la grue, la base vie, les accès, les zones de stockage.
                Demande ce style exact : "Isometric 3D architectural render, construction site layout, highly detailed, realistic materials, clean lighting, white background, tilt-shift photography, unreal engine 5 render."
                Ne renvoie QUE le texte du prompt en anglais, aucune autre phrase.
                """
                rep_description = appeler_gemini([image_2d, prompt_analyse])

            if rep_description and rep_description.text:
                prompt_image = rep_description.text.strip()
                st.info("Description générée avec succès. Lancement du moteur de rendu 3D...")

                with st.spinner("Étape 2/2 : Génération de l'image (Imagen 3)..."):
                    try:
                        # 2. Appel au modèle de génération d'images Imagen 3
                        resultat_image = client.models.generate_images(
                            model='imagen-3.0-generate-001',
                            prompt=prompt_image,
                            config=dict(
                                number_of_images=1,
                                output_mime_type="image/jpeg",
                                aspect_ratio="16:9"
                            )
                        )
                        
                        # Affichage de l'image
                        for image_generee in resultat_image.generated_images:
                            image_bytes = image_generee.image.image_bytes
                            image_3d = PIL.Image.open(io.BytesIO(image_bytes))
                            st.image(image_3d, caption="Rendu 3D Isométrique d'intention", use_container_width=True)
                            
                    except Exception as e:
                        st.error("❌ Échec du rendu 3D. Le modèle Imagen n'est probablement pas activé pour ta clé API.")
                        st.error(f"Détail technique : {e}")

# =========================================================
# ONGLET 1 : ANALYSE DU PIC (PHOTO OU FICHIER)
# =========================================================
with onglet_pic:
    st.subheader("Analyse Visuelle de Plan (PIC)")
    
    # Choix de la source : appareil photo ou fichier
    mode_acquisition = st.radio("Source de l'image :", ["📸 Appareil photo", "📁 Fichier (PDF / Image)"], horizontal=True)
    image_plan = None

    if mode_acquisition == "📸 Appareil photo":
        photo_capturee = st.camera_input("Prendre une photo du plan en direct")
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
            with st.spinner("Analyse des contraintes et risques..."):
                prompt = """
                Tu es un ingénieur méthodes. Analyse ce PIC sur 4 critères : Clôtures, Flux, Levage, Signalétique.
                RÈGLE ABSOLUE : Réponds UNIQUEMENT au format JSON strict, sans backticks markdown.
                [
                  {"Critère": "...", "Anomalie": "...", "Risque": "CRITIQUE/MAJEUR/MINEUR", "Action_Corrective": "..."}
                ]
                """
                rep = appeler_gemini([image_plan, prompt])
                if rep:
                    texte = rep.text.replace('```json', '').replace('```', '').strip()
                    try:
                        st.session_state.pic_anomalies = json.loads(texte)
                    except json.JSONDecodeError:
                        st.error("Format de réponse non conforme. Réessayez.")

    if st.session_state.pic_anomalies:
        st.divider()
        st.write("### 📊 Anomalies Détectées")
        st.dataframe(st.session_state.pic_anomalies, use_container_width=True)
        
        # Bouton d'export PDF pour le PIC
        pdf_pic = creer_rapport_pdf(
            titre_document="Audit Visuel du Plan d'Installation de Chantier (PIC)",
            section_nom="Synthèse",
            contenu_texte="Rapport d'anomalies détectées automatiquement par analyse d'image.",
            tableau_donnees=st.session_state.pic_anomalies
        )
        st.download_button(
            label="📥 Télécharger le rapport PIC en PDF",
            data=pdf_pic,
            file_name=f"Rapport_PIC_{time.strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

# =========================================================
# ONGLET 2 : CCTP / PGC
# =========================================================
with onglet_cctp:
    st.subheader("Extraction de CCTP / PGC")
    fichier_cctp = st.file_uploader("Déposer le document contractuel :", type=['pdf'], key="cctp_file")
    
    if fichier_cctp:
        if st.button("Extraire les contraintes", use_container_width=True):
            with st.spinner("Extraction des contraintes chantier..."):
                doc = fitz.open(stream=fichier_cctp.read(), filetype="pdf")
                texte_cctp = "".join([page.get_text() for page in doc])
                prompt = f"Extrais en liste à puces : 1. Phasage/Délai 2. Matériaux imposés 3. Contraintes chantier. Concis.\n\n{texte_cctp}"
                rep = appeler_gemini([prompt])
                if rep:
                    st.session_state.cctp_contraintes = rep.text

    if st.session_state.cctp_contraintes:
        st.divider()
        st.write("### 📄 Contraintes identifiées")
        st.write(st.session_state.cctp_contraintes)

# =========================================================
# ONGLET 3 : NOTE DE CADRAGE
# =========================================================
with onglet_cadrage:
    st.subheader("Note de Cadrage Logistique")
    if not st.session_state.cctp_contraintes:
        st.info("Veuillez d'abord analyser un CCTP dans l'onglet 'CCTP'.")
    else:
        effectif = st.number_input("Effectif en pointe :", min_value=1, value=20)
        if st.button("Générer la Note de Cadrage", use_container_width=True):
            with st.spinner("Rédaction technique..."):
                prompt = f"""
                Rédige une Note de Cadrage PIC formelle destinée au projeteur.
                Contraintes CCTP : {st.session_state.cctp_contraintes}
                Effectif : {effectif} compagnons.
                Structure avec : 1. DIMENSIONNEMENT BASE VIE, 2. STRATÉGIE DE LEVAGE, 3. ZONAGE ET FLUX. Directif et précis.
                """
                rep = appeler_gemini([prompt])
                if rep:
                    st.session_state.cadrage_resultat = rep.text

    if st.session_state.cadrage_resultat:
        st.divider()
        st.markdown(st.session_state.cadrage_resultat)
        
        # Bouton d'export PDF pour le cadrage
        pdf_cadrage = creer_rapport_pdf(
            titre_document="Note de Cadrage Logistique - Avant-Projet",
            section_nom="Directives d'Installation",
            contenu_texte=st.session_state.cadrage_resultat
        )
        st.download_button(
            label="📥 Télécharger la Note de Cadrage en PDF",
            data=pdf_cadrage,
            file_name=f"Note_Cadrage_{time.strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

# =========================================================
# ONGLET 4 : AUDIT CROISÉ
# =========================================================
with onglet_audit:
    st.subheader("Audit de Conformité : PIC vs CCTP")
    if not (st.session_state.pic_anomalies and st.session_state.cctp_contraintes):
        st.info("Chargez d'abord un PIC (Onglet 1) et un CCTP (Onglet 2).")
    else:
        if st.button("Lancer l'audit croisé", use_container_width=True):
            with st.spinner("Confrontation des exigences..."):
                prompt = f"""
                Confronte le plan d'installation aux exigences contractuelles.
                Anomalies PIC : {json.dumps(st.session_state.pic_anomalies, ensure_ascii=False)}
                Exigences CCTP : {st.session_state.cctp_contraintes}
                Dresse un bilan critique : 1. Conflits directs 2. Oublis. Direct et factuel.
                """
                rep = appeler_gemini([prompt])
                if rep:
                    st.session_state.rapport_audit = rep.text

    if st.session_state.rapport_audit:
        st.divider()
        st.markdown(st.session_state.rapport_audit)
        
        # Bouton d'export PDF pour l'audit croisé
        pdf_audit = creer_rapport_pdf(
            titre_document="Rapport d'Audit de Conformité (PIC vs CCTP)",
            section_nom="Synthèse de l'Audit",
            contenu_texte=st.session_state.rapport_audit
        )
        st.download_button(
            label="📥 Télécharger l'Audit Croisé en PDF",
            data=pdf_audit,
            file_name=f"Audit_Conformite_{time.strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

# =========================================================
# ONGLET 5 : E-MAIL
# =========================================================
with onglet_email:
    st.subheader("Rédaction de Mail Professionnel")
    destinataire = st.selectbox("Destinataire :", [
        "Équipe interne / Projeteur", 
        "Sous-traitant / Fournisseur", 
        "Maîtrise d'Œuvre / Architecte"
    ])
    source = st.radio("Base de rédaction :", [
        "Audit de Conformité (PIC vs CCTP)",
        "Rapport brut anomalies PIC",
        "Notes libres"
    ])
    
    donnees = ""
    if source == "Notes libres":
        donnees = st.text_area("Notes :", height=100)
    elif source == "Rapport brut anomalies PIC":
        donnees = json.dumps(st.session_state.pic_anomalies, ensure_ascii=False) if st.session_state.pic_anomalies else ""
    elif source == "Audit de Conformité (PIC vs CCTP)":
        donnees = st.session_state.rapport_audit if st.session_state.rapport_audit else ""

    if st.button("Rédiger l'e-mail", use_container_width=True):
        if not donnees:
            st.error("Aucune donnée disponible à traiter.")
        else:
            with st.spinner("Rédaction du mail..."):
                prompt = f"""
                Tu es ingénieur méthodes. Rédige un e-mail professionnel basé sur : {donnees}.
                Destinataire : {destinataire}. Ton froid, direct, exigeant des actions correctives. Objet inclus.
                """
                rep = appeler_gemini([prompt])
                if rep:
                    st.text_area("Résultat :", rep.text, height=250)
