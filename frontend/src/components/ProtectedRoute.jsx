import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Spinner } from './feedback'

export default function ProtectedRoute() {
  const { status, signOutReason } = useAuth()
  const location = useLocation()
  if (status === 'checking') {
    return (
      <div className="min-h-screen grid place-items-center">
        <Spinner label="Checking your session" />
      </div>
    )
  }
  if (status !== 'authenticated') {
    if (signOutReason === 'logout') return <Navigate to="/login" replace state={{ message: 'You have been logged out.' }} />
    return (
      <Navigate
        to="/login"
        replace
        state={{
          from: location.pathname + location.search,
          notice: signOutReason === 'expired' ? 'Your session has expired. Please log in again.' : undefined,
        }}
      />
    )
  }
  return <Outlet />
}

/** For /login and /register: signed-in users go straight to the dashboard. */
export function GuestOnlyRoute() {
  const { status } = useAuth()
  if (status === 'checking') return null
  return status === 'authenticated' ? <Navigate to="/dashboard" replace /> : <Outlet />
}
