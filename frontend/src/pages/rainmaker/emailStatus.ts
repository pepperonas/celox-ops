// E-Mail-Qualitätsurteil (aus services/email_verifier.py) → Anzeige.
export const EMAIL_STATUS: Record<string, { label: string; cls: string; title: string }> = {
  valid: { label: '✓ E-Mail ok', cls: 'text-success', title: 'Syntax ok + MX vorhanden (SMTP-frei geprüft)' },
  role: { label: 'Rollen-Adresse', cls: 'text-warning', title: 'info@/support@ … — gültig, aber selten persönlich' },
  disposable: { label: 'Wegwerf-Mail', cls: 'text-danger', title: 'Wegwerf-Provider' },
  no_mx: { label: 'Kein MX', cls: 'text-danger', title: 'Domain nimmt keine Mail an' },
  invalid_syntax: { label: 'Ungültig', cls: 'text-danger', title: 'E-Mail-Syntax ungültig' },
  unknown: { label: 'Ungeprüft', cls: 'text-text-muted', title: 'DNS temporär nicht auflösbar' },
}

export function emailStatusInfo(s: string | null | undefined) {
  return s ? EMAIL_STATUS[s] ?? null : null
}

export const EMAIL_DELIVERABLE = new Set(['valid', 'role'])
export const EMAIL_PROBLEM = new Set(['disposable', 'no_mx', 'invalid_syntax'])
