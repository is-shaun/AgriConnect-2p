import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

/** Scroll to the top on page navigation (not on query-string changes such as filters). */
export default function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
  return null
}
