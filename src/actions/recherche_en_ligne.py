import html
import os
import re
import textwrap
import urllib.error
import urllib.request
import webbrowser
import threading
from pathlib import Path
from utils import (
    resoudre_chemin,
)
from actions.live_typing import live_typing as action_live_typing

try:
    from ddgs import DDGS
    DDGS_CLIENT = "ddgs"
except Exception:
    try:
        from duckduckgo_search import DDGS
        DDGS_CLIENT = "duckduckgo_search"
    except Exception:
        DDGS = None
        DDGS_CLIENT = None


def _fetch_page_text(url: str, timeout: int = 10) -> str | None:
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            },
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw_bytes = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            text = raw_bytes.decode(charset, errors="replace")

        try:
            from lxml import html as lxml_html

            document = lxml_html.fromstring(text)
            body = document.find("body")
            page_text = body.text_content() if body is not None else document.text_content()
        except Exception:
            page_text = re.sub(r"<[^>]+>", "\n", text)

        page_text = html.unescape(page_text)
        page_text = re.sub(r"\s+", " ", page_text).strip()
        return page_text
    except Exception:
        return None


def _split_text_into_lines(text: str, width: int = 90, min_lines: int = 10) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
    lines: list[str] = []

    for paragraph in paragraphs:
        wrapped = textwrap.wrap(paragraph, width=width,
                                replace_whitespace=False)
        if wrapped:
            lines.extend(wrapped)
        if len(lines) >= min_lines:
            break

    if len(lines) < min_lines:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        for sentence in sentences:
            if len(lines) >= min_lines:
                break
            wrapped = textwrap.wrap(
                sentence.strip(), width=width, replace_whitespace=False)
            lines.extend(wrapped)

    if len(lines) < min_lines:
        lines.extend(["..."] * (min_lines - len(lines)))

    return lines[:max(min_lines, len(lines))]


def recherche_en_ligne(parametres: dict, resolve_executable_func) -> dict:
    requete = parametres.get("requete")
    if requete:
        requete = requete.strip()
    sauvegarder = parametres.get("sauvegarder_resultat", True)
    nom_fichier = parametres.get("nom_fichier_resultat")
    repertoire_cible = parametres.get("repertoire_cible")

    if not requete:
        return {"statut": "echec", "message": "Aucune requête spécifiée.", "donnees": None}

    webbrowser.open(f"https://duckduckgo.com/?q={requete.replace(' ', '+')}")

    if DDGS is None:
        return {"statut": "echec", "message": "La bibliothèque 'duckduckgo_search' est introuvable.", "donnees": None}

    try:
        with DDGS() as ddgs:
            if DDGS_CLIENT == "ddgs":
                resultats = list(ddgs.text(requete, max_results=5))
            else:
                resultats = list(ddgs.text(requete, max_results=5))
    except Exception as e:
        return {"statut": "echec", "message": f"Erreur lors de la recherche : {e}", "donnees": None}

    lignes = [f"Résultats de recherche pour : {requete}\n", "=" * 50 + "\n"]
    if not resultats:
        lignes.append("Aucun résultat n'a été trouvé pour cette recherche.")
    else:
        for r in resultats:
            titre = r.get("title", "")
            lien = r.get("href", "")
            extrait = r.get("body", "") or ""

            lignes.append(f"Titre   : {titre}")
            lignes.append(f"Lien    : {lien}")

            # Paragraphes courts ou résumé insuffisant : enrichir avec le texte de la page
            lignes.append(f"Résumé  : {extrait}")
            source_text = extrait
            if len(extrait.split()) < 40:
                page_text = _fetch_page_text(lien)
                if page_text:
                    source_text = page_text
                    lignes.append(
                        "Source  : contenu enrichi depuis la page liée")

            detail_lines = _split_text_into_lines(
                source_text, width=90, min_lines=10)
            if detail_lines:
                lignes.append("Détail  :")
                for line in detail_lines:
                    lignes.append(f"  {line}")

            lignes.append("-" * 50)

    contenu = "\n".join(lignes)

    if sauvegarder:
        nom_fichier = nom_fichier or f"recherche_{requete[:20].replace(' ', '_')}.txt"
        chemin_dossier = resoudre_chemin(
            repertoire_cible) or Path.home() / "Documents"
        chemin_fichier = chemin_dossier / nom_fichier
        chemin_fichier.write_text(contenu, encoding="utf-8")

        # Ouvre le fichier complet immédiatement pour que l'utilisateur voie
        # la sortie enrichie, même si le live typing est toujours en cours.
        try:
            os.startfile(str(chemin_fichier))
        except Exception:
            pass

        # Also type a preview of the results live into Notepad.
        # Run typing in a background thread so the action can return quickly
        # (prevents main timeout while typing continues).
        try:
            preview_lines = 40
            all_lines = contenu.splitlines()
            preview_text = "\n".join(all_lines[:preview_lines])
            if len(all_lines) > preview_lines:
                preview_text += "\n\n... suite dans le fichier sauvegardé"

            lt_params = {
                "application": "notepad",
                "texte": preview_text,
                "ouvrir_app": True,
                "max_line_length": 80,
            }

            def _run_live_typing(params, resolver, cancel_ev=None):
                try:
                    action_live_typing(
                        params, resolver, cancel_event=cancel_ev)
                except Exception:
                    return

            # pass through any cancel event from the parent action so the
            # preview typing can be stopped by the same global stop.
            cancel_ev = None
            try:
                cancel_ev = parametres.get("_cancel_event")
            except Exception:
                cancel_ev = None

            thr = threading.Thread(target=_run_live_typing, args=(
                lt_params, resolve_executable_func, cancel_ev), daemon=True)
            thr.start()
        except Exception:
            # live typing is best-effort; do not fail the whole action
            pass
        return {"statut": "succes", "message": f"Recherche terminée. Résultats sauvegardés dans : {chemin_fichier}", "donnees": {"path": str(chemin_fichier)}}

    return {"statut": "succes", "message": "Recherche terminée. Navigateur ouvert.", "donnees": None}
