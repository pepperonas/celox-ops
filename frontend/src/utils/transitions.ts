import { useCallback, useEffect, useLayoutEffect, useRef } from 'react'
import { flushSync } from 'react-dom'
import { useLocation, useNavigate, useNavigationType, type NavigateOptions } from 'react-router-dom'

export function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/**
 * Run a DOM update inside a View Transition with a directional tag, falling back
 * to an immediate update when unsupported or when the user prefers reduced motion.
 */
export function runViewTransition(update: () => void, direction: 'forward' | 'back' = 'forward') {
  if (prefersReducedMotion() || !('startViewTransition' in document)) {
    update()
    return
  }
  document.documentElement.dataset.nav = direction
  const clear = () => {
    if (document.documentElement.dataset.nav === direction) {
      delete document.documentElement.dataset.nav
    }
  }
  const vt = document.startViewTransition(() => flushSync(update))
  vt.finished.finally(clear)
  // Safety net: never leave the directional flag stuck if `finished` hangs.
  window.setTimeout(clear, 1000)
}

type AppNavOptions = NavigateOptions & { back?: boolean }

/**
 * Drop-in replacement for useNavigate that animates the route change with a
 * directional View Transition. Pass `{ back: true }` for "up a level" moves.
 */
export function useAppNavigate() {
  const navigate = useNavigate()
  return useCallback((to: string | number, opts: AppNavOptions = {}) => {
    const { back, ...rest } = opts
    runViewTransition(
      () => navigate(to as string, rest),
      back || (typeof to === 'number' && to < 0) ? 'back' : 'forward',
    )
  }, [navigate])
}

/**
 * Scroll restoration for a custom scroll container (the app shell's <main>):
 * remembers scrollTop per history entry, restores it on back/forward (POP),
 * and resets to top on new (PUSH) navigations — no animated scroll (instant).
 */
export function useScrollRestoration(ref: React.RefObject<HTMLElement>) {
  const location = useLocation()
  const navType = useNavigationType()
  const positions = useRef<Map<string, number>>(new Map())

  // Before paint: restore/reset scroll AND flag back/forward navigations so
  // entrance animations don't replay on return (they're for first sight only).
  useLayoutEffect(() => {
    const html = document.documentElement
    if (navType === 'POP') {
      html.dataset.pop = '1'
      const el = ref.current
      if (el) el.scrollTop = positions.current.get(location.key) ?? 0
    } else {
      delete html.dataset.pop
      const el = ref.current
      if (el) el.scrollTop = 0
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.key])

  // Continuously remember the current entry's scroll position.
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const onScroll = () => positions.current.set(location.key, el.scrollTop)
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  }, [ref, location.key])
}
