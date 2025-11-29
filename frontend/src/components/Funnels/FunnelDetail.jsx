import { useState, useEffect } from 'react'
import SkeletonLoader from '../UI/Common/SkeletonLoader'
import EmptyState from '../UI/Common/EmptyState'
import SpotlightCard from '../UI/Common/SpotlightCard'
import FunnelVisualization from './FunnelVisualization'
import api from '../../services/api'

export default function FunnelDetail({ funnelId, onBack }) {
  const [loading, setLoading] = useState(true)
  const [funnel, setFunnel] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchFunnel = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await api.getFunnelDetail(funnelId)
        console.log('[FunnelDetail] Received data:', data)
        console.log('[FunnelDetail] Metrics:', data.metrics)
        setFunnel(data)
      } catch (err) {
        console.error('Failed to fetch funnel:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    if (funnelId) {
      fetchFunnel()
    }
  }, [funnelId])

  if (loading) {
    return (
      <div className="space-y-6">
        <SkeletonLoader type="card" />
        <SkeletonLoader type="chart" />
      </div>
    )
  }

  if (error || !funnel) {
    return (
      <EmptyState 
        type="funnels"
          title="Воронка не найдена"
          description={error || "Запрошенная воронка не найдена."}
        action={
          <button 
            onClick={onBack}
            className="px-6 py-2 bg-accent-red text-white text-sm font-bold rounded hover:bg-accent-redLight transition-colors"
          >
            Back to List
          </button>
        }
      />
    )
  }

  // Parse steps if they come as JSON string
  const steps = typeof funnel.steps === 'string' 
    ? JSON.parse(funnel.steps || '[]') 
    : funnel.steps || []

  // Check if metrics exist - metrics should have total_entered or step_metrics
  const hasMetrics = funnel.metrics && (
    (funnel.metrics.total_entered !== undefined && funnel.metrics.total_entered !== null) || 
    (funnel.metrics.step_metrics && funnel.metrics.step_metrics.length > 0) ||
    (funnel.metrics.total_completed !== undefined && funnel.metrics.total_completed !== null)
  )

  return (
    <div className="space-y-6">
      {/* Back Link */}
      <button
        onClick={onBack}
        className="text-gray-400 hover:text-white transition-all duration-300 flex items-center gap-2 mb-4 group hover:gap-3"
      >
        <svg className="w-5 h-5 transition-transform duration-300 group-hover:-translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        <span>Вернуться к списку воронок</span>
      </button>

      {/* Funnel Info */}
      <SpotlightCard 
        className="bg-gray-card border border-gray-divider rounded-2xl p-6 animate-slideUp"
        glowColor="rgba(255, 215, 0, 0.15)"
      >
        <div className="relative z-10">
          <div className="flex justify-between items-start mb-4">
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-white mb-2">{funnel.name}</h1>
              {funnel.description && (() => {
                // Убираем строки про совместимость с версиями 2022/2024
                const filteredDescription = funnel.description
                  .split('\n')
                  .filter(line => {
                    const lowerLine = line.toLowerCase()
                    return !lowerLine.includes('2022') && 
                           !lowerLine.includes('2024') && 
                           !lowerLine.includes('bachelor') && 
                           !lowerLine.includes('/base/') && 
                           !lowerLine.includes('совместимости') &&
                           !lowerLine.includes('compatibility')
                  })
                  .join('\n')
                return filteredDescription.trim() ? (
                  <p className="text-gray-400 mb-4">{filteredDescription}</p>
                ) : null
              })()}
              <div className="flex items-center gap-4 text-sm text-gray-500">
                {funnel.version && (
                  <>
                    <span>Версия: <strong className="text-white">{funnel.version.name || funnel.version}</strong></span>
                    <span>•</span>
                  </>
                )}
                <span>глубина просмотра сайта: {steps.length}</span>
                {funnel.is_preset ? (
                  <span className="px-2 py-1 bg-accent-gold/20 text-accent-gold rounded border border-accent-gold/30 text-xs">
                    Автоматическое добавление воронки
                  </span>
                ) : (
                  <span className="px-2 py-1 bg-accent-emerald/20 text-accent-emerald rounded border border-accent-emerald/30 text-xs">
                    Созданной собственноручно
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Steps List */}
          <div className="mt-6">
            <h3 className="text-lg font-bold text-white mb-4">Глубина просмотра сайта</h3>
            <div className="space-y-3">
              {steps.map((step, index) => (
                <div 
                  key={index} 
                  className="flex items-center gap-3 p-3 bg-gray-modal/50 rounded-lg border border-gray-divider/50 hover:bg-gray-modal/70 hover:border-gray-divider transition-all duration-300 animate-slideUp"
                  style={{ animationDelay: `${0.2 + index * 0.05}s`, animationFillMode: 'forwards' }}
                >
                  <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-accent-gold to-accent-goldLight text-white rounded-full flex items-center justify-center font-bold shadow-lg shadow-accent-gold/20 transition-all duration-300 hover:scale-110 hover:shadow-accent-gold/40">
                    {index + 1}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-white">{step.name || step.step_name || `Шаг ${index + 1}`}</p>
                    <p className="text-xs text-gray-500">
                      {step.type === 'goal' ? (
                        <>Goal: <code className="text-accent-gold">{step.code}</code></>
                      ) : (
                        <>URL: <code className="text-accent-gold">{step.url || step.norm_url || 'N/A'}</code></>
                      )}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </SpotlightCard>

      {/* Metrics */}
      {hasMetrics ? (
        <FunnelVisualization funnel={funnel} metrics={funnel.metrics} />
      ) : (
        <EmptyState 
          type="funnels"
          title="Метрики не рассчитаны"
          description={funnel.metrics?.message || "Метрики воронки еще не рассчитаны. Пожалуйста, выполните команду calculate_funnels."}
          action={
            <div className="bg-gray-modal p-4 rounded-lg text-left max-w-2xl mx-auto mt-4">
              <p className="text-sm font-semibold text-gray-300 mb-2">Рассчитать метрики с помощью команды:</p>
              <code className="block bg-gray-back text-accent-gold p-3 rounded text-sm">
                docker-compose exec web python manage.py calculate_funnels --version "{funnel.version?.name || 'version_name'}" --funnel-id {funnel.id}
              </code>
            </div>
          }
        />
      )}
    </div>
  )
}
