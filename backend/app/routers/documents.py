import base64
import io
import os
import uuid
import zipfile
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from weasyprint import HTML

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.customer import Customer
from app.models.document_template import DocumentTemplate
from app.schemas.document_template import DocumentTemplateResponse, GenerateRequest

router = APIRouter(
    prefix="/api/documents",
    tags=["documents"],
    dependencies=[Depends(get_current_user)],
)

PAGE_WRAPPER = """<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8"><style>
@page {{ size: A4; margin: 2cm 2.5cm 3cm 2.5cm; }}
body {{ font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 10pt; color: #333; line-height: 1.6; }}
h1 {{ font-size: 16pt; color: #1a1a2e; margin-bottom: 10px; border-bottom: 2px solid #1a1a2e; padding-bottom: 8px; }}
h2 {{ font-size: 12pt; color: #1a1a2e; margin-top: 20px; margin-bottom: 8px; }}
h3 {{ font-size: 10pt; color: #1a1a2e; margin-top: 15px; margin-bottom: 5px; }}
p {{ margin-bottom: 8px; text-align: justify; }}
ul, ol {{ margin-bottom: 8px; padding-left: 20px; }}
li {{ margin-bottom: 4px; }}
.header {{ display: flex; justify-content: space-between; margin-bottom: 25px; }}
.header-left {{ font-size: 9pt; color: #666; }}
.header-right {{ text-align: right; font-size: 9pt; color: #666; }}
.parties {{ margin-bottom: 20px; padding: 12px 15px; background: #f5f5f5; border-radius: 6px; font-size: 9pt; }}
.parties strong {{ color: #1a1a2e; }}
.signature {{ margin-top: 50px; display: flex; justify-content: space-between; page-break-inside: avoid; }}
.sig-block {{ width: 42%; padding-top: 8px; font-size: 9pt; color: #666; }}
.sig-line {{ border-top: 1px solid #333; padding-top: 5px; margin-top: 40px; }}
</style></head><body>
<div class="header">
<div class="header-left">{anbieter_firma}<br>{anbieter_adresse}<br>{anbieter_email}</div>
<div class="header-right">Datum: {datum}</div>
</div>
<div class="parties">
<strong>Auftraggeber:</strong> {firma}, {kunde_adresse}, {kunde_email}<br>
<strong>Auftragnehmer:</strong> {anbieter_firma}, {anbieter_adresse}, {anbieter_email}
</div>
{content}
<div class="signature">
<div class="sig-block"><div class="sig-line"><br><br><br>Ort, Datum, Unterschrift Auftraggeber<br>{firma}</div></div>
<div class="sig-block">{signature_html}<div class="sig-line">{datum}<br>{anbieter_name}<br>{anbieter_firma}</div></div>
</div>
</body></html>"""


