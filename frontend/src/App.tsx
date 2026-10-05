import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom'
import CustomerView from './pages/CustomerView'
import LeadershipView from './pages/LeadershipView'

function Nav() {
  const { pathname } = useLocation()
  const isCustomer = pathname === '/'

  return (
    <nav className="border-b border-white/8 bg-cosmos-950/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <span className="text-cosmos-50 font-semibold tracking-tight">
            {isCustomer ? 'Cosmic Mart' : (
              <span className="flex items-center gap-2">
                Cosmic Mart
                <span className="text-xs font-medium px-2 py-0.5 rounded bg-nova-violet/15 text-nova-violet border border-nova-violet/20 tracking-wide">
                  INTERNAL
                </span>
              </span>
            )}
          </span>
        </div>

        <div className="flex items-center gap-1">
          <NavLink
            to="/"
            className={({ isActive }) =>
              `px-3 py-1.5 rounded-md text-sm transition-colors ${
                isActive
                  ? 'bg-white/8 text-cosmos-50 font-medium'
                  : 'text-cosmos-200 hover:text-cosmos-50'
              }`
            }
          >
            Customer Support
          </NavLink>
          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              `px-3 py-1.5 rounded-md text-sm transition-colors ${
                isActive
                  ? 'bg-white/8 text-cosmos-50 font-medium'
                  : 'text-cosmos-200 hover:text-cosmos-50'
              }`
            }
          >
            Operations
          </NavLink>
        </div>
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        <Nav />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<CustomerView />} />
            <Route path="/dashboard" element={<LeadershipView />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
