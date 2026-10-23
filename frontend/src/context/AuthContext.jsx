import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { endpoints, setUnauthorizedHandler } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [status, setStatus] = useState('checking') // checking | authenticated | anonymous
  const [signOutReason, setSignOutReason] = useState(null) // 'logout' | 'expired' | null

  useEffect(() => {
    let alive = true
    endpoints
      .me()
      .then(({ user }) => alive && (setUser(user), setStatus('authenticated')))
      .catch(() => alive && (setUser(null), setStatus('anonymous')))
    return () => {
      alive = false
    }
  }, [])

  useEffect(() => {
    // Session expired or revoked while using the app: drop local state; routes redirect to login.
    setUnauthorizedHandler(() => {
      setUser(null)
      setStatus((prev) => {
        if (prev === 'authenticated') setSignOutReason('expired')
        return 'anonymous'
      })
    })
    return () => setUnauthorizedHandler(null)
  }, [])

  const login = useCallback(async (credentials) => {
    const { user } = await endpoints.login(credentials)
    setSignOutReason(null)
    setUser(user)
    setStatus('authenticated')
    return user
  }, [])

  const register = useCallback(async (data) => {
    const { user } = await endpoints.register(data)
    setSignOutReason(null)
    setUser(user)
    setStatus('authenticated')
    return user
  }, [])

  const logout = useCallback(async () => {
    try {
      await endpoints.logout()
    } finally {
      setSignOutReason('logout')
      setUser(null)
      setStatus('anonymous')
    }
  }, [])

  const value = useMemo(
    () => ({ user, status, signOutReason, isAuthenticated: status === 'authenticated', login, register, logout, setUser }),
    [user, status, signOutReason, login, register, logout],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
