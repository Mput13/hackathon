import { useState } from 'react'

export default function Sidebar({ currentPage, setCurrentPage, isOpen, onClose }) {
  const menuItems = [
    { 
      id: 'dashboard', 
      label: 'ПАНЕЛЬ УПРАВЛЕНИЯ', 
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
        </svg>
      )
    },
    { 
      id: 'comparison', 
      label: 'СРАВНЕНИЕ', 
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
        </svg>
      )
    },
    { 
      id: 'funnels', 
      label: 'ВОРОНКИ', 
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      )
    },
    { 
      id: 'problems', 
      label: 'ПРОБЛЕМЫ', 
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      )
    }
  ]

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar Container */}
      <div className={`
        fixed lg:static inset-y-0 left-0 z-50
        w-72 bg-gray-modal border-r border-gray-divider
        transform transition-transform duration-300 ease-in-out
        flex flex-col
        ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        
        {/* Logo Section */}
        <div className="p-6 border-b border-gray-divider">
          <div className="flex items-center gap-4">
            {/* Red Circle with PNG */}
            <div className="relative flex-shrink-0 w-12 h-12 bg-accent-red rounded-full flex items-center justify-center shadow-lg shadow-accent-red/20">
               <img 
                 src="/src/assets/images/oprichlogo.png" 
                 alt="Logo" 
                 className="w-8 h-8 object-contain"
               />
            </div>
            
            {/* Text */}
            <div className="flex flex-col">
              <h1 className="text-white font-bold text-lg leading-tight">
                Опричнина
              </h1>
              <span className="text-accent-red text-xs font-semibold tracking-wider uppercase">
                Dashboard
              </span>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2">
          {menuItems.map(item => (
            <button
              key={item.id}
              onClick={() => {
                setCurrentPage(item.id)
                onClose && onClose()
              }}
              className={`
                w-full flex items-center space-x-4 px-4 py-3 rounded-xl transition-all duration-200 group
                ${currentPage === item.id 
                  ? 'bg-gray-card text-white border border-gray-divider shadow-sm' 
                  : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
                }
              `}
            >
              <span className="text-xl">{item.icon}</span>
              <span className="font-medium tracking-wide text-sm">{item.label}</span>
              
              {/* Active Indicator */}
              {currentPage === item.id && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-accent-red shadow-[0_0_8px_rgba(220,38,38,0.5)]" />
              )}
            </button>
          ))}
        </nav>

        {/* Footer / User Info */}
        <div className="p-4 border-t border-gray-divider bg-gray-card/50">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center text-xs text-white font-bold">
              AD
            </div>
            <div className="overflow-hidden">
              <p className="text-sm text-white font-medium truncate">Администратор</p>
              <p className="text-xs text-gray-500 truncate">admin@oprichnina.ai</p>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}