export default function Header({ onMenuToggle, currentPage }) {
  // Map page IDs to titles
  const titles = {
    dashboard: 'ОБЗОР',
    comparison: 'СРАВНЕНИЕ ВЕРСИЙ',
    problems: 'ОТСЛЕЖИВАНИЕ ПРОБЛЕМ',
    funnels: 'ВОРОНКИ КОНВЕРСИИ'
  }

  return (
    <header className="bg-gray-back border-b border-gray-divider h-16 flex items-center justify-between px-6 lg:px-8 sticky top-0 z-40">
      
      {/* Left: Mobile Toggle & Title */}
      <div className="flex items-center gap-4">
        <button 
          onClick={onMenuToggle}
          className="lg:hidden p-2 text-gray-400 hover:text-white transition-colors"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        
        <h2 className="text-white font-bold text-xl tracking-tight">
          {titles[currentPage] || 'ПАНЕЛЬ УПРАВЛЕНИЯ'}
        </h2>
      </div>

      {/* Right: Actions / Status */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-card border border-gray-divider rounded-full">
          <div className="w-2 h-2 rounded-full bg-accent-emerald animate-pulse" />
          <span className="text-xs font-medium text-gray-300">Система онлайн</span>
        </div>
        
        <button className="p-2 text-gray-400 hover:text-white transition-colors relative">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-accent-red rounded-full border-2 border-gray-back" />
        </button>
      </div>
    </header>
  )
}