def _load_signature_html() -> str:
    sig_path = settings.SIGNATURE_PATH
    if sig_path and os.path.isfile(sig_path):
        with open(sig_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f'<img src="data:image/png;base64,{b64}" style="max-height:70px;max-width:250px;margin-bottom:8px;display:block;" alt="Unterschrift">'
    return ""


def _replace_placeholders(text: str, customer: Customer) -> str:
    today = date.today()
    replacements = {
        "{firma}": customer.company or customer.name,
        "{kunde_name}": customer.name,
        "{kunde_adresse}": (customer.address or "").replace("\n", ", "),
        "{kunde_email}": customer.email or "",
        "{kunde_telefon}": customer.phone or "",
        "{anbieter_name}": settings.BUSINESS_OWNER,
        "{anbieter_firma}": settings.BUSINESS_NAME,
        "{anbieter_adresse}": settings.BUSINESS_ADDRESS,
        "{anbieter_email}": settings.BUSINESS_EMAIL,
        "{anbieter_web}": settings.BUSINESS_WEB,
        "{anbieter_steuernr}": settings.BUSINESS_TAX_NUMBER,
        "{datum}": today.strftime("%d.%m.%Y"),
        "{jahr}": str(today.year),
        "{signature_html}": _load_signature_html(),
    }
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


@router.get("/templates", response_model=list[DocumentTemplateResponse])
async def list_templates(db: AsyncSession = Depends(get_db)) -> list:
    result = await db.execute(select(DocumentTemplate).order_by(DocumentTemplate.category, DocumentTemplate.name))
    return [DocumentTemplateResponse.model_validate(t) for t in result.scalars().all()]


@router.post("/templates/seed")
async def seed_templates(db: AsyncSession = Depends(get_db)) -> dict:
    count = 0
    for tmpl in SYSTEM_TEMPLATES:
        result = await db.execute(select(DocumentTemplate).where(DocumentTemplate.name == tmpl["name"]))
        existing = result.scalar_one_or_none()
        if existing:
            existing.content = tmpl["content"]
            existing.description = tmpl["description"]
            existing.category = tmpl["category"]
        else:
            db.add(DocumentTemplate(**tmpl, is_system=True))
            count += 1
    await db.flush()
    return {"created": count, "total": len(SYSTEM_TEMPLATES)}


@router.post("/generate-all")
async def generate_all_documents(
    customer_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generiert alle Vorlagen für einen Kunden als ZIP mit Signatur."""
    customer = await db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    result = await db.execute(select(DocumentTemplate).order_by(DocumentTemplate.category, DocumentTemplate.name))
    templates = result.scalars().all()

    if not templates:
        raise HTTPException(status_code=404, detail="Keine Vorlagen vorhanden")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for tmpl in templates:
            content = _replace_placeholders(tmpl.content, customer)
            full_html = _replace_placeholders(PAGE_WRAPPER.replace("{content}", content), customer)
            pdf = HTML(string=full_html).write_pdf()
            filename = f"{tmpl.category}/{tmpl.name.replace(' ', '-')}.pdf"
            zf.writestr(filename, pdf)

    buf.seek(0)
    customer_label = (customer.company or customer.name).replace(" ", "-")
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="Vertragsdokumente_{customer_label}.zip"'},
    )


@router.post("/generate")
async def generate_document(data: GenerateRequest, db: AsyncSession = Depends(get_db)) -> Response:
    tmpl = await db.get(DocumentTemplate, data.template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden")
    customer = await db.get(Customer, data.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    content = _replace_placeholders(tmpl.content, customer)
    full_html = _replace_placeholders(PAGE_WRAPPER.replace("{content}", content), customer)
    pdf = HTML(string=full_html).write_pdf()

    filename = f"{tmpl.name.replace(' ', '-')}_{customer.company or customer.name}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/preview")
async def preview_document(
    template_id: uuid.UUID = Query(...),
    customer_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> Response:
    tmpl = await db.get(DocumentTemplate, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden")
    customer = await db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    content = _replace_placeholders(tmpl.content, customer)
    full_html = _replace_placeholders(PAGE_WRAPPER.replace("{content}", content), customer)
    return Response(content=full_html, media_type="text/html")


# ─── System Templates ────────────────────────────────────────────────────────

SYSTEM_TEMPLATES = [
    {
        "name": "Auftragsverarbeitungsvertrag (AV-Vertrag)",
        "category": "datenschutz",
        "description": "DSGVO Art. 28 konformer Vertrag über die Auftragsverarbeitung personenbezogener Daten",
        "content": """<h1>Auftragsverarbeitungsvertrag</h1>
<p>gemäß Art. 28 Datenschutz-Grundverordnung (DSGVO)</p>
<p>zwischen <strong>{firma}</strong> (nachfolgend „Verantwortlicher") und <strong>{anbieter_firma}</strong> (nachfolgend „Auftragsverarbeiter")</p>

<h2>§ 1 Gegenstand und Dauer</h2>
<p>(1) Der Auftragsverarbeiter verarbeitet personenbezogene Daten im Auftrag des Verantwortlichen auf Grundlage dieses Vertrages.</p>
<p>(2) Die Laufzeit dieses Vertrages richtet sich nach der Laufzeit des Hauptvertrages über die Erbringung von IT-Dienstleistungen.</p>

<h2>§ 2 Art und Zweck der Verarbeitung</h2>
<p>(1) Art der Verarbeitung: Erhebung, Speicherung, Veränderung, Übermittlung, Löschung von personenbezogenen Daten im Rahmen von Webentwicklung, Hosting und IT-Beratung.</p>
<p>(2) Zweck der Verarbeitung: Erbringung der vertraglich vereinbarten IT-Dienstleistungen, insbesondere Website-Erstellung, -Hosting und -Wartung.</p>

<h2>§ 3 Art der personenbezogenen Daten</h2>
<p>Gegenstand der Verarbeitung sind folgende Datenkategorien:</p>
<ul>
<li>Kontaktdaten (Name, E-Mail-Adresse, Telefonnummer, Anschrift)</li>
<li>Nutzungsdaten (IP-Adressen, Zugriffszeiten, besuchte Seiten)</li>
<li>Inhaltsdaten (Texte, Bilder, Dokumente des Verantwortlichen)</li>
<li>Vertragsdaten (Vertragsgegenstand, Laufzeit, Kundenkategorie)</li>
</ul>

<h2>§ 4 Kategorien betroffener Personen</h2>
<p>Die Kategorien der durch die Verarbeitung betroffenen Personen umfassen:</p>
<ul>
<li>Kunden und Interessenten des Verantwortlichen</li>
<li>Mitarbeiter und Ansprechpartner des Verantwortlichen</li>
<li>Website-Besucher</li>
<li>Newsletter-Abonnenten</li>
</ul>

<h2>§ 5 Pflichten des Auftragsverarbeiters</h2>
<p>(1) Der Auftragsverarbeiter verarbeitet personenbezogene Daten ausschließlich auf dokumentierte Weisung des Verantwortlichen.</p>
<p>(2) Der Auftragsverarbeiter gewährleistet, dass sich die zur Verarbeitung der personenbezogenen Daten befugten Personen zur Vertraulichkeit verpflichtet haben.</p>
<p>(3) Der Auftragsverarbeiter ergreift alle gemäß Art. 32 DSGVO erforderlichen technischen und organisatorischen Maßnahmen.</p>
<p>(4) Der Auftragsverarbeiter nimmt keine Unterauftragsverarbeiter ohne vorherige schriftliche Genehmigung des Verantwortlichen in Anspruch.</p>
<p>(5) Der Auftragsverarbeiter unterstützt den Verantwortlichen bei der Erfüllung der Pflichten aus Art. 32–36 DSGVO.</p>
<p>(6) Der Auftragsverarbeiter unterstützt den Verantwortlichen bei der Beantwortung von Anträgen betroffener Personen gemäß Kapitel III DSGVO.</p>
<p>(7) Nach Abschluss der Verarbeitung löscht der Auftragsverarbeiter sämtliche personenbezogene Daten oder gibt sie zurück.</p>
<p>(8) Der Auftragsverarbeiter stellt dem Verantwortlichen alle erforderlichen Informationen zum Nachweis der Einhaltung der Pflichten zur Verfügung.</p>
<p>(9) Der Auftragsverarbeiter informiert den Verantwortlichen unverzüglich, wenn er der Auffassung ist, dass eine Weisung gegen Datenschutzvorschriften verstößt.</p>
<p>(10) Der Auftragsverarbeiter meldet Verletzungen des Schutzes personenbezogener Daten unverzüglich an den Verantwortlichen.</p>

<h2>§ 6 Unterauftragsverarbeiter</h2>
<p>(1) Der Auftragsverarbeiter darf Unterauftragsverarbeiter nur mit vorheriger schriftlicher Zustimmung des Verantwortlichen einsetzen.</p>
<p>(2) Dem Unterauftragsverarbeiter sind vertraglich dieselben Datenschutzpflichten aufzuerlegen.</p>

<h2>§ 7 Kontrollrechte</h2>
<p>(1) Der Verantwortliche hat das Recht, Überprüfungen durchzuführen oder durch einen Prüfer durchführen zu lassen.</p>
<p>(2) Der Auftragsverarbeiter stellt sicher, dass sich der Verantwortliche von der Einhaltung der Pflichten überzeugen kann.</p>

<h2>§ 8 Technische und organisatorische Maßnahmen</h2>
<p>Der Auftragsverarbeiter hat folgende Maßnahmen implementiert:</p>
<ul>
<li>Zutrittskontrolle: Schutz vor unbefugtem Zutritt zu Datenverarbeitungsanlagen</li>
<li>Zugangskontrolle: Schutz vor unbefugter Systembenutzung</li>
<li>Zugriffskontrolle: Berechtigungskonzept, Protokollierung</li>
<li>Weitergabekontrolle: Verschlüsselung bei Datenübertragung (TLS/SSL)</li>
<li>Eingabekontrolle: Protokollierung von Eingaben, Änderungen und Löschungen</li>
<li>Verfügbarkeitskontrolle: Regelmäßige Backups, Notfallkonzept</li>
<li>Trennungskontrolle: Mandantenfähigkeit, getrennte Datenverarbeitung</li>
</ul>

<h2>§ 9 Haftung</h2>
<p>Für Schäden, die durch eine nicht ordnungsgemäße Verarbeitung entstehen, haftet der Auftragsverarbeiter nach den gesetzlichen Bestimmungen.</p>

<h2>§ 10 Laufzeit und Kündigung</h2>
<p>(1) Dieser Vertrag gilt für die Dauer des Hauptvertrages.</p>
<p>(2) Das Recht zur außerordentlichen Kündigung aus wichtigem Grund bleibt unberührt.</p>
<p>(3) Der Auftragsverarbeiter kann den Vertrag kündigen, wenn der Verantwortliche wiederholt gegen Weisungen verstößt.</p>""",
    },
    {
        "name": "Datenschutzerklärung für Dienstleister",
        "category": "datenschutz",
        "description": "Information über die Verarbeitung personenbezogener Daten im Rahmen der Dienstleistung",
        "content": """<h1>Datenschutzerklärung</h1>
<p>Information gemäß Art. 13, 14 DSGVO über die Verarbeitung personenbezogener Daten</p>

<h2>§ 1 Verantwortlicher</h2>
<p>{anbieter_firma}<br>{anbieter_name}<br>{anbieter_adresse}<br>E-Mail: {anbieter_email}<br>Web: {anbieter_web}</p>

<h2>§ 2 Art der verarbeiteten Daten</h2>
<p>Im Rahmen unserer Dienstleistung verarbeiten wir folgende Kategorien personenbezogener Daten:</p>
<ul>
<li>Bestandsdaten (Name, Adresse, Kontaktdaten)</li>
<li>Vertragsdaten (Vertragsgegenstand, Laufzeit, Zahlungsinformationen)</li>
<li>Nutzungsdaten (Zugriffszeiten, IP-Adressen, Logfiles)</li>
<li>Inhaltsdaten (Texte, Bilder und sonstige Inhalte des Auftraggebers)</li>
</ul>

<h2>§ 3 Zweck der Verarbeitung</h2>
<p>Die Verarbeitung erfolgt zu folgenden Zwecken:</p>
<ul>
<li>Erbringung der vertraglich vereinbarten IT-Dienstleistungen</li>
<li>Website-Erstellung, -Hosting und -Wartung</li>
<li>Kommunikation und Projektabwicklung</li>
<li>Rechnungsstellung und Buchhaltung</li>
<li>Erfüllung gesetzlicher Aufbewahrungspflichten</li>
</ul>

<h2>§ 4 Rechtsgrundlage</h2>
<p>Die Verarbeitung erfolgt auf Grundlage von:</p>
<ul>
<li>Art. 6 Abs. 1 lit. b DSGVO — Vertragserfüllung</li>
<li>Art. 6 Abs. 1 lit. c DSGVO — Rechtliche Verpflichtung (z.B. Steuerrecht)</li>
<li>Art. 6 Abs. 1 lit. f DSGVO — Berechtigtes Interesse (z.B. IT-Sicherheit)</li>
</ul>

<h2>§ 5 Weitergabe an Dritte</h2>
<p>Eine Weitergabe personenbezogener Daten an Dritte erfolgt nur, soweit dies zur Vertragserfüllung erforderlich ist. Dies betrifft insbesondere:</p>
<ul>
<li>Hosting-Provider für den Betrieb von Websites und Servern</li>
<li>Domain-Registrare für die Registrierung von Domains</li>
<li>E-Mail-Dienstleister für den Betrieb von E-Mail-Konten</li>
<li>Steuerberater im Rahmen der Buchhaltungspflichten</li>
</ul>
<p>Mit allen Dienstleistern bestehen Auftragsverarbeitungsverträge gemäß Art. 28 DSGVO.</p>

<h2>§ 6 Speicherdauer</h2>
<p>Personenbezogene Daten werden gelöscht, sobald der Zweck der Verarbeitung entfällt und keine gesetzlichen Aufbewahrungspflichten entgegenstehen. Steuerrechtliche Aufbewahrungsfristen betragen bis zu 10 Jahre.</p>

<h2>§ 7 Rechte der betroffenen Personen</h2>
<p>Sie haben das Recht auf:</p>
<ul>
<li>Auskunft über Ihre gespeicherten Daten (Art. 15 DSGVO)</li>
<li>Berichtigung unrichtiger Daten (Art. 16 DSGVO)</li>
<li>Löschung Ihrer Daten (Art. 17 DSGVO)</li>
<li>Einschränkung der Verarbeitung (Art. 18 DSGVO)</li>
<li>Datenübertragbarkeit (Art. 20 DSGVO)</li>
<li>Widerspruch gegen die Verarbeitung (Art. 21 DSGVO)</li>
</ul>

<h2>§ 8 Beschwerderecht</h2>
<p>Sie haben das Recht, sich bei einer Datenschutz-Aufsichtsbehörde über die Verarbeitung Ihrer personenbezogenen Daten zu beschweren.</p>""",
    },
    {
        "name": "Bestellung zum externen Datenschutzbeauftragten",
        "category": "datenschutz",
        "description": "Vertrag über die Bestellung als externer Datenschutzbeauftragter gemäß Art. 37 DSGVO",
        "content": """<h1>Vertrag über die Bestellung zum externen Datenschutzbeauftragten</h1>
<p>gemäß Art. 37 ff. DSGVO, § 38 BDSG</p>

<h2>§ 1 Bestellung</h2>
<p>(1) {firma} (nachfolgend „Verantwortlicher") bestellt hiermit {anbieter_firma}, vertreten durch {anbieter_name}, zum externen Datenschutzbeauftragten gemäß Art. 37 Abs. 6 DSGVO.</p>
<p>(2) Die Bestellung wird bei der zuständigen Aufsichtsbehörde angezeigt und die Kontaktdaten des Datenschutzbeauftragten veröffentlicht.</p>

<h2>§ 2 Aufgaben</h2>
<p>Der Datenschutzbeauftragte nimmt folgende Aufgaben gemäß Art. 39 DSGVO wahr:</p>
<ul>
<li>Unterrichtung und Beratung des Verantwortlichen und seiner Beschäftigten</li>
<li>Überwachung der Einhaltung der DSGVO und anderer Datenschutzvorschriften</li>
<li>Beratung im Zusammenhang mit der Datenschutz-Folgenabschätzung (Art. 35 DSGVO)</li>
<li>Zusammenarbeit mit der Aufsichtsbehörde</li>
<li>Anlaufstelle für die Aufsichtsbehörde</li>
<li>Schulung und Sensibilisierung der Mitarbeiter</li>
<li>Führung des Verzeichnisses von Verarbeitungstätigkeiten (Art. 30 DSGVO)</li>
<li>Prüfung und Beratung bei Auftragsverarbeitungsverträgen</li>
</ul>

<h2>§ 3 Stellung und Unabhängigkeit</h2>
<p>(1) Der Datenschutzbeauftragte ist bei der Erfüllung seiner Aufgaben weisungsfrei (Art. 38 Abs. 3 DSGVO).</p>
<p>(2) Er berichtet unmittelbar der höchsten Managementebene.</p>
<p>(3) Der Verantwortliche stellt sicher, dass der Datenschutzbeauftragte ordnungsgemäß und frühzeitig in alle Datenschutzfragen eingebunden wird.</p>

<h2>§ 4 Pflichten des Verantwortlichen</h2>
<p>(1) Der Verantwortliche stellt dem Datenschutzbeauftragten die zur Aufgabenerfüllung erforderlichen Ressourcen und Informationen zur Verfügung.</p>
<p>(2) Der Verantwortliche informiert den Datenschutzbeauftragten unverzüglich über datenschutzrelevante Vorfälle.</p>

<h2>§ 5 Vergütung</h2>
<p>Die Vergütung des Datenschutzbeauftragten richtet sich nach der gesonderten Vergütungsvereinbarung.</p>

<h2>§ 6 Geheimhaltung</h2>
<p>Der Datenschutzbeauftragte ist zur Geheimhaltung über die Identität betroffener Personen sowie über Umstände, die Rückschlüsse auf betroffene Personen zulassen, verpflichtet (§ 38 Abs. 2 i.V.m. § 6 Abs. 5 BDSG).</p>

<h2>§ 7 Laufzeit und Kündigung</h2>
<p>(1) Dieser Vertrag wird auf unbestimmte Zeit geschlossen.</p>
<p>(2) Die Kündigung ist mit einer Frist von 3 Monaten zum Monatsende möglich.</p>
<p>(3) Die Abberufung als Datenschutzbeauftragter ist nur unter den Voraussetzungen des § 6 Abs. 4 BDSG möglich.</p>""",
    },
    {
        "name": "Vertrag über Website-Erstellung",
        "category": "dienstleistung",
        "description": "Werkvertrag über Konzeption, Design und technische Umsetzung einer Website",
        "content": """<h1>Vertrag über Website-Erstellung</h1>

<h2>§ 1 Vertragsgegenstand</h2>
<p>(1) {anbieter_firma} (nachfolgend „Auftragnehmer") erstellt für {firma} (nachfolgend „Auftraggeber") eine Website gemäß den vereinbarten Spezifikationen.</p>
<p>(2) Der genaue Leistungsumfang ergibt sich aus dem Angebot bzw. dem Pflichtenheft, das Bestandteil dieses Vertrages ist.</p>

<h2>§ 2 Leistungsumfang</h2>
<p>Der Auftragnehmer erbringt folgende Leistungen:</p>
<ul>
<li>Konzeption und Informationsarchitektur</li>
<li>Webdesign (Desktop, Tablet, Mobil)</li>
<li>Technische Umsetzung (Frontend und ggf. Backend)</li>
<li>Content-Management-System Einrichtung</li>
<li>Responsive Anpassung für alle gängigen Endgeräte</li>
<li>SEO-Grundoptimierung</li>
<li>Testphase und Fehlerbehebung</li>
<li>Einweisung in die Bedienung des CMS</li>
</ul>

<h2>§ 3 Mitwirkungspflichten des Auftraggebers</h2>
<p>(1) Der Auftraggeber stellt dem Auftragnehmer rechtzeitig alle für die Erstellung der Website erforderlichen Inhalte, Texte, Bilder und Informationen zur Verfügung.</p>
<p>(2) Der Auftraggeber benennt einen Ansprechpartner, der für Rückfragen und Abstimmungen zur Verfügung steht.</p>
<p>(3) Verzögerungen, die auf fehlende Mitwirkung des Auftraggebers zurückzuführen sind, gehen nicht zu Lasten des Auftragnehmers.</p>

<h2>§ 4 Vergütung und Zahlungsbedingungen</h2>
<p>(1) Die Vergütung richtet sich nach dem vereinbarten Angebot.</p>
<p>(2) Rechnungen sind innerhalb von 14 Tagen nach Zugang ohne Abzug zahlbar.</p>
<p>(3) Bei Projekten über 2.000 EUR ist eine Anzahlung von 50% bei Auftragserteilung fällig.</p>

<h2>§ 5 Abnahme</h2>
<p>(1) Nach Fertigstellung wird die Website dem Auftraggeber zur Abnahme präsentiert.</p>
<p>(2) Der Auftraggeber hat die Website innerhalb von 14 Tagen zu prüfen und etwaige Mängel schriftlich mitzuteilen.</p>
<p>(3) Erfolgt keine Rückmeldung innerhalb dieser Frist, gilt die Website als abgenommen.</p>
<p>(4) Unwesentliche Mängel berechtigen nicht zur Verweigerung der Abnahme.</p>

<h2>§ 6 Gewährleistung</h2>
<p>(1) Der Auftragnehmer gewährleistet, dass die Website den vereinbarten Spezifikationen entspricht.</p>
<p>(2) Die Gewährleistungsfrist beträgt 12 Monate ab Abnahme.</p>
<p>(3) Mängel werden im Rahmen der Nacherfüllung kostenfrei beseitigt.</p>

<h2>§ 7 Haftung</h2>
<p>(1) Der Auftragnehmer haftet unbeschränkt für Vorsatz und grobe Fahrlässigkeit.</p>
<p>(2) Bei leichter Fahrlässigkeit haftet der Auftragnehmer nur bei Verletzung wesentlicher Vertragspflichten, begrenzt auf den vorhersehbaren, vertragstypischen Schaden.</p>
<p>(3) Die Haftung ist auf die Höhe der vereinbarten Vergütung begrenzt.</p>

<h2>§ 8 Nutzungsrechte und Urheberrecht</h2>
<p>(1) Mit vollständiger Zahlung der Vergütung gehen die Nutzungsrechte an der Website auf den Auftraggeber über.</p>
<p>(2) Der Auftragnehmer behält das Recht, die Website als Referenz zu verwenden, sofern dem nicht schriftlich widersprochen wird.</p>
<p>(3) Quellcode-Bibliotheken Dritter (Open Source) unterliegen deren jeweiligen Lizenzbedingungen.</p>

<h2>§ 9 Vertraulichkeit</h2>
<p>Beide Parteien verpflichten sich, vertrauliche Informationen der anderen Partei geheim zu halten und nur für die Zwecke dieses Vertrages zu verwenden.</p>

<h2>§ 10 Kündigung</h2>
<p>(1) Der Vertrag kann von beiden Parteien aus wichtigem Grund gekündigt werden.</p>
<p>(2) Bei Kündigung durch den Auftraggeber sind die bis dahin erbrachten Leistungen zu vergüten.</p>

<h2>§ 11 Schlussbestimmungen</h2>
<p>(1) Änderungen und Ergänzungen dieses Vertrages bedürfen der Schriftform.</p>
<p>(2) Es gilt das Recht der Bundesrepublik Deutschland.</p>
<p>(3) Sollte eine Bestimmung dieses Vertrages unwirksam sein, bleibt die Wirksamkeit der übrigen Bestimmungen unberührt (salvatorische Klausel).</p>""",
    },
    {
        "name": "Hosting-Vertrag",
        "category": "dienstleistung",
        "description": "Vertrag über Webhosting-Dienstleistungen inkl. Verfügbarkeit und Support",
        "content": """<h1>Hosting-Vertrag</h1>

<h2>§ 1 Leistungsbeschreibung</h2>
<p>(1) {anbieter_firma} stellt {firma} Webhosting-Dienstleistungen zur Verfügung.</p>
<p>(2) Die Leistung umfasst: Bereitstellung von Webspace, Datenbanken, E-Mail-Postfächern, SSL-Zertifikaten sowie technischen Support.</p>

<h2>§ 2 Verfügbarkeit</h2>
<p>(1) Der Auftragnehmer gewährleistet eine Verfügbarkeit von 99,5% im Jahresmittel.</p>
<p>(2) Ausgenommen sind geplante Wartungsarbeiten, die mindestens 48 Stunden im Voraus angekündigt werden.</p>
<p>(3) Höhere Gewalt und Störungen außerhalb des Einflussbereichs des Auftragnehmers sind von der Verfügbarkeitsgarantie ausgenommen.</p>

<h2>§ 3 Datensicherung</h2>
<p>(1) Der Auftragnehmer erstellt tägliche Backups der gehosteten Daten.</p>
<p>(2) Backups werden für mindestens 14 Tage aufbewahrt.</p>
<p>(3) Die Wiederherstellung aus einem Backup erfolgt auf Anfrage des Auftraggebers.</p>

<h2>§ 4 Support</h2>
<p>(1) Technischer Support ist per E-Mail erreichbar.</p>
<p>(2) Reaktionszeit: innerhalb von 24 Stunden an Werktagen.</p>
<p>(3) Bei kritischen Störungen (Website nicht erreichbar) beträgt die Reaktionszeit 4 Stunden.</p>

<h2>§ 5 Vergütung</h2>
<p>(1) Die monatliche Vergütung richtet sich nach dem vereinbarten Tarif.</p>
<p>(2) Die Abrechnung erfolgt im Voraus.</p>

<h2>§ 6 Laufzeit und Kündigung</h2>
<p>(1) Der Vertrag hat eine Mindestlaufzeit von 12 Monaten.</p>
<p>(2) Er verlängert sich automatisch um jeweils 12 Monate, wenn er nicht mit einer Frist von 3 Monaten zum Ende der Laufzeit gekündigt wird.</p>

<h2>§ 7 Datenschutz</h2>
<p>Soweit personenbezogene Daten im Rahmen des Hostings verarbeitet werden, wird ein gesonderter Auftragsverarbeitungsvertrag geschlossen.</p>

<h2>§ 8 Haftung</h2>
<p>(1) Der Auftragnehmer haftet nicht für den Verlust von Daten, soweit der Auftraggeber es versäumt hat, eigene Datensicherungen durchzuführen.</p>
<p>(2) Im Übrigen gelten die gesetzlichen Haftungsregelungen.</p>""",
    },
    {
        "name": "Wartungsvertrag",
        "category": "dienstleistung",
        "description": "Vertrag über laufende Wartung, Updates und technischen Support",
        "content": """<h1>Wartungsvertrag</h1>

<h2>§ 1 Leistungsumfang</h2>
<p>{anbieter_firma} erbringt für {firma} folgende Wartungsleistungen:</p>
<ul>
<li>Regelmäßige Updates des Content-Management-Systems und aller Plugins</li>
<li>Sicherheitsupdates und Patches</li>
<li>Monitoring der Website-Verfügbarkeit</li>
<li>Monatliche Überprüfung der Website-Funktionalität</li>
<li>Regelmäßige Datensicherungen</li>
<li>Technischer Support bei Problemen</li>
</ul>

<h2>§ 2 Reaktionszeiten</h2>
<p>(1) Kritische Störungen (Website nicht erreichbar): Reaktion innerhalb von 4 Stunden an Werktagen.</p>
<p>(2) Mittlere Störungen (Funktionseinschränkungen): Reaktion innerhalb von 24 Stunden an Werktagen.</p>
<p>(3) Geringe Störungen (kosmetische Fehler): Reaktion innerhalb von 72 Stunden an Werktagen.</p>

<h2>§ 3 Servicezeiten</h2>
<p>Die Servicezeiten sind Montag bis Freitag von 9:00 bis 18:00 Uhr (ausgenommen gesetzliche Feiertage).</p>

<h2>§ 4 Vergütung</h2>
<p>(1) Die monatliche Pauschale richtet sich nach dem vereinbarten Tarif.</p>
<p>(2) Leistungen, die über den vereinbarten Umfang hinausgehen, werden nach Aufwand zu dem vereinbarten Stundensatz berechnet.</p>

<h2>§ 5 Laufzeit und Kündigung</h2>
<p>(1) Der Vertrag wird auf unbestimmte Zeit geschlossen.</p>
<p>(2) Er kann mit einer Frist von 3 Monaten zum Monatsende gekündigt werden.</p>
<p>(3) Das Recht zur außerordentlichen Kündigung aus wichtigem Grund bleibt unberührt.</p>

<h2>§ 6 Haftung</h2>
<p>Der Auftragnehmer haftet für Schäden nur bei Vorsatz und grober Fahrlässigkeit. Bei leichter Fahrlässigkeit ist die Haftung auf den vorhersehbaren, vertragstypischen Schaden begrenzt.</p>""",
    },
    {
        "name": "IT-Beratungsvertrag",
        "category": "dienstleistung",
        "description": "Dienstvertrag über IT-Beratung und technische Konzeptionierung",
        "content": """<h1>IT-Beratungsvertrag</h1>

<h2>§ 1 Beratungsgegenstand</h2>
<p>(1) {anbieter_firma} erbringt für {firma} IT-Beratungsleistungen.</p>
<p>(2) Der konkrete Beratungsgegenstand wird im jeweiligen Einzelauftrag festgelegt.</p>

<h2>§ 2 Leistungsumfang</h2>
<p>Die Beratungsleistungen umfassen insbesondere:</p>
<ul>
<li>Analyse bestehender IT-Infrastruktur und Prozesse</li>
<li>Erstellung von Konzepten und technischen Spezifikationen</li>
<li>Bewertung und Auswahl von Technologien und Dienstleistern</li>
<li>Projektbegleitende technische Beratung</li>
<li>Qualitätssicherung und Code-Review</li>
</ul>

<h2>§ 3 Vergütung</h2>
<p>(1) Die Vergütung erfolgt auf Stundenbasis zum vereinbarten Stundensatz.</p>
<p>(2) Reisezeiten werden mit 50% des Stundensatzes berechnet.</p>
<p>(3) Reisekosten werden nach tatsächlichem Aufwand erstattet.</p>
<p>(4) Die Abrechnung erfolgt monatlich auf Basis der geleisteten Stunden.</p>

<h2>§ 4 Vertraulichkeit</h2>
<p>(1) Beide Parteien verpflichten sich zur Geheimhaltung aller im Rahmen der Zusammenarbeit erlangten vertraulichen Informationen.</p>
<p>(2) Diese Pflicht besteht auch nach Beendigung des Vertragsverhältnisses fort.</p>

<h2>§ 5 Haftung</h2>
<p>(1) Die Beratung erfolgt nach bestem Wissen und Gewissen.</p>
<p>(2) Eine Haftung für den wirtschaftlichen Erfolg der Beratung wird nicht übernommen.</p>
<p>(3) Die Haftung ist auf die Höhe der im betreffenden Einzelauftrag vereinbarten Vergütung begrenzt.</p>

<h2>§ 6 Laufzeit</h2>
<p>(1) Dieser Rahmenvertrag wird auf unbestimmte Zeit geschlossen.</p>
<p>(2) Er kann mit einer Frist von 4 Wochen zum Monatsende gekündigt werden.</p>
<p>(3) Laufende Einzelaufträge bleiben von einer Kündigung unberührt.</p>""",
    },
    {
        "name": "Allgemeine Geschäftsbedingungen (AGB)",
        "category": "allgemein",
        "description": "AGB für IT-Dienstleistungen, Webentwicklung und Beratung",
        "content": """<h1>Allgemeine Geschäftsbedingungen</h1>
<p>für IT-Dienstleistungen der {anbieter_firma}</p>

<h2>§ 1 Geltungsbereich</h2>
<p>(1) Diese AGB gelten für alle Verträge zwischen {anbieter_firma} und dem Auftraggeber über IT-Dienstleistungen, Webentwicklung, Hosting, Beratung und damit zusammenhängende Leistungen.</p>
<p>(2) Abweichende Bedingungen des Auftraggebers werden nicht anerkannt, es sei denn, der Auftragnehmer stimmt ihrer Geltung ausdrücklich schriftlich zu.</p>

<h2>§ 2 Vertragsschluss</h2>
<p>(1) Angebote des Auftragnehmers sind freibleibend.</p>
<p>(2) Der Vertrag kommt durch schriftliche Auftragsbestätigung oder durch Beginn der Leistungserbringung zustande.</p>

<h2>§ 3 Leistungen</h2>
<p>(1) Art und Umfang der Leistungen ergeben sich aus dem jeweiligen Angebot bzw. der Leistungsbeschreibung.</p>
<p>(2) Der Auftragnehmer ist berechtigt, Teilleistungen zu erbringen.</p>

<h2>§ 4 Vergütung</h2>
<p>(1) Die Vergütung richtet sich nach dem vereinbarten Angebot.</p>
<p>(2) Alle Preise verstehen sich zuzüglich der gesetzlichen Umsatzsteuer, sofern anwendbar.</p>
<p>(3) Rechnungen sind innerhalb von 14 Tagen nach Zugang zahlbar.</p>
<p>(4) Bei Zahlungsverzug werden Verzugszinsen in gesetzlicher Höhe berechnet.</p>

<h2>§ 5 Mitwirkungspflichten</h2>
<p>(1) Der Auftraggeber stellt alle zur Leistungserbringung erforderlichen Informationen und Materialien rechtzeitig zur Verfügung.</p>
<p>(2) Er benennt einen entscheidungsbefugten Ansprechpartner.</p>
<p>(3) Verzögerungen durch fehlende Mitwirkung berechtigen den Auftragnehmer zur angemessenen Verlängerung der Leistungsfrist.</p>

<h2>§ 6 Abnahme</h2>
<p>(1) Werkleistungen sind vom Auftraggeber innerhalb von 14 Tagen nach Bereitstellung abzunehmen.</p>
<p>(2) Unwesentliche Mängel berechtigen nicht zur Abnahmeverweigerung.</p>

<h2>§ 7 Gewährleistung</h2>
<p>(1) Die Gewährleistungsfrist beträgt 12 Monate ab Abnahme.</p>
<p>(2) Mängel sind unverzüglich schriftlich anzuzeigen.</p>
<p>(3) Der Auftragnehmer hat das Recht zur Nacherfüllung.</p>

<h2>§ 8 Haftung</h2>
<p>(1) Der Auftragnehmer haftet unbeschränkt für Vorsatz und grobe Fahrlässigkeit.</p>
<p>(2) Bei leichter Fahrlässigkeit haftet der Auftragnehmer nur bei Verletzung wesentlicher Vertragspflichten (Kardinalpflichten), begrenzt auf den vorhersehbaren, vertragstypischen Schaden.</p>
<p>(3) Die Haftung für mittelbare Schäden und entgangenen Gewinn ist ausgeschlossen.</p>

<h2>§ 9 Nutzungsrechte</h2>
<p>(1) Mit vollständiger Bezahlung erhält der Auftraggeber ein einfaches, zeitlich unbegrenztes Nutzungsrecht an den erstellten Werken.</p>
<p>(2) Das Urheberrecht verbleibt beim Auftragnehmer.</p>

<h2>§ 10 Vertraulichkeit</h2>
<p>Beide Parteien sind verpflichtet, alle im Rahmen der Zusammenarbeit erhaltenen vertraulichen Informationen geheim zu halten.</p>

<h2>§ 11 Datenschutz</h2>
<p>Die Verarbeitung personenbezogener Daten erfolgt gemäß den geltenden Datenschutzbestimmungen. Soweit erforderlich, wird ein gesonderter Auftragsverarbeitungsvertrag geschlossen.</p>

<h2>§ 12 Schlussbestimmungen</h2>
<p>(1) Es gilt das Recht der Bundesrepublik Deutschland.</p>
<p>(2) Änderungen dieses Vertrages bedürfen der Schriftform.</p>
<p>(3) Sollte eine Bestimmung unwirksam sein, bleibt die Wirksamkeit der übrigen Bestimmungen unberührt.</p>""",
    },
    {
        "name": "Vertraulichkeitsvereinbarung (NDA)",
        "category": "allgemein",
        "description": "Gegenseitige Vertraulichkeitsvereinbarung zum Schutz vertraulicher Informationen",
        "content": """<h1>Vertraulichkeitsvereinbarung</h1>
<p>(Non-Disclosure Agreement / NDA)</p>

<h2>§ 1 Vertrauliche Informationen</h2>
<p>(1) Als „vertrauliche Informationen" gelten sämtliche Informationen und Unterlagen, die eine Partei der anderen im Rahmen der Zusammenarbeit zugänglich macht, unabhängig davon, ob sie als vertraulich gekennzeichnet sind.</p>
<p>(2) Dies umfasst insbesondere:</p>
<ul>
<li>Geschäfts- und Betriebsgeheimnisse</li>
<li>Technische Daten, Quellcode und Dokumentationen</li>
<li>Kunden- und Lieferantendaten</li>
<li>Finanzinformationen und Kalkulationen</li>
<li>Strategien, Pläne und Konzepte</li>
<li>Personenbezogene Daten</li>
</ul>

<h2>§ 2 Geheimhaltungspflichten</h2>
<p>(1) Beide Parteien verpflichten sich, vertrauliche Informationen streng geheim zu halten und ausschließlich für den vereinbarten Zweck zu verwenden.</p>
<p>(2) Vertrauliche Informationen dürfen nur denjenigen Mitarbeitern und Beauftragten zugänglich gemacht werden, die diese für die Durchführung der Zusammenarbeit benötigen.</p>
<p>(3) Diese Personen sind ebenfalls zur Vertraulichkeit zu verpflichten.</p>

<h2>§ 3 Ausnahmen</h2>
<p>Die Geheimhaltungspflicht gilt nicht für Informationen, die:</p>
<ul>
<li>zum Zeitpunkt der Offenlegung bereits öffentlich bekannt waren</li>
<li>nach der Offenlegung ohne Verschulden der empfangenden Partei öffentlich bekannt werden</li>
<li>der empfangenden Partei vor der Offenlegung bereits bekannt waren</li>
<li>von einem Dritten ohne Geheimhaltungspflicht erhalten werden</li>
<li>aufgrund gesetzlicher Verpflichtung offengelegt werden müssen</li>
</ul>

<h2>§ 4 Rückgabe und Löschung</h2>
<p>Nach Beendigung der Zusammenarbeit sind sämtliche vertrauliche Unterlagen zurückzugeben oder nachweislich zu vernichten. Dies umfasst auch digitale Kopien.</p>

<h2>§ 5 Vertragsstrafe</h2>
<p>Bei schuldhafter Verletzung der Geheimhaltungspflicht ist eine Vertragsstrafe in Höhe von 10.000 EUR pro Verstoß zu zahlen. Die Geltendmachung weitergehender Schadensersatzansprüche bleibt unberührt.</p>

<h2>§ 6 Laufzeit</h2>
<p>(1) Diese Vereinbarung tritt mit Unterzeichnung in Kraft.</p>
<p>(2) Die Geheimhaltungspflicht besteht für die Dauer der Zusammenarbeit und 3 Jahre über deren Ende hinaus.</p>
<p>(3) Für Geschäftsgeheimnisse im Sinne des GeschGehG gilt die Geheimhaltungspflicht zeitlich unbegrenzt.</p>""",
    },
    {
        "name": "Support-Vertrag",
        "category": "dienstleistung",
        "description": "Vertrag über technischen Support mit definierten Reaktionszeiten und Prioritäten",
        "content": """<h1>Support-Vertrag</h1>

<h2>§ 1 Supportumfang</h2>
<p>{anbieter_firma} erbringt für {firma} technische Supportleistungen für die vereinbarten IT-Systeme und Anwendungen.</p>
<p>Der Support umfasst:</p>
<ul>
<li>Fehleranalyse und -behebung</li>
<li>Beantwortung technischer Fragen</li>
<li>Unterstützung bei der Bedienung von Software und Systemen</li>
<li>Beratung zu technischen Optimierungen</li>
<li>Remote-Zugriff zur Problemlösung (nach Freigabe)</li>
</ul>

<h2>§ 2 Prioritäten und Reaktionszeiten</h2>
<p><strong>Priorität 1 — Kritisch:</strong> System nicht verfügbar, Geschäftsbetrieb beeinträchtigt. Reaktionszeit: 4 Stunden.</p>
<p><strong>Priorität 2 — Hoch:</strong> Wesentliche Funktionseinschränkung, Workaround möglich. Reaktionszeit: 8 Stunden.</p>
<p><strong>Priorität 3 — Normal:</strong> Einzelne Funktion betroffen, kein Workaround nötig. Reaktionszeit: 24 Stunden.</p>
<p><strong>Priorität 4 — Niedrig:</strong> Kosmetische Fehler, Verbesserungswünsche. Reaktionszeit: 72 Stunden.</p>

<h2>§ 3 Servicezeiten</h2>
<p>(1) Reguläre Servicezeiten: Montag bis Freitag, 9:00–18:00 Uhr (ausgenommen gesetzliche Feiertage).</p>
<p>(2) Supportanfragen außerhalb der Servicezeiten werden am nächsten Werktag bearbeitet.</p>

<h2>§ 4 Eskalation</h2>
<p>(1) Wird eine Störung nicht innerhalb der vereinbarten Reaktionszeit behoben, erfolgt eine Eskalation an die Projektleitung.</p>
<p>(2) Bei anhaltenden Störungen der Priorität 1 wird innerhalb von 24 Stunden ein Statusbericht erstellt.</p>

<h2>§ 5 Vergütung</h2>
<p>(1) Die monatliche Supportpauschale richtet sich nach dem vereinbarten Tarif.</p>
<p>(2) Leistungen, die über den vereinbarten Supportumfang hinausgehen, werden nach Aufwand berechnet.</p>

<h2>§ 6 Laufzeit und Kündigung</h2>
<p>(1) Der Vertrag hat eine Mindestlaufzeit von 12 Monaten.</p>
<p>(2) Er verlängert sich automatisch um jeweils 12 Monate, wenn er nicht mit einer Frist von 3 Monaten zum Ende der Laufzeit gekündigt wird.</p>""",
    },
]
