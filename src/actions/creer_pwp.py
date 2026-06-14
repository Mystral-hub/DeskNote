"""Create PowerPoint presentation via COM (visible) with progress callbacks.

This implementation:
- runs in the executor thread (ensure pythoncom.CoInitialize is called)
- launches a visible PowerPoint instance and drives it via win32com
- inserts images from C:/Users/MystralMJ/Pictures/slides (slide1.jpg...)
- resizes images keeping aspect ratio and positions left/right/top/bottom
- sends progress updates via the provided `progress_callback` (call_id included by executor)

Requirements: pywin32 installed, Microsoft PowerPoint available (Windows).
"""
from pathlib import Path
from datetime import datetime
import time
import subprocess
import random

from PIL import Image


def _resolve_powerpoint() -> Path | None:
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


def _find_slide_image(slide_index: int) -> Path | None:
    base_path = Path("C:/Users/MystralMJ/Pictures/slides")
    for ext in (".jpg", ".jpeg", ".png"):
        p = base_path / f"slide{slide_index}{ext}"
        if p.exists():
            return p
    return None


def _get_image_size_inches(image_path: Path) -> tuple[float, float]:
    try:
        with Image.open(image_path) as img:
            dpi = img.info.get("dpi", (96, 96))[0]
            w_px, h_px = img.size
            # fallback dpi -> 96
            if dpi == 0:
                dpi = 96
            return (w_px / dpi, h_px / dpi)
    except Exception:
        return (0.0, 0.0)


def _inch_to_points(inches: float) -> float:
    # 1 inch = 72 points
    return inches * 72.0


def _color_hex_to_rgb(hex_color: str) -> int:
    h = hex_color.lstrip("#")
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return r + (g << 8) + (b << 16)


