"""Lücken der Datenbasis und ihre Einträge unter `offene_punkte`.

Eine Lücke ist eine Angabe, die ein Skript nicht prüfen kann. Beispiele sind ein fehlender Kontoauszug oder eine
Zahlung der Abrechnung ohne passende Bankbuchung. Jede Lücke hat einen Schlüssel, etwa
„fehlt: Kontoauszug DE00 0000 0000 0000 0000 00 7/2025“ oder „fehlt: Zahlung 2025-03-01 250,00“.

Ein Eintrag unter `offene_punkte` dokumentiert eine Lücke, wenn er mit ihrem Schlüssel beginnt. Direkt nach dem
Schlüssel darf kein Buchstabe und keine Ziffer folgen, damit „… 7/2025“ nicht auch „… 7/20251“ abdeckt. Nach dem
Schlüssel steht frei der Grund, etwa „ – Sammel-Lastschrift, im Auszug nicht einzeln erkennbar“.

Eine dokumentierte Lücke ist kein Fehler. Eine Lücke ohne Eintrag lässt das prüfende Skript mit Exit-Code 1 enden.
"""
import re


def kontoauszug(konto, nr):
    """Schlüssel eines Kontoauszugs, der nur als Platzhalter (`datei: null`) in der Datenbasis steht."""
    return f"fehlt: Kontoauszug {konto} {nr}"


def zahlung(art, datum, betrag):
    """Schlüssel einer Zahlung, etwa `zahlung("fehlt", "2025-03-01", 250)` → „fehlt: Zahlung 2025-03-01 250,00“."""
    return f"{art}: Zahlung {datum} " + f"{betrag:.2f}".replace(".", ",")


def dokumentiert(schluessel, offene_punkte):
    """Beginnt ein Eintrag aus `offene_punkte` mit dem Schlüssel der Lücke?"""
    muster = re.compile(re.escape(schluessel) + r"(?!\w)")
    return any(isinstance(e, str) and muster.match(e) for e in offene_punkte or [])
