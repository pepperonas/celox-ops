import { useCallback, useEffect, useLayoutEffect, useRef } from 'react'
import { useLocation, useNavigate, useNavigationType, type NavigateOptions } from 'react-router-dom'

export function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

type AppNavOptions = NavigateOptions & { back?: boolean }

/**
 * Drop-in replacement for useNavigate that tags the navigation direction
 * (`html[data-nav]`) so the content reveal animates from the right (deeper) or
 * left (up a level). The reveal is a lightweight GPU-only CSS animation on the
 * incoming content — NOT the View Transitions API, which snapshots the page and
 * flickers/janks with our async-loading, canvas-heavy views. Pass `{ back: true }`
 * for up-a-level moves. Reduced motion → plain instant navigation.
 */
export function useAppNavigate() {
  const navigate = useNavigate()
  return useCallback((to: string | number, opts: AppNavOptions = {}) => {
    const { back, ...rest } = opts
    const direction = back || (typeof to === 'number' && to < 0) ? 'back' : 'forward'
    if (!prefersReducedMotion()) {
      document.documentElement.dataset.nav = direction
      window.setTimeout(() => {
        if (document.documentElement.dataset.nav === direction) {
          delete document.documentElement.dataset.nav
        }
      }, 360)
    }
    navigate(to as string, rest)
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
