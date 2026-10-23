import { useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import Logo from '../components/Logo'
import { ButtonLink } from '../components/ui'
import { useAuth } from '../context/AuthContext'

const links = [
  { to: '/markets', label: 'Market prices' },
  { to: '/crops', label: 'Crops' },
  { to: '/about', label: 'About' },
  { to: '/contact', label: 'Contact' },
]

export default function PublicLayout() {
  const { isAuthenticated } = useAuth()
  const [open, setOpen] = useState(false)
  const navCls = ({ isActive }) =>
    `px-3 py-2 rounded-lg font-bold ${isActive ? 'text-forest bg-sprout/70' : 'text-ink-soft hover:text-forest'}`

  return (
    <div className="min-h-screen flex flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-2 focus:rounded focus:bg-white focus:px-3 focus:py-2">
        Skip to content
      </a>
      <header className="sticky top-0 z-30 border-b border-line/70 bg-field/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Logo />
          <nav aria-label="Main" className="hidden md:flex items-center gap-1">
            {links.map((l) => (
              <NavLink key={l.to} to={l.to} className={navCls}>
                {l.label}
              </NavLink>
            ))}
          </nav>
          <div className="hidden md:flex items-center gap-2">
            {isAuthenticated ? (
              <ButtonLink to="/dashboard" variant="dark">Open dashboard</ButtonLink>
            ) : (
              <>
                <ButtonLink to="/login" variant="ghost">Log in</ButtonLink>
                <ButtonLink to="/register">Create account</ButtonLink>
              </>
            )}
          </div>
          <button
            className="md:hidden grid size-11 place-items-center rounded-lg text-forest"
            aria-label={open ? 'Close menu' : 'Open menu'}
            aria-expanded={open}
            aria-controls="mobile-nav"
            onClick={() => setOpen((o) => !o)}
          >
            {open ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
          </button>
        </div>
        {open && (
          <nav id="mobile-nav" aria-label="Mobile" className="md:hidden border-t border-line bg-field px-4 pb-4 pt-2">
            <div className="flex flex-col gap-1" onClick={() => setOpen(false)}>
              {links.map((l) => (
                <NavLink key={l.to} to={l.to} className={navCls}>
                  {l.label}
                </NavLink>
              ))}
              {isAuthenticated ? (
                <ButtonLink to="/dashboard" variant="dark" className="mt-2">Open dashboard</ButtonLink>
              ) : (
                <div className="mt-2 grid grid-cols-2 gap-2">
                  <ButtonLink to="/login" variant="secondary">Log in</ButtonLink>
                  <ButtonLink to="/register">Create account</ButtonLink>
                </div>
              )}
            </div>
          </nav>
        )}
      </header>
      <main id="main" className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}

export function Footer() {
  return (
    <footer className="bg-forest-deep text-chalk/80">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 sm:px-6 md:grid-cols-[1.4fr_1fr_1fr]">
        <div>
          <Logo light />
          <p className="mt-3 max-w-sm text-sm">
            Mandi price records, price history and statistical price estimates for Indian crops.
          </p>
        </div>
        <div>
          <h2 className="text-sm font-bold text-white">Explore</h2>
          <ul className="mt-3 space-y-2 text-sm">
            <li><Link className="hover:text-white" to="/markets">Market prices</Link></li>
            <li><Link className="hover:text-white" to="/crops">Crops</Link></li>
            <li><Link className="hover:text-white" to="/predict">Price estimates</Link></li>
          </ul>
        </div>
        <div>
          <h2 className="text-sm font-bold text-white">AgriConnect</h2>
          <ul className="mt-3 space-y-2 text-sm">
            <li><Link className="hover:text-white" to="/about">About</Link></li>
            <li><Link className="hover:text-white" to="/contact">Contact</Link></li>
            <li><Link className="hover:text-white" to="/privacy">Privacy</Link></li>
            <li><Link className="hover:text-white" to="/terms">Terms</Link></li>
          </ul>
        </div>
      </div>
      <p className="border-t border-white/10 px-4 py-4 text-center text-xs text-chalk/60">
        Price estimates are statistical, not guaranteed. The bundled dataset is synthetic demo data.
      </p>
    </footer>
  )
}
