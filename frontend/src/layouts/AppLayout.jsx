import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { LayoutDashboard, LineChart, LogOut, Menu, Sprout, Store, UserRound, X } from 'lucide-react'
import Logo from '../components/Logo'
import { useAuth } from '../context/AuthContext'

const nav = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/markets', label: 'Market prices', icon: Store },
  { to: '/crops', label: 'Crops', icon: Sprout },
  { to: '/predict', label: 'Price estimate', icon: LineChart },
  { to: '/profile', label: 'Profile', icon: UserRound },
]

function NavItems({ onNavigate }) {
  return (
    <ul className="space-y-1">
      {nav.map(({ to, label, icon: Icon }) => (
        <li key={to}>
          <NavLink
            to={to}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 min-h-11 font-bold ${
                isActive ? 'bg-white/12 text-white' : 'text-chalk/75 hover:text-white hover:bg-white/6'
              }`
            }
          >
            <Icon className="size-[1.15rem]" aria-hidden="true" />
            {label}
          </NavLink>
        </li>
      ))}
    </ul>
  )
}

export default function AppLayout() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)

  // After logout the route guard sends the user to /login with a "logged out" notice.
  const doLogout = async () => {
    setBusy(true)
    await logout()
  }

  const sidebar = (
    <div className="flex h-full flex-col">
      <div className="px-4 py-5">
        <Logo to="/dashboard" light />
      </div>
      <nav aria-label="App" className="flex-1 px-3">
        <NavItems onNavigate={() => setOpen(false)} />
      </nav>
      <div className="border-t border-white/10 p-4">
        <p className="truncate font-bold text-white">{user?.name}</p>
        <p className="truncate text-sm text-chalk/70">{user?.email}</p>
        <button
          onClick={doLogout}
          disabled={busy}
          className="mt-3 inline-flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm font-bold text-chalk/85 hover:text-white hover:bg-white/6"
        >
          <LogOut className="size-4" aria-hidden="true" /> Log out
        </button>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen md:grid md:grid-cols-[248px_1fr]">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-2 focus:rounded focus:bg-white focus:px-3 focus:py-2">
        Skip to content
      </a>
      <aside className="hidden md:block sticky top-0 h-screen bg-forest">{sidebar}</aside>

      <header className="md:hidden sticky top-0 z-30 flex h-14 items-center justify-between bg-forest px-4">
        <Logo to="/dashboard" light />
        <button className="grid size-11 place-items-center text-white" aria-label="Open menu" aria-expanded={open} onClick={() => setOpen(true)}>
          <Menu aria-hidden="true" />
        </button>
      </header>
      {open && (
        <div className="md:hidden fixed inset-0 z-40" role="dialog" aria-modal="true" aria-label="Menu">
          <button className="absolute inset-0 bg-ink/50" aria-label="Close menu" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-72 max-w-[85%] bg-forest">
            <button className="absolute right-2 top-3 grid size-11 place-items-center text-white" aria-label="Close menu" onClick={() => setOpen(false)}>
              <X aria-hidden="true" />
            </button>
            {sidebar}
          </div>
        </div>
      )}

      <main id="main" className="min-w-0 px-4 py-6 sm:px-6 lg:px-10 lg:py-9">
        <div className="mx-auto max-w-6xl">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
