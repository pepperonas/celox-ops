#!/usr/bin/env python3
"""Badges mit Codeumfang und Testanzahl aktualisieren — gemessen, nicht geschätzt.

Warum ein Skript und keine handgepflegten Zahlen: die alten Badges behaupteten
„241 tests passing", tatsächlich waren es zu dem Zeitpunkt schon über 900. Eine
Zahl im README, die niemand nachzieht, ist schlechter als keine.

Aufruf (aus dem Repo-Wurzelverzeichnis):

    python3 scripts/update-badges.py            # messen und README-Blöcke ersetzen
    python3 scripts/update-badges.py --check    # nur prüfen (Exit 1 bei Abweichung)
    python3 scripts/update-badges.py --no-tests # nur LoC (ohne Testläufe, schnell)

**Die Testzahl wird nur übernommen, wenn die Suiten wirklich grün sind** — der
Badge sagt „passing", also muss das auch stimmen. Schlägt eine Suite fehl oder
fehlt das Werkzeug, bricht das Skript ab und ändert nichts.

Die Blöcke im README sind mit HTML-Kommentaren markiert; alles dazwischen wird
ersetzt:

    <!-- badges:begin -->  …  <!-- badges:end -->
    <!-- loc-table:begin --> … <!-- loc-table:end -->
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Verzeichnisse, die nie mitgezählt werden (Fremdcode, Build-Artefakte).
SKIP_DIRS = {
    "node_modules", "dist", "build", ".git", "__pycache__", ".venv", "venv",
    ".pytest_cache", ".ruff_cache", ".playwright-mcp", "coverage", ".vite",
}

# Gruppe → (Startverzeichnisse, Endungen, Test-Dateien mitzählen?)
GROUPS: dict[str, tuple[list[str], tuple[str, ...], bool]] = {
    "Backend (Python)":      (["backend/app"], (".py",), False),
    "Frontend (TS/TSX)":     (["frontend/src"], (".ts", ".tsx"), False),
    "PDF-Vorlagen (Jinja)":  (["backend/app/templates"], (".html",), False),
    "Betrieb (Shell/SQL)":   (["scripts", "backend/scripts"], (".sh", ".sql"), False),
    "Tests (Backend)":       (["backend/tests"], (".py",), True),
    "Tests (Frontend)":      (["frontend/src"], (".test.ts", ".test.tsx"), True),
}
# „Anwendungscode" = alles außer Tests; Vorlagen liegen unter backend/app und
# würden sonst doppelt zählen.
APP_GROUPS = ["Backend (Python)", "Frontend (TS/TSX)", "Betrieb (Shell/SQL)"]
TEST_GROUPS = ["Tests (Backend)", "Tests (Frontend)"]


def _is_test(path: Path) -> bool:
    return path.name.endswith((".test.ts", ".test.tsx")) or "tests" in path.parts


def count_lines(dirs: list[str], suffixes: tuple[str, ...], tests: bool) -> tuple[int, int]:
    """(Zeilen, Dateien) für die passenden Dateien."""
    lines = files = 0
    for start in dirs:
        base = ROOT / start
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or any(p in SKIP_DIRS for p in path.parts):
                continue
            if not path.name.endswith(suffixes):
                continue
            if _is_test(path) != tests:
                continue
            try:
                lines += sum(1 for _ in path.open("r", encoding="utf-8", errors="replace"))
            except OSError:
                continue
            files += 1
    return lines, files


def measure_loc() -> dict[str, tuple[int, int]]:
    out = {}
    for name, (dirs, suffixes, tests) in GROUPS.items():
        out[name] = count_lines(dirs, suffixes, tests)
    # Vorlagen sind in „Backend (Python)" nicht enthalten (andere Endung), aber
    # ihr Verzeichnis liegt darunter — sie stehen als eigene Gruppe daneben.
    return out


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def measure_pytest() -> int:
    """Backend-Tests zählen — nur wenn sie GRÜN durchlaufen."""
    cmd = ["docker", "compose", "-f", "docker-compose.dev.yml", "run", "--rm", "--no-deps",
           "-v", f"{ROOT}/backend/tests:/app/tests", "backend", "python", "-m", "pytest", "-q"]
    code, out = _run(cmd, ROOT)
    match = re.search(r"(\d+) passed", out)
    if code != 0 or not match:
        raise SystemExit(
            "Backend-Tests nicht grün oder nicht zählbar — Badges unverändert.\n"
            + out[-1500:])
    if re.search(r"\d+ failed", out):
        raise SystemExit("Backend-Tests enthalten Fehlschläge — Badges unverändert.")
    skipped = re.search(r"(\d+) skipped", out)
    passed = int(match.group(1))
    # Übersprungene Integrationstests (ohne TEST_DATABASE_URL) zählen mit: sie
    # existieren und laufen in der CI.
    return passed + (int(skipped.group(1)) if skipped else 0)


def measure_vitest() -> int:
    """Frontend-Tests zählen — nur wenn sie GRÜN durchlaufen."""
    code, out = _run(["npx", "vitest", "run", "--reporter=basic"], ROOT / "frontend")
    match = re.search(r"Tests\s+(\d+) passed", out)
    if code != 0 or not match:
        raise SystemExit("Frontend-Tests nicht grün oder nicht zählbar — Badges unverändert.\n"
                         + out[-1500:])
    return int(match.group(1))


def de(n: int) -> str:
    """Deutsche Tausendertrennung — im Badge als Punkt (URL-sicher)."""
    return f"{n:,}".replace(",", ".")


def build_badges(loc_app: int, tests_total: int, py: int, ts: int) -> str:
    """Die prominente Badge-Zeile (for-the-badge = groß)."""
    return "\n".join([
        f'[![Lines of Code](https://img.shields.io/badge/Lines_of_Code-{de(loc_app)}-1f6feb'
        f'?style=for-the-badge&logo=files&logoColor=white)](#projektumfang)',
        f'[![Unit Tests](https://img.shields.io/badge/Unit_Tests-{de(tests_total)}_passing-2ea043'
        f'?style=for-the-badge&logo=checkmarx&logoColor=white)](#qualitätssicherung)',
        f'[![pytest](https://img.shields.io/badge/pytest-{py}-0A9EDC'
        f'?style=for-the-badge&logo=pytest&logoColor=white)](backend/tests)',
        f'[![Vitest](https://img.shields.io/badge/Vitest-{ts}-6E9F18'
        f'?style=for-the-badge&logo=vitest&logoColor=white)](frontend/src)',
    ])


def build_table(loc: dict[str, tuple[int, int]], loc_app: int, tests_loc: int) -> str:
    rows = ["| Bereich | Zeilen | Dateien |", "|---|---:|---:|"]
    for name in APP_GROUPS + ["PDF-Vorlagen (Jinja)"]:
        lines, files = loc[name]
        rows.append(f"| {name} | {de(lines)} | {files} |")
    rows.append(f"| **Anwendungscode** | **{de(loc_app)}** | |")
    for name in TEST_GROUPS:
        lines, files = loc[name]
        rows.append(f"| {name} | {de(lines)} | {files} |")
    rows.append(f"| **Testcode** | **{de(tests_loc)}** | |")
    return "\n".join(rows)


def _slug(heading: str) -> str:
    """GitHubs Anker-Regel (vereinfacht): klein, Sonderzeichen weg, Leerzeichen→'-'.

    Wichtig: jedes Leerzeichen wird EINZELN ersetzt — „Rechnungen & Geld" ergibt
    `rechnungen--geld`, nicht `rechnungen-geld`. Umlaute bleibt GitHub erhalten.
    """
    text = heading.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return text.replace(" ", "-")


def fix_anchors(markdown: str, target_text: str) -> str:
    """Links auf nicht vorhandene Überschriften entschärfen.

    Die Badge-Zeile ist für alle READMEs dieselbe, die Überschriften sind es nicht
    (`## Projektumfang` gibt es nur auf Deutsch). Ein Link ins Nichts ist kein
    Beinbruch, aber vermeidbar: fehlt der Anker, bleibt das Bild ohne Link.
    """
    have = {_slug(m.group(1)) for m in re.finditer(r"^#{1,6}\s+(.+)$", target_text, re.M)}

    def strip(match: re.Match) -> str:
        image, anchor = match.group(1), match.group(2)
        return match.group(0) if anchor in have else image

    # [![Bild](url)](#anker) → nur [![Bild](url)], wenn der Anker fehlt.
    return re.sub(r"\[(!\[[^\]]*\]\([^)]*\))\]\(#([^)]+)\)", strip, markdown)


def replace_block(text: str, marker: str, content: str) -> tuple[str, bool]:
    pattern = re.compile(
        rf"(<!-- {marker}:begin -->\n).*?(\n<!-- {marker}:end -->)", re.S)
    if not pattern.search(text):
        return text, False
    return pattern.sub(lambda m: m.group(1) + content + m.group(2), text), True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="nur prüfen, nichts schreiben")
    parser.add_argument("--no-tests", action="store_true",
                        help="Testläufe überspringen (nur LoC aktualisieren)")
    args = parser.parse_args()

    loc = measure_loc()
    loc_app = sum(loc[g][0] for g in APP_GROUPS) + loc["PDF-Vorlagen (Jinja)"][0]
    tests_loc = sum(loc[g][0] for g in TEST_GROUPS)

    print("Codeumfang:")
    for name, (lines, files) in loc.items():
        print(f"  {name:24} {de(lines):>8} Zeilen  ({files} Dateien)")
    print(f"  {'Anwendungscode':24} {de(loc_app):>8} Zeilen")
    print(f"  {'Testcode':24} {de(tests_loc):>8} Zeilen")

    if args.no_tests:
        print("\n--no-tests: Testzahlen bleiben unverändert.")
        return

    print("\nTests zählen (nur grüne Läufe werden übernommen)…")
    py = measure_pytest()
    ts = measure_vitest()
    total = py + ts
    print(f"  pytest {py} · vitest {ts} · gesamt {total}")

    badges = build_badges(loc_app, total, py, ts)
    table = build_table(loc, loc_app, tests_loc)

    changed = []
    for name in ("README.md", "README_DE.md", "README_EN.md"):
        path = ROOT / name
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        text, hit_b = replace_block(original, "badges", fix_anchors(badges, original))
        text, hit_t = replace_block(text, "loc-table", table)
        if not (hit_b or hit_t):
            continue
        if text != original:
            changed.append(name)
            if not args.check:
                path.write_text(text, encoding="utf-8")

    if args.check:
        if changed:
            print("\nVeraltete Badges in: " + ", ".join(changed))
            sys.exit(1)
        print("\nBadges sind aktuell.")
        return
    print("\nAktualisiert: " + (", ".join(changed) if changed else "nichts (schon aktuell)"))


if __name__ == "__main__":
    main()
