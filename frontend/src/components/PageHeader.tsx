interface PageHeaderProps {
  title: string
  subtitle?: string
  /** Optional action(s) rendered at the trailing edge (e.g. a button). */
  actions?: React.ReactNode
}

/**
 * MD3 Expressive page header — emphasized headline with optional subtitle
 * and trailing actions. Used across all top-level pages for a consistent,
 * bolder type hierarchy.
 */
export default function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <div className="flex flex-wrap justify-between items-start gap-4 mb-6">
      <div>
        <h2 className="text-2xl font-semibold text-text tracking-tight">{title}</h2>
        {subtitle && <p className="text-sm text-text-muted mt-1">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}
