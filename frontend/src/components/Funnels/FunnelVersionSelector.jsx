import { useState, useEffect } from 'react'
import SkeletonLoader from '../UI/Common/SkeletonLoader'
import EmptyState from '../UI/Common/EmptyState'
import { useVersions } from '../../contexts/VersionsContext'

export default function FunnelVersionSelector({ selectedVersionId, onVersionChange }) {
  const { versions, loading, error } = useVersions()

  useEffect(() => {
    // Auto-select first version if none selected
    if (!selectedVersionId && versions.length > 0) {
      onVersionChange(versions[0].id, versions[0].name)
    }
  }, [selectedVersionId, versions, onVersionChange])

  const handleChange = (e) => {
    const selectedId = e.target.value ? parseInt(e.target.value) : null
    const selectedVersion = versions.find(v => v.id === selectedId)
    onVersionChange(selectedId, selectedVersion?.name || null)
  }

  if (loading) {
    return (
      <div className="bg-gray-card border border-gray-divider rounded-2xl p-6">
        <div className="h-10 bg-gray-700 rounded animate-pulse" />
      </div>
    )
  }

  if (error) {
    return (
      <EmptyState
        type="funnels"
        title="Сервер бэкенда не запущен"
        description="Не удалось загрузить версии. Убедитесь, что сервер Django бэкенда запущен на http://172.29.8.236:8000."
        action={
          <div className="bg-gray-modal p-4 rounded-lg text-left max-w-2xl mx-auto mt-4">
            <p className="text-sm font-semibold text-gray-300 mb-2">Для запуска бэкенда:</p>
            <code className="block bg-gray-back text-accent-gold p-3 rounded text-sm">
              docker-compose up
            </code>
          </div>
        }
      />
    )
  }

  return (
    <div className="bg-gray-card border border-gray-divider rounded-2xl p-6 hover:border-accent-gold/40 hover:shadow-[0_0_15px_-3px_rgba(255,215,0,0.15)] transition-all duration-500">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">ВЫБЕРИТЕ ВЕРСИЮ</h3>
        {selectedVersionId && (
          <div className="text-sm text-gray-400">
            Выбрано: <span className="text-accent-gold font-semibold">
              {versions.find(v => v.id === selectedVersionId)?.name || ''}
            </span>
          </div>
        )}
      </div>
      
      <div className="flex flex-wrap gap-3">
        {versions.map(version => {
          const isSelected = selectedVersionId === version.id
          return (
            <button
              key={version.id}
              onClick={() => onVersionChange(version.id, version.name)}
              className={`
                relative px-6 py-3 rounded-xl border transition-all duration-300
                ${isSelected 
                  ? 'bg-gray-modal border-accent-gold text-white shadow-[0_0_15px_rgba(255,215,0,0.3)] scale-105' 
                  : 'bg-gray-modal/50 border-gray-divider text-gray-400 hover:border-accent-gold/50 hover:text-white hover:scale-105'
                }
              `}
            >
              <span className="font-semibold text-sm">{version.name}</span>
              {isSelected && (
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-accent-gold rounded-full shadow-[0_0_8px_rgba(255,215,0,0.6)]" />
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
