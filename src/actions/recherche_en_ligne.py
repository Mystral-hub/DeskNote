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


def _split_text_into_lines(text: str, width: int = 90, min_lines: int = 20) -> list[str]:
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

    # Build a concise, coherent summary to keep the live-typing output
    # short (roughly 10-15 lines) and useful for note-taking. Only one
    # source will be included per your request.
    lines = [f"Résultats de recherche pour : {requete}", "=" * 50]

    if not resultats:
        lines.append("Aucun résultat trouvé.")
    else:
        # only include a single best result
        r = resultats[0]
        titre = (r.get("title") or "").strip()
        lien = (r.get("href") or "").strip()
        extrait = (r.get("body") or "").strip()

        # Attempt to get richer page text when excerpt is short
        source_text = extrait
        if len(extrait.split()) < 50 and lien:
            page_text = _fetch_page_text(lien)
            if page_text:
                source_text = page_text

        # create a multi-line summary from the source text (best-effort)
        detail_lines = _split_text_into_lines(
            source_text, width=90, min_lines=20)

        lines.append(f"Titre : {titre}")
        lines.append(f"Lien  : {lien}")
        lines.append("Résumé :")
        # include up to ~15 lines from detail_lines; these are not translated
        for s in detail_lines[:15]:
            lines.append(f"  {s}")

        # create final concise content: include metadata and raw text truncated
        # to a small number of lines (5-10) as requested.
        max_text_lines = int(parametres.get("text_lines", 10))

        # extract raw text lines from the chosen source_text
        raw_lines = _split_text_into_lines(
            source_text, width=90, min_lines=max_text_lines)
        truncated_text_lines = raw_lines[:max_text_lines]

        # assemble final content: metadata + blank line + truncated raw text
        metadata_lines = [f"Requête : {requete}", f"Lien    : {lien}",]
        concise_content = "\n".join(
            metadata_lines + ["", *truncated_text_lines])

    if sauvegarder:
        nom_fichier = nom_fichier or f"recherche_{requete[:20].replace(' ', '_')}.txt"
        chemin_dossier = resoudre_chemin(
            repertoire_cible) or Path.home() / "Documents"
        chemin_fichier = chemin_dossier / nom_fichier

        # ensure directory exists and create the target file beforehand to
        # avoid Notepad showing a confirmation popup when the file is missing
        try:
            chemin_dossier.mkdir(parents=True, exist_ok=True)
            if not chemin_fichier.exists():
                chemin_fichier.write_text("", encoding="utf-8")
        except Exception:
            pass

        # prepare metadata (3 important fields) and final content to save
        try:
            from datetime import datetime
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            date_str = ""

        metadata_lines = [
            f"Requête : {requete}",
            f"Date    : {date_str}",
            f"Résultats trouvés : {len(resultats)}",
        ]

        final_content = "\n".join(metadata_lines) + "\n\n" + concise_content

        # Launch Notepad with the target file and type the content into it.
        try:
            lt_params = {
                "application": "notepad",
                "application_args": [str(chemin_fichier)],
                "texte": "\n".join(metadata_lines + ["", concise_content]),
                "ouvrir_app": True,
                "max_line_length": 80,
                "auto_save": True,
            }

            def _run_live_typing(params, resolver, cancel_ev=None):
                try:
                    action_live_typing(
                        params, resolver, cancel_event=cancel_ev)
                except Exception:
                    # fallback: if typing fails, write the file directly
                    try:
                        chemin_dossier.mkdir(parents=True, exist_ok=True)
                        chemin_fichier.write_text(
                            "\n".join(metadata_lines + ["", concise_content]), encoding="utf-8")
                    except Exception:
                        pass

            cancel_ev = None
            try:
                cancel_ev = parametres.get("_cancel_event")
            except Exception:
                cancel_ev = None

            thr = threading.Thread(target=_run_live_typing, args=(
                lt_params, resolve_executable_func, cancel_ev), daemon=True)
            thr.start()
        except Exception:
            # fallback: write the file directly if we cannot launch Notepad
            try:
                chemin_dossier.mkdir(parents=True, exist_ok=True)
                chemin_fichier.write_text(
                    "\n".join(metadata_lines + ["", concise_content]), encoding="utf-8")
            except Exception:
                pass

        return {"statut": "succes", "message": f"Recherche terminée. Résultat tapé dans : {chemin_fichier}", "donnees": {"path": str(chemin_fichier)}}

    # no saving requested: just return concise content and open browser
    return {"statut": "succes", "message": "Recherche terminée. Navigateur ouvert.", "donnees": {"preview": concise_content}}
