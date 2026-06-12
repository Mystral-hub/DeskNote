import time
import subprocess
from pathlib import Path
from datetime import datetime
from utils import nettoyer_valeur, resoudre_chemin


def _safe_float(valeur, defaut=0.0):
    """Convertit une valeur en float sans planter."""
    try:
        return float(valeur)
    except (TypeError, ValueError):
        return defaut


def _attendre_fichier_disponible(chemin: Path, timeout: int = 10) -> bool:
    """
    Attend que le fichier soit complètement écrit et disponible.
    Retourne True si le fichier est prêt, False sinon.
    """
    debut = time.time()
    while time.time() - debut < timeout:
        try:
            if chemin.exists():
                taille = chemin.stat().st_size
                if taille > 1000:  # Fichier DOCX valide fait au moins ~1KB
                    # Essayer d'ouvrir le fichier en lecture pour vérifier qu'il n'est pas verrouillé
                    try:
                        with open(chemin, 'rb') as f:
                            # Lire les premiers bytes du ZIP (DOCX est un ZIP)
                            f.read(4)
                        return True
                    except (IOError, OSError):
                        # Fichier toujours verrouillé
                        time.sleep(0.5)
                        continue
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _resolve_word() -> Path | None:
    """Trouve le chemin de winword.exe sur le système."""
    import shutil

    found = shutil.which("winword")
    if found:
        return Path(found)

    emplacements = [
        Path("C:/Program Files/Microsoft Office/root/Office16/WINWORD.EXE"),
        Path("C:/Program Files (x86)/Microsoft Office/root/Office16/WINWORD.EXE"),
        Path("C:/Program Files/Microsoft Office/Office16/WINWORD.EXE"),
        Path("C:/Program Files (x86)/Microsoft Office/Office16/WINWORD.EXE"),
    ]
    for chemin in emplacements:
        if chemin.exists():
            return chemin
    return None