def run(parametres: dict, progress_callback=None, cancel_event=None) -> dict:
    """Create PowerPoint presentation using COM.

    progress_callback(message: str) can be supplied to receive updates.
    """
    try:
        import pythoncom
        import win32com.client as win32
    except Exception:
        return {"statut": "echec", "message": "pywin32 non disponible. Installez pywin32.", "donnees": None}

    # initialize COM in this thread
    try:
        pythoncom.CoInitialize()
    except Exception:
        pass

    def _progress(msg: str):
        try:
            if progress_callback:
                progress_callback(msg)
        except Exception:
            pass

    titre_presentation = parametres.get("titre", "Présentation DeskNote")
    slides_data = parametres.get("slides", [])
    repertoire = parametres.get("repertoire_cible", None)
    # options: laisser l'application ouverte après création, et contrôle de sauvegarde
    laisser_ouvert = bool(parametres.get("laisser_ouvert", True))
    auto_save = bool(parametres.get("auto_save", True))

    if not slides_data:
        return {"statut": "echec", "message": "Aucune slide fournie.", "donnees": None}

    # resolve output folder
    if repertoire and isinstance(repertoire, str):
        rep = repertoire.lower()
        if rep in ("telechargements", "downloads"):
            chemin_dossier = Path.home() / "Downloads"
        else:
            chemin_dossier = Path(repertoire).expanduser()
    else:
        chemin_dossier = Path.home() / "Documents"

    chemin_dossier.mkdir(parents=True, exist_ok=True)
    date_aujourd_hui = datetime.now().strftime("%d-%m-%Y_%H%M%S")
    nom_fichier = f"presentation_{date_aujourd_hui}.pptx"
    chemin_fichier = chemin_dossier / nom_fichier

    # find PowerPoint
    ppt_exec = _resolve_powerpoint()
    if ppt_exec is None:
        pythoncom.CoUninitialize()
        return {"statut": "echec", "message": "POWERPNT.EXE introuvable. Installe PowerPoint.", "donnees": None}

    try:
        _progress("Lancement de PowerPoint...")
        subprocess.Popen(str(ppt_exec), stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)

        # connect to PowerPoint application
        _progress("Connexion à PowerPoint...")
        ppt_app = None
        for attempt in range(40):
            try:
                ppt_app = win32.GetObject(Class="PowerPoint.Application")
                if ppt_app:
                    break
            except Exception:
                time.sleep(0.5)

        if not ppt_app:
            pythoncom.CoUninitialize()
            return {"statut": "echec", "message": "Impossible de se connecter à PowerPoint.", "donnees": None}

        ppt_app.Visible = True
        time.sleep(0.8)

        _progress("Création de la présentation...")
        presentation = ppt_app.Presentations.Add()
        time.sleep(0.3)

        # slide dimensions in inches (default 10 x 7.5)
        SLIDE_W_IN = 10.0
        SLIDE_H_IN = 7.5
        SLIDE_W_PT = _inch_to_points(SLIDE_W_IN)
        SLIDE_H_PT = _inch_to_points(SLIDE_H_IN)

        total = len(slides_data)
        for i, slide_info in enumerate(slides_data, start=1):
            # check cancellation request
            try:
                if cancel_event is not None and getattr(cancel_event, "is_set", lambda: False)():
                    _progress("Arrêt demandé — interruption de la création.")
                    presentation.Close()
                    ppt_app.Quit()
                    pythoncom.CoUninitialize()
                    return {"statut": "annule", "message": "Création annulée par l'utilisateur.", "donnees": None}
            except Exception:
                pass
            _progress(f"Slide {i}/{total} — création...")
            # choose layout: blank when image expected, else title+content
            image_path = _find_slide_image(i)
            if image_path:
                # 12 = ppLayoutBlank on many installs
                slide = presentation.Slides.Add(i, 12)
                # get image size in inches
                # Determine desired size. Use a larger default so images are
                # clearly visible: prefer ~35% of slide width (for landscape)
                # or ~50% of slide height (for portrait), and never occupy
                # more than 70% of slide width/height respectively. Keep
                # aspect ratio and avoid upscaling beyond source size.
                try:
                    with Image.open(image_path) as _img:
                        px_w, px_h = _img.size
                        dpi = _img.info.get("dpi", (96, 96))[0] or 96
                except Exception:
                    # fallback assumptions
                    px_w, px_h = 800, 600
                    dpi = 96

                img_ratio = (px_w / px_h) if px_h > 0 else 1.0

                # slide size in pixels at image DPI
                slide_w_px = (SLIDE_W_PT / 72.0) * dpi
                slide_h_px = (SLIDE_H_PT / 72.0) * dpi

                # Rules requested by user:
                # - portrait images: height == slide height (prefer), width == 35%-50% of slide width
                # - landscape images: width == slide width (prefer), height == 30%-40% of slide height
                # We attempt to honor those while keeping aspect ratio and avoiding upscaling.

                portrait_min_w = slide_w_px * 0.35
                portrait_max_w = slide_w_px * 0.50
                landscape_min_h = slide_h_px * 0.30
                landscape_max_h = slide_h_px * 0.40

                # minimal space reserved for text (fraction of slide width)
                min_text_w_pct = 0.35
                max_image_w_for_text = slide_w_px * (1.0 - min_text_w_pct)

                if img_ratio < 1.0:
                    # Portrait: prefer full slide height, compute width from ratio
                    desired_h_px = int(slide_h_px)
                    candidate_w_px = int(desired_h_px * img_ratio)

                    # Clamp width to configured portrait bounds
                    if candidate_w_px < portrait_min_w:
                        if px_w >= portrait_min_w:
                            candidate_w_px = int(portrait_min_w)
                            desired_h_px = int(candidate_w_px / img_ratio)
                        else:
                            candidate_w_px = px_w
                            desired_h_px = int(candidate_w_px / img_ratio)
                    elif candidate_w_px > portrait_max_w:
                        candidate_w_px = int(portrait_max_w)
                        desired_h_px = int(candidate_w_px / img_ratio)

                    # ensure we leave room for text: don't let image occupy more than allowed
                    if candidate_w_px > max_image_w_for_text:
                        candidate_w_px = int(max_image_w_for_text)
                        desired_h_px = int(candidate_w_px / img_ratio)

                    candidate_h_px = desired_h_px
                    position = random.choice(["left", "right"])
                else:
                    # Landscape: prefer a height between 30-40% of slide; compute width from ratio
                    candidate_h_px = int(slide_h_px * 0.35)
                    # clamp to min/max
                    if candidate_h_px < landscape_min_h:
                        candidate_h_px = int(landscape_min_h)
                    elif candidate_h_px > landscape_max_h:
                        candidate_h_px = int(landscape_max_h)

                    candidate_w_px = int(candidate_h_px * img_ratio)

                    # ensure we leave room for text: cap image width
                    if candidate_w_px > max_image_w_for_text:
                        candidate_w_px = int(max_image_w_for_text)
                        candidate_h_px = int(candidate_w_px / img_ratio)

                    position = random.choice(["left", "right"])

                # Avoid upscaling beyond source image size while preserving aspect ratio
                scale = min(1.0, px_w / candidate_w_px if candidate_w_px > 0 else 1.0,
                            px_h / candidate_h_px if candidate_h_px > 0 else 1.0)
                candidate_w_px = int(candidate_w_px * scale)
                candidate_h_px = int(candidate_h_px * scale)

                # convert to points
                new_w = int(round(candidate_w_px / dpi * 72.0))
                new_h = int(round(candidate_h_px / dpi * 72.0))

                margin = int(round(_inch_to_points(0.2)))
                if position == "left":
                    left = margin
                    top = int((SLIDE_H_PT - new_h) / 2)
                    text_left = left + new_w + margin
                    text_top = margin
                    text_w = int(SLIDE_W_PT - text_left - margin)
                    text_h = int(SLIDE_H_PT - 2 * margin)
                elif position == "right":
                    left = int(SLIDE_W_PT - new_w - margin)
                    top = int((SLIDE_H_PT - new_h) / 2)
                    text_left = margin
                    text_top = margin
                    text_w = int(left - 2 * margin)
                    text_h = int(SLIDE_H_PT - 2 * margin)
                elif position == "top":
                    left = int((SLIDE_W_PT - new_w) / 2)
                    top = margin
                    text_left = margin
                    text_top = top + new_h + margin
                    text_w = int(SLIDE_W_PT - 2 * margin)
                    text_h = int(SLIDE_H_PT - text_top - margin)
                else:  # bottom
                    left = int((SLIDE_W_PT - new_w) / 2)
                    top = int(SLIDE_H_PT - new_h - margin)
                    text_left = margin
                    text_top = margin
                    text_w = int(SLIDE_W_PT - 2 * margin)
                    text_h = int(top - margin - text_top)

                try:
                    slide.Shapes.AddPicture(
                        str(image_path), False, True, left, top, new_w, new_h)
                    _progress(f"Slide {i}/{total} — image insérée")
                except Exception as e:
                    _progress(f"Slide {i}/{total} — avertissement image: {e}")

                # add title textbox (always create to ensure consistent layout)
                titre = slide_info.get("titre", "")
                style = slide_info.get("style", {})
                try:
                    tb = slide.Shapes.AddTextbox(
                        1, text_left, text_top, text_w, int(text_h * 0.18))
                    tb.TextFrame.TextRange.Text = titre
                    if style.get("police"):
                        tb.TextFrame.TextRange.Font.Name = style.get("police")
                    tb.TextFrame.TextRange.Font.Size = style.get(
                        "taille_titre", 28)
                    if style.get("couleur_texte"):
                        tb.TextFrame.TextRange.Font.Color.RGB = _color_hex_to_rgb(
                            style.get("couleur_texte"))
                except Exception:
                    pass

                # add content textbox
                contenu = slide_info.get("contenu", "")
                if contenu:
                    try:
                        content_top = text_top + int(text_h * 0.18) + 10
                        cb = slide.Shapes.AddTextbox(
                            1, text_left, content_top, text_w, int(text_h - int(text_h * 0.18) - 10))
                        # set text
                        lines = contenu.split("\n")
                        cb.TextFrame.TextRange.Text = "\r".join(lines)
                        cb.TextFrame.TextRange.Font.Size = style.get(
                            "taille_contenu", 18)
                        if style.get("police"):
                            cb.TextFrame.TextRange.Font.Name = style.get(
                                "police")
                        if style.get("couleur_texte"):
                            cb.TextFrame.TextRange.Font.Color.RGB = _color_hex_to_rgb(
                                style.get("couleur_texte"))
                    except Exception:
                        pass

            else:
                # standard layout with title + content
                slide = presentation.Slides.Add(i, 2)
                titre = slide_info.get("titre", "")
                try:
                    if hasattr(slide, "Shapes") and slide.Shapes.Count > 0:
                        title_shape = slide.Shapes.Title
                        if title_shape:
                            title_shape.TextFrame.TextRange.Text = titre
                            style = slide_info.get("style", {})
                            if style.get("taille_titre"):
                                title_shape.TextFrame.TextRange.Font.Size = style.get(
                                    "taille_titre")
                            if style.get("police"):
                                title_shape.TextFrame.TextRange.Font.Name = style.get(
                                    "police")
                            if style.get("couleur_texte"):
                                title_shape.TextFrame.TextRange.Font.Color.RGB = _color_hex_to_rgb(
                                    style.get("couleur_texte"))
                except Exception:
                    pass

                contenu = slide_info.get("contenu", "")
                if contenu and slide.Shapes.Count > 1:
                    try:
                        body_shape = slide.Shapes(2)
                        if body_shape.HasTextFrame:
                            body_shape.TextFrame.TextRange.Text = "\r".join(
                                contenu.split("\n"))
                            style = slide_info.get("style", {})
                            if style.get("taille_contenu"):
                                body_shape.TextFrame.TextRange.Font.Size = style.get(
                                    "taille_contenu")
                            if style.get("police"):
                                body_shape.TextFrame.TextRange.Font.Name = style.get(
                                    "police")
                            if style.get("couleur_texte"):
                                body_shape.TextFrame.TextRange.Font.Color.RGB = _color_hex_to_rgb(
                                    style.get("couleur_texte"))
                    except Exception:
                        pass

            # small delay to let PowerPoint render and allow user to see
            time.sleep(0.25)

        # save if requested
        if auto_save:
            _progress("Enregistrement du fichier...")
            try:
                presentation.SaveAs(str(chemin_fichier))
            except Exception:
                # best-effort: ignore save errors but report
                _progress("Avertissement : impossible d'enregistrer le fichier.")
            time.sleep(0.5)

        # If laisser_ouvert is True, leave PowerPoint open so user can view/edit the file.
        if laisser_ouvert:
            _progress("Présentation créée et laissée ouverte dans PowerPoint.")
            # do not call Close() or Quit() so the app stays visible
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass
            return {"statut": "succes", "message": f"Présentation créée et laissée ouverte : {chemin_fichier}", "donnees": {"path": str(chemin_fichier) if auto_save else None, "nombre_slides": total, "left_open": True}}

        # default behavior: close presentation and quit PowerPoint
        try:
            presentation.Close()
        except Exception:
            pass
        try:
            ppt_app.Quit()
        except Exception:
            pass

        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass

        _progress("Terminé")
        return {"statut": "succes", "message": f"Présentation créée : {chemin_fichier}", "donnees": {"path": str(chemin_fichier), "nombre_slides": total}}

    except Exception as e:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass
        return {"statut": "echec", "message": f"Erreur lors de la création de la présentation : {e}", "donnees": None}
