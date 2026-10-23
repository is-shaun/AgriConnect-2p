import { Link } from 'react-router-dom'

export function LogoMark({ className = 'size-8' }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="#1F4D2B" />
      <path d="M16 26V12" stroke="#DDEDCF" strokeWidth="2.4" strokeLinecap="round" />
      <path d="M16 15c-4.5 0-7-2.6-7-7 4.5 0 7 2.6 7 7Zm0 4c4.5 0 7-2.6 7-7-4.5 0-7 2.6-7 7Z" fill="#7BC47F" />
    </svg>
  )
}

export default function Logo({ to = '/', light = false }) {
  return (
    <Link to={to} className="inline-flex items-center gap-2.5" aria-label="AgriConnect home">
      <LogoMark />
      <span className={`font-display text-[1.35rem] font-extrabold tracking-tight ${light ? 'text-white' : 'text-forest'}`}>
        AgriConnect
      </span>
    </Link>
  )
}
