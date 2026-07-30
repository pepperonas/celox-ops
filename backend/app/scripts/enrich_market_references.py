"""Referenzkunden anreichern: Website auflösen, Impressum lesen.

    docker compose exec backend python -m app.scripts.enrich_market_references \\
        --owner martin --vorschau            # zeigt die Auswahl, fragt NICHTS ab
    ... --apply                              # löst auf, liest Impressum, schreibt
    ... --top 200 --limit 50                 # Umfang begrenzen
    ... --nur-impressum                      # ohne Places, nur bekannte Websites

Zwei Schritte je Firma:

  1. **Name → Website** über Google Places (Textsuche + Details = zwei Abfragen).
  2. **Website → Impressum**: E-Mail, Telefon, Geschäftsführung — kostenlos und
     deterministisch (`market_contacts`), jeder Wert eine wörtliche Teilzeichenfolge
     der Seite, mit Quelle und Zitat in `contact_evidence`.

**⚠️ Es gibt hier keinen kostenlosen Trockenlauf.** Ohne Places-Abfrage gibt es keine
Website, also nichts zu prüfen. Deshalb heißt der Standard `--vorschau`: Er zeigt nur,
WELCHE Firmen dran wären und wie viele Abfragen das kostet, und fragt nichts ab. Ein
Lauf mit `--apply` fragt ab und schreibt — und erhöht den Nutzungszähler um die
**echten** Aufrufe, auch die erfolglosen: Bezahlt werden sie trotzdem.

**Die Mitarbeiterzahl wird NICHT gefüllt.** Bei den Herstellern waren 13 von 25 Funden
falsch (fremde Firmengrößen aus Referenz-Kacheln und Zielgruppen-Angaben). Das Feld
existiert, bleibt aber der Handpflege überlassen.

Die Auswahl (`--spitze`, Standard): alle **Mehrfachnutzer** plus die besten nach
**Score**. Dort lohnen sich die Abfragen; der lange Schwanz bei Score 20–39
unterscheidet sich ohnehin nicht.
"""
import argparse
import asyncio
import sys

import app.main  # noqa: F401 — registriert Modelle + Tenancy-Events
import httpx
from sqlalchemy import select

from app.database import async_session_factory
from app.models.market_baustein import MarketBaustein
from app.models.market_product import MarketProduct
from app.models.market_reference import MarketReference
from app.models.user import User
from app.services.business_time import now
from app.services.email_verifier import verify_email
from app.services.market_contacts import fetch_contacts
from app.services.lead_discovery import PlacesQuotaExhausted
from app.services.market_reference_enrich import resolve_website
from app.services.market_reference_pipeline import bausteine_fuer
from app.services.market_reference_scoring import bewerte
from app.routers.settings import get_or_create_settings
from app.services.places_usage import bump
from app.tenancy import current_owner_id

# E-Mail-Status, bei denen die Adresse verworfen wird: ohne MX oder mit kaputter
# Syntax ist sie kein Kontaktweg. `role` (info@, kontakt@) bleibt — das IST die
# Firmenadresse.
KAPUTT = ("invalid_syntax", "no_mx", "disposable")


async def _owner(db, benutzer: str):
    row = (await db.execute(
        select(User).where((User.username == benutzer) | (User.email == benutzer))
    )).scalar_one_or_none()
    if row is None:
        print(f"Benutzer '{benutzer}' nicht gefunden.", file=sys.stderr)
        raise SystemExit(2)
    return row.id


