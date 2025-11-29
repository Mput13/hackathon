import { useState } from 'react'
import { BrowserRouter, Routes, Route, useLocation, useNavigate } from 'react-router-dom'
import './fonts.css'

// Context
import { VersionsProvider } from './contexts/VersionsContext'

// Layout components
import Header from './components/Layout/Header'
import Sidebar from './components/Layout/Sidebar'

// Pages
import Dashboard from './pages/Dashboard'
import Comparison from './pages/Comparison'
import Problems from './pages/Problems'
import Funnels from './pages/Funnels'

function AppContent() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()

  // Map URL path to page ID
  const getCurrentPage = () => {
    const path = location.pathname
    if (path === '/' || path === '/dashboard') return 'dashboard'
    if (path === '/comparison') return 'comparison'
    if (path === '/problems') return 'problems'
    if (path === '/funnels') return 'funnels'
    return 'dashboard'
  }

  const currentPage = getCurrentPage()

  const handleNavigate = (page) => {
    const routes = {
      dashboard: '/dashboard',
      comparison: '/comparison',
      problems: '/problems',
      funnels: '/funnels'
    }
    navigate(routes[page] || '/dashboard')
  }

  return (
    <div className="min-h-screen bg-gray-back text-white flex font-sans selection:bg-accent-red selection:text-white relative">
      {/* Sidebar */}
      <Sidebar 
        currentPage={currentPage}
        setCurrentPage={handleNavigate}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 z-10">
        {/* Header */}
        <Header 
          onMenuToggle={() => setSidebarOpen(!sidebarOpen)}
          currentPage={currentPage}
        />
        
        {/* Page Content */}
        <main className="flex-1 p-6 lg:p-8 overflow-y-auto">
          <div className="max-w-7xl mx-auto">
            <Routes>
              <Route path="/" element={<Dashboard onNavigate={handleNavigate} />} />
              <Route path="/dashboard" element={<Dashboard onNavigate={handleNavigate} />} />
              <Route path="/comparison" element={<Comparison />} />
              <Route path="/problems" element={<Problems />} />
              <Route path="/funnels" element={<Funnels />} />
            </Routes>
          </div>
        </main>
      </div>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <VersionsProvider>
        <AppContent />
      </VersionsProvider>
    </BrowserRouter>
  )
}

export default App