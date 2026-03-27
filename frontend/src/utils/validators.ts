export function validateEmail(email: string): string | null {
  if (!email) return null
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!re.test(email)) {
    return 'Bitte geben Sie eine gueltige E-Mail-Adresse ein.'
  }
  return null
}

export function validateRequired(value: unknown, fieldName: string): string | null {
  if (value === null || value === undefined || value === '') {
    return `${fieldName} ist ein Pflichtfeld.`
  }
  return null
}
