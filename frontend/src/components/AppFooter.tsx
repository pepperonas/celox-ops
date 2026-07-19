/** App-weiter Footer — Jahr dynamisch, nie hartkodiert (M3E-Rule, Footer-Regel). */
export default function AppFooter() {
  return (
    <footer className="mt-12 pt-6 border-t border-border text-center text-xs text-text-muted">
      © {new Date().getFullYear()} Martin Pfeffer | celox.io
    </footer>
  )
}
