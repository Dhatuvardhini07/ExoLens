import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { Activity, Aperture, BookOpenText, Menu, Orbit, Search, X } from 'lucide-react'
import { ImportResult } from './ImportResult'
import { healthCheck } from '../api/client'

const nav = [
  { to: '/', label: 'Overview', icon: Aperture, end: true },
  { to: '/dashboard', label: 'Analytics', icon: Activity },
  { to: '/explore', label: 'Target explorer', icon: Search },
  { to: '/methods', label: 'Methods', icon: BookOpenText },
]

export function AppShell() {
  const [open, setOpen] = useState(false)
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)
  useEffect(() => {
    let active = true
    const check = async () => {
      const online = await healthCheck()
      if (active) setApiOnline(online)
    }
    void check()
    const timer = window.setInterval(() => void check(), 30_000)
    return () => { active = false; window.clearInterval(timer) }
  }, [])
  return <div className="app-shell">
    <header className="mission-header">
      <NavLink to="/" className="brand" onClick={() => setOpen(false)}><span className="brand-mark"><Orbit size={19}/></span><span>exo<span className="brand-light">lens</span><small>TRANSIT RESEARCH WORKSPACE</small></span></NavLink>
      <button className="mobile-menu" onClick={() => setOpen(!open)} aria-label={open ? 'Close menu' : 'Open menu'} aria-expanded={open} aria-controls="primary-navigation">{open ? <X size={19}/> : <Menu size={19}/>}</button>
      <nav id="primary-navigation" className={`mission-nav ${open ? 'mission-nav-open' : ''}`} aria-label="Main navigation">{nav.map(item => <NavLink key={item.to} to={item.to} end={item.end} onClick={() => setOpen(false)} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}><item.icon size={15}/><span>{item.label}</span></NavLink>)}</nav>
      <div className="header-tools"><div className={`connection-state ${apiOnline === false ? 'connection-offline' : ''}`} aria-live="polite"><i/><span>API</span><strong>{apiOnline === null ? 'CHECKING' : apiOnline ? 'ONLINE' : 'OFFLINE'}</strong></div><ImportResult/></div>
    </header>
    <main className="main-area"><div className="page-content"><Outlet/></div><footer className="footer"><span>ExoLens <span className="footer-dim">· Every dip tells a story.</span></span><span>Exploration is not confirmation.</span><a href="https://archive.stsci.edu/tess/" target="_blank" rel="noreferrer">TESS MAST ARCHIVE ↗</a></footer></main>
  </div>
}