def creer_facture(parametres: dict) -> dict:
    """Crée une facture dans Word avec effet visuel progressif."""
    try:
        import win32com.client as win32
    except Exception:
        return {
            "statut": "echec",
            "message": "win32com.client indisponible. Installe pywin32 : pip install pywin32",
            "donnees": None
        }

    # --- extraction des paramètres ---
    numero = nettoyer_valeur(parametres.get("numero_facture")) or "001"
    emetteur_nom = nettoyer_valeur(
        parametres.get("emetteur_nom")) or "non fourni"
    emetteur_adr = nettoyer_valeur(parametres.get("emetteur_adresse")) or ""
    client_nom = nettoyer_valeur(parametres.get("client_nom")) or "non fourni"
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

    def _log(etape):
        print(f"[Facture] {etape}")

    # --- trouver Word ---
    word_exec = _resolve_word()
    if word_exec is None:
        return {
            "statut": "echec",
            "message": "winword.exe introuvable. Vérifiez que Microsoft Word est installé.",
            "donnees": None
        }

    try:
        _log("Lancement de Word...")
        try:
            p = subprocess.Popen(
                [str(word_exec)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            p = subprocess.Popen(
                str(word_exec),
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        pid = getattr(p, "pid", None)

        # --- connexion COM ---
        _log("Connexion à Word...")
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
                "message": "Impossible de se connecter à Word après 40 secondes.",
                "donnees": None
            }

        word_app.Visible = True
        time.sleep(2)

        # --- nouveau document ---
        _log("Création du document...")
        doc = word_app.Documents.Add()
        time.sleep(1)

        sel = word_app.Selection
        sel.Font.Name = "Calibri"
        sel.Font.Size = 11

        # --- titre ---
        _log(f"Ajout du titre — Facture N° {numero}...")
        sel.Font.Bold = True
        sel.Font.Size = 22
        sel.Font.Color = 0x1F3864
        sel.TypeText(f"FACTURE N° {numero}\n")
        time.sleep(0.8)

        # --- date ---
        _log(f"Ajout de la date — {date_aujourd_hui}...")
        sel.Font.Bold = False
        sel.Font.Size = 10
        sel.Font.Color = 0x404040
        sel.TypeText(f"Date : {date_aujourd_hui}\n\n")
        time.sleep(0.6)

        # --- émetteur ---
        _log(f"Ajout de l'émetteur — {emetteur_nom}...")
        sel.Font.Bold = True
        sel.Font.Size = 11
        sel.Font.Color = 0x000000
        sel.TypeText("DE :\n")
        sel.Font.Bold = False
        sel.TypeText(f"{emetteur_nom}\n")
        if emetteur_adr:
            sel.TypeText(f"{emetteur_adr}\n")
        time.sleep(0.6)

        # --- client ---
        _log(f"Ajout du client — {client_nom}...")
        sel.Font.Bold = True
        sel.TypeText("\nA :\n")
        sel.Font.Bold = False
        sel.TypeText(f"{client_nom}\n")
        if client_adr:
            sel.TypeText(f"{client_adr}\n")
        time.sleep(0.6)

        # --- tableau ---
        _log(f"Création du tableau — {len(articles)} article(s)...")
        sel.Font.Bold = True
        sel.Font.Size = 12
        sel.TypeText("\n\nArticles :\n")
        time.sleep(0.4)

        nb_articles = len(articles)
        nb_rows = nb_articles + 2  # 1 en-tête + articles + 1 total
        nb_cols = 4

        table = doc.Tables.Add(sel.Range, nb_rows, nb_cols)
        table.Style = "Table Grid"
        time.sleep(0.6)

        # --- en-têtes ---
        _log("Formatage des en-têtes...")
        entetes = ["Description", "Quantité", "Prix unitaire", "Total"]
        for col_idx, entete in enumerate(entetes):
            cell = table.Rows(1).Cells(col_idx + 1)
            cell.Range.Text = entete
            cell.Range.Font.Bold = True
            cell.Range.Font.Color = 0xFFFFFF
            cell.Shading.BackgroundPatternColor = 0x1F3864
            cell.VerticalAlignment = 1
            time.sleep(0.15)

        time.sleep(0.4)

        # --- articles ---
        total_general = 0.0

        for row_idx, article in enumerate(articles, start=2):
            description = article.get("description",   "prestation")
            quantite = _safe_float(article.get("quantite"),      1)
            prix_unitaire = _safe_float(article.get("prix_unitaire"), 0)
            total_ligne = quantite * prix_unitaire
            total_general += total_ligne

            _log(f"Article {row_idx - 1}/{nb_articles} — {description}...")

            table.Rows(row_idx).Cells(1).Range.Text = str(description)
            table.Rows(row_idx).Cells(2).Range.Text = f"{quantite:.0f}"
            table.Rows(row_idx).Cells(
                3).Range.Text = f"{prix_unitaire:,.0f} {symbole}"
            table.Rows(row_idx).Cells(
                4).Range.Text = f"{total_ligne:,.0f} {symbole}"

            # couleur alternée
            couleur = 0xFFFFFF if row_idx % 2 == 0 else 0xEBF3FB
            for col in range(1, 5):
                table.Rows(row_idx).Cells(
                    col).Shading.BackgroundPatternColor = couleur

            # alignement centré pour quantité, prix, total
            for col in range(2, 5):
                table.Rows(row_idx).Cells(
                    col).Range.ParagraphFormat.Alignment = 1

            time.sleep(0.5)

        # --- ligne total ---
        _log(f"Ajout du total — {total_general:,.0f} {symbole}...")
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

        time.sleep(0.8)

        # --- pied de page ---
        _log("Ajout du pied de page...")
        sel = word_app.Selection
        sel.EndKey(6)
        sel.TypeText("\n\n")
        sel.Font.Italic = True
        sel.Font.Size = 9
        sel.Font.Color = 0x808080
        sel.Font.Bold = False
        sel.ParagraphFormat.Alignment = 1
        sel.TypeText("Merci pour votre confiance.")
        time.sleep(0.8)

        # --- sauvegarde ---
        _log(f"Enregistrement — {chemin_fichier}...")
        time.sleep(0.5)

        # Sauvegarder avec les paramètres appropriés
        # wdFormatDocx = 16 (format DOCX moderne)
        try:
            doc.SaveAs(str(chemin_fichier), FileFormat=16)
        except Exception:
            # Si ça échoue avec FileFormat, essayer sans
            doc.SaveAs(str(chemin_fichier))

        _log("Attente de la sauvegarde complète...")
        time.sleep(2)  # Attendre que Word finisse d'écrire le fichier

        # Fermer le document sans resauvegarder
        try:
            doc.Close(SaveChanges=False)
        except Exception:
            pass

        time.sleep(1)  # Attendre que le document soit complètement fermé

        # Attendre que le fichier soit vraiment disponible et déverrouillé
        _log("Vérification que le fichier est complètement écrit...")
        fichier_pret = _attendre_fichier_disponible(chemin_fichier, timeout=10)

        if not fichier_pret:
            return {
                "statut":  "echec",
                "message": f"Le fichier n'a pas pu être créé correctement ou est toujours verrouillé : {chemin_fichier}",
                "donnees": None
            }

        taille_fichier = chemin_fichier.stat().st_size
        _log(f"Facture créée avec succès ({taille_fichier} bytes).")

        return {
            "statut":  "succes",
            "message": f"Facture créée : {chemin_fichier}",
            "donnees": {
                "pid":   pid,
                "path":  str(chemin_fichier),
                "total": total_general,
                "taille_fichier": taille_fichier
            }
        }

    except Exception as e:
        _log(f"Erreur : {repr(e)}")
        return {
            "statut":  "echec",
            "message": f"Erreur lors de la création de la facture : {repr(e)}",
            "donnees": None
        }
