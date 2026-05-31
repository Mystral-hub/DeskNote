# actions/creer_presentation.py
import time
import subprocess
from pathlib import Path
from datetime import datetime


def _resolve_powerpoint() -> Path | None:
    """Trouve le chemin de POWERPNT.EXE sur le système."""
    import shutil

    found = shutil.which("powerpnt")
    if found:
        return Path(found)

    emplacements = [
        Path("C:/Program Files/Microsoft Office/root/Office16/POWERPNT.EXE"),
        Path("C:/Program Files (x86)/Microsoft Office/root/Office16/POWERPNT.EXE"),
        Path("C:/Program Files/Microsoft Office/Office16/POWERPNT.EXE"),
        Path("C:/Program Files (x86)/Microsoft Office/Office16/POWERPNT.EXE"),
    ]
    for chemin in emplacements:
        if chemin.exists():
            return chemin
    return None


def run(parametres: dict) -> dict:
    """Crée une présentation PowerPoint à partir des paramètres fournis par le planificateur."""

    try:
        import win32com.client as win32
    except Exception:
        return {
            "statut": "echec",
            "message": "win32com.client indisponible. Installe pywin32 : pip install pywin32",
            "donnees": None
        }

    # --- extraction des paramètres ---
    titre_presentation = parametres.get("titre", "Présentation DeskNote")
    slides_data = parametres.get("slides", [])
    repertoire = parametres.get("repertoire_cible", None)

    if not slides_data:
        return {
            "statut": "echec",
            "message": "Aucune slide fournie dans les paramètres.",
            "donnees": None
        }

    date_aujourd_hui = datetime.now().strftime("%d/%m/%Y")
    nom_fichier = f"presentation_{date_aujourd_hui.replace('/', '-')}.pptx"
    chemin_dossier = Path(
        repertoire) if repertoire else Path.home() / "Documents"
    chemin_fichier = chemin_dossier / nom_fichier

    def _log(etape):
        print(f"[Presentation] {etape}")

    # --- trouver PowerPoint ---
    ppt_exec = _resolve_powerpoint()
    if ppt_exec is None:
        return {
            "statut": "echec",
            "message": "POWERPNT.EXE introuvable. Vérifiez que Microsoft PowerPoint est installé.",
            "donnees": None
        }

    try:
        _log("Lancement de PowerPoint...")
        p = subprocess.Popen(
            str(ppt_exec),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # --- connexion COM ---
        _log("Connexion à PowerPoint...")
        ppt_app = None
        for attempt in range(40):
            try:
                ppt_app = win32.GetObject(Class="PowerPoint.Application")
                if ppt_app:
                    break
            except Exception:
                time.sleep(1)

        if not ppt_app:
            return {
                "statut": "echec",
                "message": "Impossible de se connecter à PowerPoint après 40 secondes.",
                "donnees": None
            }

        ppt_app.Visible = True
        time.sleep(2)

        # --- création de la présentation ---
        _log("Création de la présentation...")
        presentation = ppt_app.Presentations.Add()
        time.sleep(1)

        # --- ajout des slides ---
        for i, slide_info in enumerate(slides_data, start=1):
            _log(f"Ajout de la slide {i}/{len(slides_data)}...")

            # On utilise ppLayoutText pour avoir une zone titre + contenu
            # 2 = ppLayoutText (titre + contenu)
            slide = presentation.Slides.Add(i, 2)

            # --- titre ---
            titre_slide = slide_info.get("titre", "")
            if hasattr(slide, "Shapes") and slide.Shapes.Count > 0:
                # La forme titre est généralement la première
                title_shape = slide.Shapes.Title
                if title_shape:
                    title_shape.TextFrame.TextRange.Text = titre_slide
                    # Appliquer le style du titre si présent
                    style = slide_info.get("style", {})
                    if style.get("taille_titre"):
                        title_shape.TextFrame.TextRange.Font.Size = style["taille_titre"]
                    if style.get("couleur_texte"):
                        # Conversion de la couleur hexa en RGB
                        hex_color = style["couleur_texte"].lstrip('#')
                        r, g, b = int(hex_color[0:2], 16), int(
                            hex_color[2:4], 16), int(hex_color[4:6], 16)
                        title_shape.TextFrame.TextRange.Font.Color.RGB = r + \
                            (g << 8) + (b << 16)
                    if style.get("police"):
                        title_shape.TextFrame.TextRange.Font.Name = style["police"]

            # --- contenu ---
            contenu = slide_info.get("contenu", "")
            if contenu and slide.Shapes.Count > 1:
                # La forme contenu est généralement la deuxième
                body_shape = slide.Shapes(2)
                if body_shape.HasTextFrame:
                    # On remplace les \n par des paragraphes pour créer des puces
                    lignes = contenu.split("\n")
                    body_shape.TextFrame.TextRange.Text = ""
                    for j, ligne in enumerate(lignes):
                        if j == 0:
                            body_shape.TextFrame.TextRange.Text = ligne
                        else:
                            body_shape.TextFrame.TextRange.InsertAfter(
                                "\r" + ligne)
                    # Style du contenu
                    style = slide_info.get("style", {})
                    if style.get("taille_contenu"):
                        body_shape.TextFrame.TextRange.Font.Size = style["taille_contenu"]
                    if style.get("couleur_texte"):
                        hex_color = style["couleur_texte"].lstrip('#')
                        r, g, b = int(hex_color[0:2], 16), int(
                            hex_color[2:4], 16), int(hex_color[4:6], 16)
                        body_shape.TextFrame.TextRange.Font.Color.RGB = r + \
                            (g << 8) + (b << 16)
                    if style.get("police"):
                        body_shape.TextFrame.TextRange.Font.Name = style["police"]

            # --- arrière-plan de la slide (couleur fond) ---
            style = slide_info.get("style", {})
            if style.get("couleur_fond"):
                hex_color = style["couleur_fond"].lstrip('#')
                r, g, b = int(hex_color[0:2], 16), int(
                    hex_color[2:4], 16), int(hex_color[4:6], 16)
                # Appliquer un fond uni à la slide
                slide.FollowMasterBackground = False
                slide.Background.Fill.ForeColor.RGB = r + (g << 8) + (b << 16)
                slide.Background.Fill.Visible = True
                slide.Background.Fill.Solid()

            time.sleep(0.5)

        # --- sauvegarde ---
        _log(f"Enregistrement — {chemin_fichier}...")
        presentation.SaveAs(str(chemin_fichier))
        time.sleep(1)
        presentation.Close()
        ppt_app.Quit()

        _log("Présentation créée avec succès.")

        return {
            "statut": "succes",
            "message": f"Présentation créée : {chemin_fichier}",
            "donnees": {
                "path": str(chemin_fichier),
                "nombre_slides": len(slides_data)
            }
        }

    except Exception as e:
        _log(f"Erreur : {repr(e)}")
        return {
            "statut": "echec",
            "message": f"Erreur lors de la création de la présentation : {repr(e)}",
            "donnees": None
        }
