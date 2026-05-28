"""Creer facture action — create an invoice in Word with visual progression (like Gamma)."""

import time
import subprocess
from pathlib import Path
from datetime import datetime
from utils import nettoyer_valeur, resoudre_chemin


def creer_facture(parametres: dict, resolve_executable_func) -> dict:
    """Crée une facture dans Word avec effet visuel progressif.

    La facture se construit étape par étape :
    - Titre apparaît
    - Date apparaît
    - Bloc DE apparaît
    - Bloc À apparaît
    - Tableau se crée et se remplit ligne par ligne
    - Formatage/couleurs s'appliquent
    - Pied de page apparaît
    - Enregistrement

    Paramètres:
        parametres: dict with invoice info (numero, emetteur_nom, etc.)
        resolve_executable_func: fonction pour résoudre le chemin d'une app

    Retour:
        dict: {'statut': 'succes'|'echec', 'message': str, 'donnees': dict|None}
    """
    try:
        import win32com.client as win32
    except Exception:
        return {
            "statut": "echec",
            "message": "win32com.client indisponible. Installe pywin32 : pip install pywin32",
            "donnees": None
        }

    # === EXTRACTION DES PARAMÈTRES ===
    numero = nettoyer_valeur(parametres.get("numero_facture")) or "001"
    emetteur_nom = nettoyer_valeur(
        parametres.get("emetteur_nom")) or "Mon Entreprise"
    emetteur_adr = nettoyer_valeur(parametres.get("emetteur_adresse")) or ""
    client_nom = nettoyer_valeur(parametres.get("client_nom")) or "Client"
    client_adr = nettoyer_valeur(parametres.get("client_adresse")) or ""
    articles = parametres.get("articles") or []
    devise = nettoyer_valeur(parametres.get("devise")) or "EUR"
    repertoire = nettoyer_valeur(parametres.get("repertoire_cible"))

    symboles_devise = {"EUR": "€", "USD": "$", "XAF": "FCFA"}
    symbole = symboles_devise.get(devise.upper(), devise)

    date_aujourd_hui = datetime.now().strftime("%d/%m/%Y")
    nom_fichier = f"facture_{client_nom.replace(' ', '_')}_{numero}.docx"

    chemin_dossier = resoudre_chemin(repertoire) or Path.home() / "Documents"
    chemin_fichier = chemin_dossier / nom_fichier

    def _log(step):
        """Affiche un log de progression."""
        print(f"[Facture] {step}")

    # === LANCER WORD ===
    word_exec = resolve_executable_func("winword")
    if word_exec is None:
        return {
            "statut": "echec",
            "message": "winword.exe introuvable. Installe Microsoft Word.",
            "donnees": None
        }

    try:
        _log("🚀 Lancement de Word...")
        try:
            p = subprocess.Popen(
                [str(word_exec)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
        except Exception:
            p = subprocess.Popen(str(
                word_exec), shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)

        pid = getattr(p, "pid", None)

        # === CONNEXION COM ===
        _log("⏳ Connexion à Word (cela peut prendre quelques secondes)...")
        word_app = None
        for attempt in range(40):
            try:
                word_app = win32.GetObject(Class="Word.Application")
                if word_app:
                    break
            except Exception:
                time.sleep(1)

        if not word_app:
            return {
                "statut": "echec",
                "message": "Impossible de se connecter à Word COM après 40 secondes.",
                "donnees": None
            }

        word_app.Visible = True
        time.sleep(2)

        _log("📄 Création d'un nouveau document...")
        doc = word_app.Documents.Add()
        time.sleep(2)

        selection = word_app.Selection
        selection.Font.Name = "Calibri"
        selection.Font.Size = 11

        # === TITRE ===
        _log(f"📋 Ajout du titre (Facture N° {numero})...")
        sel = word_app.Selection
        sel.Font.Bold = True
        sel.Font.Size = 22
        sel.Font.Color = 0x1F3864
        sel.TypeText(f"FACTURE N° {numero}\n")
        time.sleep(1)

        # === DATE ===
        _log(f"📅 Ajout de la date ({date_aujourd_hui})...")
        sel.Font.Bold = False
        sel.Font.Size = 10
        sel.Font.Color = 0x404040
        sel.TypeText(f"Date : {date_aujourd_hui}\n\n")
        time.sleep(0.8)

        # === BLOC ÉMETTEUR ===
        _log(f"🏢 Ajout de l'émetteur ({emetteur_nom})...")
        sel.Font.Bold = True
        sel.Font.Size = 11
        sel.TypeText("DE :\n")
        time.sleep(0.3)
        sel.Font.Bold = False
        sel.TypeText(f"{emetteur_nom}\n")
        if emetteur_adr:
            sel.TypeText(f"{emetteur_adr}\n")
        time.sleep(0.8)

        # === BLOC CLIENT ===
        _log(f"👥 Ajout du client ({client_nom})...")
        sel.Font.Bold = True
        sel.TypeText("\nA :\n")
        time.sleep(0.3)
        sel.Font.Bold = False
        sel.TypeText(f"{client_nom}\n")
        if client_adr:
            sel.TypeText(f"{client_adr}\n")
        time.sleep(0.8)

        # === TABLEAU ===
        _log("📊 Création du tableau des articles...")
        sel.Font.Bold = True
        sel.Font.Size = 12
        sel.TypeText("\n\nArticles :\n")
        time.sleep(0.5)

        nb_articles = len(articles)
        nb_rows = nb_articles + 2  # +1 en-tête, +1 total
        nb_cols = 4

        table = doc.Tables.Add(sel.Range, nb_rows, nb_cols)
        table.Style = "Table Grid"
        time.sleep(0.8)

        # === EN-TÊTES TABLEAU ===
        _log("🎨 Formatage des en-têtes...")
        headers = ["Description", "Quantité", "Prix unitaire", "Total"]
        for col_idx, header in enumerate(headers):
            cell = table.Rows(1).Cells(col_idx + 1)
            cell.Range.Text = header
            cell.Range.Font.Bold = True
            cell.Range.Font.Color = 0xFFFFFF
            cell.Shading.BackgroundPatternColor = 0x1F3864
            cell.VerticalAlignment = 1
            time.sleep(0.2)

        time.sleep(0.5)

        # === LIGNES ARTICLES ===
        total_general = 0
        for row_idx, article in enumerate(articles, start=2):
            description = article.get("description", "")
            quantite = float(article.get("quantite", 0))
            prix_unitaire = float(article.get("prix_unitaire", 0))
            total_ligne = quantite * prix_unitaire
            total_general += total_ligne

            _log(
                f"📝 Ajout article ({row_idx - 1}/{nb_articles}) : {description}...")

            table.Rows(row_idx).Cells(1).Range.Text = description
            table.Rows(row_idx).Cells(2).Range.Text = f"{quantite:.0f}"
            table.Rows(row_idx).Cells(
                3).Range.Text = f"{prix_unitaire:,.0f} {symbole}"
            table.Rows(row_idx).Cells(
                4).Range.Text = f"{total_ligne:,.0f} {symbole}"

            # Coloration alternée
            couleur = 0xFFFFFF if row_idx % 2 == 0 else 0xEBF3FB
            for col in range(1, 5):
                table.Rows(row_idx).Cells(
                    col).Shading.BackgroundPatternColor = couleur

            # Alignement
            for col in range(2, 5):
                table.Rows(row_idx).Cells(
                    col).Range.ParagraphFormat.Alignment = 1

            time.sleep(0.6)

        # === LIGNE TOTAL ===
        _log(f"💰 Ajout du total ({total_general:,.0f} {symbole})...")
        total_row = nb_rows
        table.Rows(total_row).Cells(1).Range.Text = ""
        table.Rows(total_row).Cells(2).Range.Text = ""
        table.Rows(total_row).Cells(3).Range.Text = "TOTAL :"
        table.Rows(total_row).Cells(
            4).Range.Text = f"{total_general:,.0f} {symbole}"

        for col in range(1, 5):
            table.Rows(total_row).Cells(col).Range.Font.Bold = True
            table.Rows(total_row).Cells(
                col).Shading.BackgroundPatternColor = 0xE8F0F8

        time.sleep(1)

        # === PIED DE PAGE ===
        _log("✍️ Ajout du pied de page...")
        sel = word_app.Selection
        sel.EndKey(6)
        sel.TypeText("\n\n")
        sel.Font.Italic = True
        sel.Font.Size = 9
        sel.Font.Color = 0x808080
        sel.ParagraphFormat.Alignment = 1
        sel.TypeText("Merci pour votre confiance.")
        time.sleep(1)

        # === ENREGISTREMENT ===
        _log(f"💾 Enregistrement du fichier ({chemin_fichier})...")
        time.sleep(1)
        doc.SaveAs(str(chemin_fichier))
        time.sleep(2)
        doc.Close()
        time.sleep(1)

        _log("✅ Facture créée avec succès!")

        return {
            "statut": "succes",
            "message": f"Facture créée avec succès : {chemin_fichier}",
            "donnees": {"pid": pid, "path": str(chemin_fichier), "total": total_general}
        }

    except Exception as e:
        _log(f"❌ Erreur : {repr(e)}")
        return {
            "statut": "echec",
            "message": f"Erreur lors de la création de la facture : {repr(e)}",
            "donnees": None
        }
