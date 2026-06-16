import { useRef } from 'react'
import { prefersReducedMotion } from '../utils/transitions'

interface TiltCardProps {
  className?: string
  onClick?: () => void
  /** Max tilt in degrees. */
  max?: number
  children: React.ReactNode
}

const canTilt = () =>
  typeof window !== 'undefined'
  && window.matchMedia('(hover: hover) and (pointer: fine)').matches
  && !prefersReducedMotion()

/**
 * A card that tilts a few degrees toward the cursor (damped via CSS transition),
 * gated to real pointers + reduced-motion. Touch users get a plain card.
 */
export default function TiltCard({ className = '', onClick, max = 5, children }: TiltCardProps) {
  const ref = useRef<HTMLDivElement>(null)
  const active = useRef(false)

  const onEnter = () => { active.current = canTilt() }

  const onMove = (e: React.PointerEvent) => {
    if (!active.current) return
    const el = ref.current
    if (!el) return
    const r = el.getBoundingClientRect()
    const px = (e.clientX - r.left) / r.width - 0.5
    const py = (e.clientY - r.top) / r.height - 0.5
    el.style.setProperty('--tx', `${px * max}deg`)
    el.style.setProperty('--ty', `${-py * max}deg`)
  }

  const reset = () => {
    const el = ref.current
    if (!el) return
    el.style.setProperty('--tx', '0deg')
    el.style.setProperty('--ty', '0deg')
  }

  return (
    <div
      ref={ref}
      onClick={onClick}
      onPointerEnter={onEnter}
      onPointerMove={onMove}
      onPointerLeave={reset}
      className={`card-tilt ${className}`}
    >
      {children}
    </div>
  )
}
