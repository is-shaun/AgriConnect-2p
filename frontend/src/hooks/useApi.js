import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Run an async loader and track { data, error, loading }. Re-runs when deps change;
 * in-flight requests are aborted when deps change or the component unmounts.
 * The loader receives { signal } to pass to axios.
 */
export function useApi(loader, deps = [], { enabled = true } = {}) {
  const [state, setState] = useState({ data: null, error: null, loading: enabled })
  const [nonce, setNonce] = useState(0)
  const loaderRef = useRef(loader)
  loaderRef.current = loader

  useEffect(() => {
    if (!enabled) {
      setState({ data: null, error: null, loading: false })
      return undefined
    }
    const controller = new AbortController()
    setState((s) => ({ ...s, loading: true, error: null }))
    loaderRef
      .current({ signal: controller.signal })
      .then((data) => !controller.signal.aborted && setState({ data, error: null, loading: false }))
      .catch((error) => {
        if (controller.signal.aborted || error?.name === 'CanceledError') return
        setState({ data: null, error, loading: false })
      })
    return () => controller.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce, enabled])

  const reload = useCallback(() => setNonce((n) => n + 1), [])
  return { ...state, reload }
}

export function useDebounced(value, delay = 300) {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return v
}

const RECENT_KEY = 'agriconnect:recent-crops'

/** Recently viewed crops: non-sensitive UI convenience, stored per browser. */
export function useRecentCrops() {
  const read = () => {
    try {
      const parsed = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]')
      return Array.isArray(parsed) ? parsed.slice(0, 6) : []
    } catch {
      return []
    }
  }
  const [recent, setRecent] = useState(read)
  const remember = useCallback((crop) => {
    if (!crop?.id) return
    setRecent((prev) => {
      const next = [{ id: crop.id, name: crop.name, category: crop.category }, ...prev.filter((c) => c.id !== crop.id)].slice(0, 6)
      try {
        localStorage.setItem(RECENT_KEY, JSON.stringify(next))
      } catch {
        /* storage unavailable: keep in memory only */
      }
      return next
    })
  }, [])
  return { recent, remember }
}
