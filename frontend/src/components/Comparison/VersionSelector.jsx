import { useState, useEffect, useRef } from 'react'
import { useVersions } from '../../contexts/VersionsContext'

export default function VersionSelector({ onCompare }) {
  const { versions, loading } = useVersions()
  const [v1, setV1] = useState(null)
  const [v2, setV2] = useState(null)
  const hasInitialized = useRef(false)

  // Auto-select first and last version when versions are loaded (only once)
  useEffect(() => {
    if (versions.length > 0 && !hasInitialized.current) {
      setV1(versions[0].id)
      setV2(versions[versions.length - 1].id)
      hasInitialized.current = true
    }
  }, [versions])

  const handleCompare = () => {
    if (v1 && v2 && onCompare) {
      onCompare(v1, v2)
    }
  }

  if (loading) {
    return (
      <div className="bg-gray-card border border-gray-divider rounded-2xl p-6 mb-6">
        <div className="h-10 bg-gray-700 rounded animate-pulse" />
      </div>
    )
  }

  return (
    <div className="bg-gray-card border border-gray-divider rounded-2xl p-6 mb-6 hover:border-accent-red/40 hover:shadow-[0_0_15px_-3px_rgba(220,38,38,0.15)] transition-all duration-500">
      <h3 className="text-lg font-semibold mb-4 text-white">СРАВНЕНИЕ ВЕРСИЙ</h3>
      
      <div className="flex flex-col md:flex-row gap-6">
        {/* Base Version */}
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-500 mb-2">
            Базовая версия
          </label>
          <div className="relative">
            <select 
              value={v1 || ''}
              onChange={(e) => setV1(e.target.value ? parseInt(e.target.value) : null)}
              className="w-full bg-gray-modal border border-gray-divider rounded-xl py-3 px-4 text-white appearance-none focus:outline-none focus:border-accent-red transition-colors"
            >
              <option value="">-- Выберите версию --</option>
              {versions.map(version => (
                <option key={version.id} value={version.id}>{version.name}</option>
              ))}
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-500">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>
        </div>

        {/* Compare Icon */}
        <div className="flex items-center justify-center">
          <div className="w-10 h-10 bg-gray-modal border border-accent-red rounded-full flex items-center justify-center">
            <span className="text-accent-red font-bold">VS</span>
          </div>
        </div>

        {/* Compare Version */}
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-500 mb-2">
            Версия для сравнения
          </label>
          <div className="relative">
            <select 
              value={v2 || ''}
              onChange={(e) => setV2(e.target.value ? parseInt(e.target.value) : null)}
              className="w-full bg-gray-modal border border-gray-divider rounded-xl py-3 px-4 text-white appearance-none focus:outline-none focus:border-accent-red transition-colors"
            >
              <option value="">-- Выберите версию --</option>
              {versions.map(version => (
                <option key={version.id} value={version.id}>{version.name}</option>
              ))}
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-500">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex justify-end gap-3 mt-6">
        <button 
          onClick={() => {
            setV1(versions[0]?.id || null)
            setV2(versions[versions.length - 1]?.id || null)
          }}
          className="px-6 py-2 border border-gray-divider text-gray-400 rounded-xl hover:border-gray-600 hover:bg-gray-modal transition-all duration-300"
        >
          Сбросить
        </button>
        <button 
          onClick={handleCompare}
          disabled={!v1 || !v2}
          className="px-6 py-2 bg-accent-red text-white rounded-xl hover:bg-accent-redLight transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Сравнить версии
        </button>
      </div>
    </div>
  )
}