async def _auswahl(db, args) -> tuple[list, str]:
    """Welche Firmen sind dran? Gruppiert nach Firma, bewertet wie in der Oberfläche."""
    alle = list((await db.execute(select(MarketReference))).scalars())
    produkte = {p.id: p for p in (await db.execute(select(MarketProduct))).scalars()}
    bausteine = list((await db.execute(select(MarketBaustein))).scalars())

    gruppen: dict[str, list[MarketReference]] = {}
    for r in alle:
        gruppen.setdefault(r.company_norm, []).append(r)

    bewertet = []
    for schluessel, zeilen in gruppen.items():
        anzahl = len({r.product_id for r in zeilen})
        best = max((produkte[r.product_id].score for r in zeilen
                    if r.product_id in produkte), default=0)
        hat_b = any(bausteine_fuer(produkte[r.product_id].catalog_id, bausteine)
                    for r in zeilen if r.product_id in produkte)
        website = next((r.website for r in zeilen if r.website), None)
        name = max((r.company for r in zeilen), key=len)
        b = bewerte(company=name, systeme=anzahl, hat_baustein=hat_b,
                    produkt_score=best, hat_website=bool(website))
        bewertet.append({"score": b["score"], "systeme": anzahl, "key": schluessel,
                         "zeilen": zeilen, "website": website, "name": name})

    if args.nur_impressum:
        auswahl = [x for x in bewertet if x["website"]]
        grund = "mit bereits bekannter Website"
    else:
        mehrfach = [x for x in bewertet if x["systeme"] > 1]
        schon = {x["key"] for x in mehrfach}
        rest = sorted((x for x in bewertet if x["key"] not in schon),
                      key=lambda x: (-x["score"], x["name"]))[:args.top]
        auswahl = mehrfach + rest
        grund = f"{len(mehrfach)} Mehrfachnutzer + Top {args.top} nach Score"

    # Bereits geprüfte nicht erneut abfragen — Abfragen kosten Geld.
    auswahl = [x for x in auswahl if not any(r.contact_checked_at for r in x["zeilen"])]
    auswahl.sort(key=lambda x: (-x["score"], x["name"]))
    if args.limit:
        auswahl = auswahl[:args.limit]
    return auswahl, grund


