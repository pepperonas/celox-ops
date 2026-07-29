import { describe, expect, it } from 'vitest'
import {
  canAdministerLeads,
  canDelete,
  canEditOutreachTemplates,
  canSendEmail,
  canUsePaidAi,
  isScopedRole,
  navPathsForRole,
} from './permissions'

describe('canDelete', () => {
  it('erlaubt Löschen für Admin und Benutzer', () => {
    expect(canDelete('admin')).toBe(true)
    expect(canDelete('user')).toBe(true)
  })

  it('erlaubt Löschen für Verkäufer — es wirkt als Papierkorb', () => {
    // Ein Verbot wäre die falsche Antwort: Leads aussortieren ist Kernarbeit im
    // Vertrieb. Die Sicherheit kommt aus Umkehrbarkeit + Tagesdeckel.
    expect(canDelete('verkaeufer')).toBe(true)
  })

  it('sperrt Löschen für Mitarbeiter', () => {
    expect(canDelete('mitarbeiter')).toBe(false)
  })

  it('fällt bei unbekannter/fehlender Rolle auf erlaubt zurück (Server entscheidet)', () => {
    expect(canDelete(null)).toBe(true)
    expect(canDelete(undefined)).toBe(true)
    expect(canDelete('')).toBe(true)
  })

  it('toleriert Leerraum', () => {
    expect(canDelete(' mitarbeiter ')).toBe(false)
  })
})

describe('zugeschnittene Rolle', () => {
  it('erkennt verkaeufer', () => {
    expect(isScopedRole('verkaeufer')).toBe(true)
    for (const role of ['admin', 'user', 'mitarbeiter', null, '']) {
      expect(isScopedRole(role)).toBe(false)
    }
  })

  it('liefert genau die erlaubten Nav-Pfade', () => {
    // Muss zur Erlaubnisliste im Backend passen (role_scope.py): Pipeline,
    // Vorlagen, plus Einstellungen für Passwort/2FA.
    expect(navPathsForRole('verkaeufer')).toEqual(['/pipeline', '/akquise', '/einstellungen'])
  })

  it('gibt für alle anderen null zurück (keine Einschränkung)', () => {
    for (const role of ['admin', 'user', 'mitarbeiter', null, undefined, '']) {
      expect(navPathsForRole(role)).toBeNull()
    }
  })
})

describe('Verkäufer-Grenzen', () => {
  it('kein Mailversand, keine bezahlte KI, keine Vorlagen-Änderung', () => {
    expect(canSendEmail('verkaeufer')).toBe(false)
    expect(canUsePaidAi('verkaeufer')).toBe(false)
    expect(canEditOutreachTemplates('verkaeufer')).toBe(false)
  })

  it('keine Aufsicht über die eigene Arbeit', () => {
    // Sonst wäre der Papierkorb kein Sicherheitsnetz, sondern ein
    // Zwischenschritt beim Löschen.
    expect(canAdministerLeads('verkaeufer')).toBe(false)
    expect(canAdministerLeads('mitarbeiter')).toBe(false)
  })

  it('der Inhaber darf all das', () => {
    for (const role of ['admin', 'user']) {
      expect(canSendEmail(role)).toBe(true)
      expect(canUsePaidAi(role)).toBe(true)
      expect(canEditOutreachTemplates(role)).toBe(true)
      expect(canAdministerLeads(role)).toBe(true)
    }
  })
})
