import { useState, useEffect } from 'react'
import SkeletonLoader from '../UI/Common/SkeletonLoader'
import EmptyState from '../UI/Common/EmptyState'
import SpotlightCard from '../UI/Common/SpotlightCard'
import api from '../../services/api'

export default function FunnelsList({ versionId, versionName, onFunnelSelect, onCreateClick }) {
  const [loading, setLoading] = useState(true)
  const [funnels, setFunnels] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!versionId) {
      setFunnels([])
      setLoading(false)
      return
    }

    const fetchFunnels = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await api.getFunnels(versionId)
        // API returns {count, results} or array
        const funnelsList = Array.isArray(data) ? data : (data.results || data.funnels || [])
        setFunnels(funnelsList)
      } catch (err) {
        console.error('Failed to fetch funnels:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchFunnels()
  }, [versionId])

  if (loading) {
    return (
      <div className="space-y-6">
        <SkeletonLoader type="card" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2].map(i => (
            <SkeletonLoader key={i} type="card" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <EmptyState
        type="funnels"
        title="Ошибка загрузки воронок"
        description={error}
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* Header with title and count */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">
          Воронки для {versionName || 'выбранной версии'}
        </h2>
        <div className="flex items-center gap-4">
          <div className="text-sm text-gray-500">
            {funnels.length > 0 ? `Всего воронок: ${funnels.length}` : 'Воронки не найдены'}
          </div>
          {onCreateClick && (
            <button
              onClick={onCreateClick}
              className="px-4 py-2 bg-accent-gold text-white font-bold rounded-xl hover:bg-accent-goldLight transition-all duration-300 shadow-lg shadow-accent-gold/20 hover:shadow-accent-gold/40"
            >
              + Создать воронку
            </button>
          )}
        </div>
      </div>

      {funnels.length === 0 ? (
        <EmptyState 
          type="funnels"
          title="Воронки не найдены"
          description={`Воронки конверсии не найдены для ${versionName || 'этой версии'}. Воронки появятся здесь после их создания.`}
          action={
            <div className="bg-gray-modal p-4 rounded-lg text-left max-w-2xl mx-auto mt-4">
              <p className="text-sm font-semibold text-gray-300 mb-2">Создать воронки с помощью команды:</p>
              <code className="block bg-gray-back text-accent-gold p-3 rounded text-sm">
                docker-compose exec web python manage.py create_funnels --version "{versionName || 'version_name'}"
              </code>
            </div>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {funnels.map((funnel, index) => (
            <SpotlightCard
              key={funnel.id}
              className="bg-gray-card border border-gray-divider rounded-2xl p-6 hover:border-accent-gold/40 hover:shadow-[0_0_15px_-3px_rgba(255,215,0,0.15)] hover:scale-[1.02] transition-all duration-500 cursor-pointer animate-slideUp"
              glowColor="rgba(255, 215, 0, 0.15)"
              onClick={() => onFunnelSelect(funnel.id)}
              style={{ animationDelay: `${index * 0.1}s`, animationFillMode: 'forwards' }}
            >
              <div className="relative z-10">
                {/* Header */}
                <div className="mb-4">
                  <h3 className="text-lg font-bold text-white mb-3">{funnel.name}</h3>
                  <div className="flex items-center gap-2 text-xs mb-4">
                    <span className="px-2 py-1 bg-gray-700 rounded text-gray-300">
                      {(() => {
                        const steps = typeof funnel.steps === 'string' 
                          ? JSON.parse(funnel.steps || '[]') 
                          : funnel.steps || []
                        const count = steps.length || funnel.steps_count || 0
                        return `глубина просмотра сайта: ${count}`
                      })()}
                    </span>
                    {funnel.is_preset ? (
                      <span className="px-2 py-1 bg-accent-gold/20 text-accent-gold rounded border border-accent-gold/30">
                        Автоматическое добавление воронки
                      </span>
                    ) : (
                      <span className="px-2 py-1 bg-accent-emerald/20 text-accent-emerald rounded border border-accent-emerald/30">
                        Созданной собственноручно
                      </span>
                    )}
                  </div>
                </div>

                {/* Metrics or Warning */}
                {funnel.has_metrics && funnel.total_entered !== undefined ? (
                  <div className="grid grid-cols-3 gap-4 p-4 bg-gray-modal/50 rounded-xl border border-gray-divider/50 mb-4">
                    <div className="text-center">
                      <p className="text-xs text-gray-500 mb-1 uppercase tracking-wider">Вошли</p>
                      <p className="text-xl font-bold text-white">{funnel.total_entered || 0}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-xs text-gray-500 mb-1 uppercase tracking-wider">Завершили</p>
                      <p className="text-xl font-bold text-white">{funnel.total_completed || 0}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-xs text-gray-500 mb-1 uppercase tracking-wider">Конверсия</p>
                      <p className={`text-xl font-bold ${
                        funnel.overall_conversion < 10 ? 'text-accent-red' :
                        funnel.overall_conversion < 20 ? 'text-accent-gold' :
                        'text-accent-emerald'
                      }`}>
                        {funnel.overall_conversion?.toFixed(1) || 0}%
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="p-4 bg-gray-modal/50 rounded-xl border border-gray-divider/50 mb-4">
                    <div className="flex items-center gap-2 text-sm text-gray-400">
                      <svg className="w-5 h-5 text-accent-gold" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      <span>Метрики еще не рассчитаны. Выполните команду <code className="text-accent-gold">calculate_funnels</code></span>
                    </div>
                  </div>
                )}

                {/* Action Button */}
                <div className="pt-4 border-t border-gray-divider">
                  <button 
                    onClick={(e) => {
                      e.stopPropagation()
                      onFunnelSelect(funnel.id)
                    }}
                    className="w-full px-4 py-2 bg-accent-gold text-white font-bold rounded-lg hover:bg-accent-goldLight transition-all duration-300 shadow-lg shadow-accent-gold/20 hover:shadow-accent-gold/40 hover:scale-[1.02] active:scale-[0.98]"
                  >
                    Открыть →
                  </button>
                </div>
              </div>
            </SpotlightCard>
          ))}
        </div>
      )}
    </div>
  )
}