def _beleg(evidence: dict, feld: str, quelle: str, zitat: str | None) -> None:
    evidence[feld] = {"quelle": quelle, "zitat": zitat} if zitat else {"quelle": quelle}


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--owner", required=True)
    ap.add_argument("--apply", action="store_true",
                    help="abfragen und schreiben (Standard: nur Vorschau der Auswahl)")
    ap.add_argument("--vorschau", action="store_true",
                    help="nur zeigen, wer dran wäre (Standard) — fragt NICHTS ab")
    ap.add_argument("--top", type=int, default=200)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--nur-impressum", action="store_true")
    ap.add_argument("--concurrency", type=int, default=4)
    args = ap.parse_args()

    async with async_session_factory() as db:
        current_owner_id.set(await _owner(db, args.owner))
        einst = await get_or_create_settings(db)
        key = (einst.google_places_api_key or "").strip()
        if not args.nur_impressum and not key:
            print("Kein Google-Places-Schlüssel im Arbeitsbereich (Einstellungen → "
                  "Google Places). Ohne ihn geht nur --nur-impressum.", file=sys.stderr)
            raise SystemExit(2)

        auswahl, grund = await _auswahl(db, args)
        print(f"{len(auswahl)} Firmen — {grund}, noch ungeprüft")
        if not args.apply:
            print("\nVORSCHAU: Es wird NICHTS abgefragt und nichts geschrieben.")
            if not args.nur_impressum:
                print(f"Ein Lauf mit --apply kostet bis zu {len(auswahl) * 2} "
                      f"Places-Abfragen (Textsuche + Details je Firma).")
            for x in auswahl[:20]:
                print(f"  {x['score']:3}  {x['systeme']} Sys  {x['name'][:44]:46}"
                      f"{'Website bekannt' if x['website'] else ''}")
            if len(auswahl) > 20:
                print(f"  … und {len(auswahl) - 20} weitere")
            return

        sem = asyncio.Semaphore(max(1, args.concurrency))
        mx_cache: dict = {}
        zaehler = {"website": 0, "email": 0, "phone": 0, "decision_maker": 0}
        places_calls = 0
        fehler_liste: list[str] = []

        async with httpx.AsyncClient(timeout=20) as client:
            async def einer(x: dict):
                async with sem:
                    website, quelle, calls = x["website"], "verlinkt" if x["website"] else None, 0
                    telefon = adresse = None
                    if not website and not args.nur_impressum:
                        try:
                            treffer, calls = await resolve_website(x["name"], key, client)
                        except PlacesQuotaExhausted:
                            # Nicht weitermachen: Jede weitere Abfrage läuft ins Leere
                            # und zählt bei Google trotzdem.
                            raise
                        except Exception as exc:
                            # Die MELDUNG, nicht der Klassenname — sonst steht 253-mal
                            # „ValueError" da und man weiß nicht, was los ist (live
                            # passiert: es war das erschöpfte Tageskontingent).
                            return x, None, calls, f"Places: {exc}"
                        if treffer:
                            website, quelle = treffer["website"], "places"
                            telefon, adresse = treffer.get("phone"), treffer.get("address")
                    if not website:
                        return x, None, calls, "keine Website gefunden"
                    fund = await fetch_contacts(website)
                    return x, (fund, website, quelle, telefon, adresse), calls, None

            aufgaben = [asyncio.ensure_future(einer(x)) for x in auswahl]
            kontingent_weg = False
            for coro in asyncio.as_completed(aufgaben):
                try:
                    x, ergebnis, calls, fehler = await coro
                except PlacesQuotaExhausted as exc:
                    if not kontingent_weg:
                        kontingent_weg = True
                        print(f"\n  ⛔ {exc}\n     Lauf abgebrochen. Bereits Geprüftes ist "
                              f"gespeichert; ein neuer Lauf macht dort weiter.")
                        for a in aufgaben:
                            a.cancel()
                    continue
                except asyncio.CancelledError:
                    continue
                places_calls += calls
                if fehler:
                    fehler_liste.append(f"{x['name']}: {fehler}")
                    print(f"  ✗ {x['name'][:40]:42} {fehler}")
                    continue
                fund, website, quelle, telefon, adresse = ergebnis

                email, status = fund.email, None
                if email:
                    pruefung = await verify_email(email, mx_cache=mx_cache)
                    status = pruefung.status.value if pruefung.status else None
                    if status in KAPUTT:
                        email, status = None, None
                telefon = fund.phone or telefon

                evidence = dict(fund.evidence or {})
                if quelle == "places":
                    # Herkunft der Website festhalten: aufgelöst ist schwächer belegt
                    # als im Verzeichnis verlinkt.
                    _beleg(evidence, "website", "Google Places (Namensauflösung)", None)
                    if telefon and not fund.phone:
                        _beleg(evidence, "phone", "Google Places", None)
                    if adresse:
                        _beleg(evidence, "address", "Google Places", None)

                gefunden = [k for k, v in (("website", website), ("email", email),
                                           ("phone", telefon),
                                           ("decision_maker", fund.decision_maker)) if v]
                for k in gefunden:
                    zaehler[k] += 1
                print(f"  · {x['name'][:40]:42} {', '.join(gefunden)}  [{quelle}]")

                # Auf ALLE Nennungen der Firma schreiben: Die Kontaktdaten gehören der
                # Firma, nicht dem Paar (Firma, Hersteller). Vorhandenes nie mit Leere
                # überschreiben.
                for r in x["zeilen"]:
                    if website:
                        r.website = website[:255]
                        r.website_source = quelle
                    if email:
                        r.email, r.email_status = email[:255], status
                    if telefon:
                        r.phone = telefon[:60]
                    if fund.decision_maker:
                        r.decision_maker = fund.decision_maker[:255]
                    if adresse:
                        r.address = adresse[:255]
                    if evidence:
                        r.contact_evidence = {**(r.contact_evidence or {}), **evidence}
                    r.contact_checked_at = now()

        await db.commit()
        # **Zähler auch bei erfolglosen Abfragen erhöhen** — Google rechnet sie ab.
        # `bump` ist rein und liefert (Periode, Stand); geschrieben wird hier.
        if places_calls and key:
            einst.google_places_period, einst.google_places_calls = bump(
                einst.google_places_period, einst.google_places_calls,
                increment=places_calls)
            await db.commit()

        print(f"\n{len(auswahl)} Firmen geprüft · Places-Abfragen: {places_calls}")
        for k, v in zaehler.items():
            anteil = f"{v / len(auswahl) * 100:.0f}%" if auswahl else "—"
            print(f"  {k:16} {v:4}  ({anteil})")
        if fehler_liste:
            print(f"{len(fehler_liste)} ohne Ergebnis")


if __name__ == "__main__":
    asyncio.run(main())
