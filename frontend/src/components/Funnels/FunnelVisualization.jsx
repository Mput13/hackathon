import { useEffect, useRef } from 'react'
import SpotlightCard from '../UI/Common/SpotlightCard'

export default function FunnelVisualization({ funnel, metrics }) {
  const stepMetrics = metrics.step_metrics || []
  const progressBarsRef = useRef([])

  useEffect(() => {
    // Animate progress bars on mount
    progressBarsRef.current.forEach((bar, index) => {
      if (bar) {
        setTimeout(() => {
          bar.style.width = bar.dataset.width || '0%'
        }, index * 100)
      }
    })
  }, [stepMetrics])

  return (
    <div className="space-y-6">
      {/* Overall Metrics - KPI Cards with Spotlight */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <SpotlightCard 
          className="bg-gray-card border border-gray-divider rounded-2xl p-6 hover:scale-[1.02] transition-all duration-300 animate-slideUp"
          glowColor="rgba(220, 38, 38, 0.15)"
          style={{ animationDelay: '0.1s' }}
        >
          <div className="relative z-10">
            <p className="text-sm text-gray-500 mb-2 uppercase tracking-wider">Входов в воронку</p>
            <p className="text-3xl font-bold text-white transition-all duration-300">{metrics.total_entered || 0}</p>
          </div>
        </SpotlightCard>

        <SpotlightCard 
          className="bg-gray-card border border-gray-divider rounded-2xl p-6 hover:scale-[1.02] transition-all duration-300 animate-slideUp"
          glowColor="rgba(16, 185, 129, 0.15)"
          style={{ animationDelay: '0.2s' }}
        >
          <div className="relative z-10">
            <p className="text-sm text-gray-500 mb-2 uppercase tracking-wider">Завершили воронку</p>
            <p className="text-3xl font-bold text-white transition-all duration-300">{metrics.total_completed || 0}</p>
          </div>
        </SpotlightCard>

        <SpotlightCard 
          className="bg-gray-card border border-gray-divider rounded-2xl p-6 hover:scale-[1.02] transition-all duration-300 animate-slideUp"
          glowColor="rgba(255, 215, 0, 0.15)"
          style={{ animationDelay: '0.3s' }}
        >
          <div className="relative z-10">
            <p className="text-sm text-gray-500 mb-2 uppercase tracking-wider">Общая конверсия</p>
            <p className={`text-3xl font-bold transition-all duration-300 ${
              metrics.overall_conversion < 10 ? 'text-accent-red' :
              metrics.overall_conversion < 20 ? 'text-accent-gold' :
              'text-accent-emerald'
            }`}>
              {metrics.overall_conversion?.toFixed(1) || 0}%
            </p>
          </div>
        </SpotlightCard>
      </div>

      {/* Funnel Steps Visualization - Enhanced with animations */}
      <div className="bg-gray-card border border-gray-divider rounded-2xl p-6 hover:border-gray-divider/80 transition-all duration-500">
        <h3 className="text-lg font-bold text-white mb-6">ВИЗУАЛИЗАЦИЯ КОНВЕРСИИ</h3>
        
        <div className="space-y-8">
          {stepMetrics.map((stepMetric, index) => (
            <div 
              key={index} 
              className="relative animate-slideUp opacity-0"
              style={{ 
                animationDelay: `${0.4 + index * 0.1}s`,
                animationFillMode: 'forwards'
              }}
            >
              {/* Step Info */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-4 group">
                  <div className="w-10 h-10 bg-gradient-to-br from-accent-gold to-accent-goldLight text-white rounded-full flex items-center justify-center font-bold text-base shadow-lg shadow-accent-gold/20 transition-all duration-300 group-hover:scale-110 group-hover:shadow-accent-gold/40">
                    {stepMetric.step_number || index + 1}
                  </div>
                  <div>
                    <p className="font-bold text-white text-base transition-colors duration-300">{stepMetric.step_name || `Шаг ${stepMetric.step_number || index + 1}`}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      <span 
                        className="font-semibold text-white transition-all duration-300"
                        style={{
                          textShadow: '0 0 8px rgba(255, 255, 255, 0.3), 0 0 15px rgba(255, 255, 255, 0.2)'
                        }}
                      >
                        {stepMetric.users_reached || 0}
                      </span> пользователей достигло
                    </p>
                  </div>
                </div>
                {stepMetric.step_number > 1 && stepMetric.conversion_from_prev !== undefined && (
                  <div className="text-right">
                    <p 
                      className={`text-xl font-bold font-mono transition-all duration-300 ${
                        stepMetric.conversion_from_prev < 50 ? 'text-accent-red' :
                        stepMetric.conversion_from_prev < 70 ? 'text-accent-gold' :
                        'text-accent-emerald'
                      }`}
                      style={{
                        textShadow: stepMetric.conversion_from_prev < 50 
                          ? '0 0 10px rgba(220, 38, 38, 0.5), 0 0 20px rgba(220, 38, 38, 0.3)'
                          : stepMetric.conversion_from_prev < 70
                          ? '0 0 10px rgba(255, 215, 0, 0.5), 0 0 20px rgba(255, 215, 0, 0.3)'
                          : '0 0 10px rgba(16, 185, 129, 0.5), 0 0 20px rgba(16, 185, 129, 0.3)'
                      }}
                    >
                      {stepMetric.conversion_from_prev?.toFixed(2) || 0}%
                    </p>
                    <p className="text-xs text-gray-500 uppercase tracking-wide font-bold">конверсия</p>
                  </div>
                )}
              </div>

              {/* Progress Bar with gradient and glow */}
              {stepMetric.step_number > 1 && stepMetric.conversion_from_prev !== undefined && (
                <div className="ml-14 mb-4">
                  <div className="h-2.5 bg-gray-700 rounded-full overflow-hidden relative">
                    <div 
                      ref={el => {
                        if (el) {
                          progressBarsRef.current[index] = el
                          // Set initial width to 0, then animate
                          el.style.width = '0%'
                          setTimeout(() => {
                            el.style.width = `${stepMetric.conversion_from_prev || 0}%`
                          }, 100 + index * 150)
                        }
                      }}
                      data-width={`${stepMetric.conversion_from_prev || 0}%`}
                      className={`h-full rounded-full transition-all duration-1000 ease-out relative overflow-hidden ${
                        stepMetric.conversion_from_prev < 50 
                          ? 'bg-gradient-to-r from-accent-red via-red-500 to-red-400' 
                          : stepMetric.conversion_from_prev < 70
                          ? 'bg-gradient-to-r from-accent-gold via-yellow-400 to-yellow-300'
                          : 'bg-gradient-to-r from-accent-emerald via-emerald-400 to-emerald-300'
                      }`}
                      style={{ 
                        width: '0%',
                        boxShadow: stepMetric.conversion_from_prev < 50
                          ? '0 0 10px rgba(220, 38, 38, 0.4), inset 0 0 10px rgba(220, 38, 38, 0.2)'
                          : stepMetric.conversion_from_prev < 70
                          ? '0 0 10px rgba(255, 215, 0, 0.4), inset 0 0 10px rgba(255, 215, 0, 0.2)'
                          : '0 0 10px rgba(16, 185, 129, 0.4), inset 0 0 10px rgba(16, 185, 129, 0.2)'
                      }}
                    >
                      {/* Shimmer effect */}
                      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer opacity-0 hover:opacity-100 transition-opacity duration-500" />
                    </div>
                  </div>
                  {stepMetric.drop_off > 0 && (
                    <div className="flex items-center justify-between mt-2 animate-fadeIn" style={{ animationDelay: `${0.5 + index * 0.1}s` }}>
                      <p className="text-xs text-gray-500 transition-colors duration-300">
                        Потеряно: <span className="font-semibold text-accent-red">{stepMetric.drop_off} пользователей</span>
                      </p>
                      <p className="text-xs text-gray-500 font-mono">
                        ({stepMetric.drop_off_percentage?.toFixed(1) || 0}%)
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Divider Line with animation */}
              {index < stepMetrics.length - 1 && (
                <div className="ml-14 mt-4 mb-4">
                  <div className="h-px bg-gradient-to-r from-transparent via-gray-divider to-transparent transition-all duration-500"></div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* AI Analysis - With Spotlight */}
      {metrics.ai_analysis && (
        <SpotlightCard 
          className="bg-gray-card/80 border border-accent-gold/30 rounded-2xl p-6 animate-slideUp hover:scale-[1.01] transition-all duration-300" 
          glowColor="rgba(255, 215, 0, 0.15)"
          style={{ animationDelay: `${0.5 + stepMetrics.length * 0.1}s` }}
        >
          <div className="relative z-10 flex items-start gap-4">
            <div className="p-3 bg-accent-gold/20 rounded-full text-accent-gold transition-all duration-300 hover:bg-accent-gold/30 hover:scale-110">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div className="flex-1">
              <h4 className="text-accent-gold font-bold text-lg mb-2 transition-colors duration-300">AI-анализ и рекомендации</h4>
              <div className="text-sm text-gray-300 leading-relaxed whitespace-pre-line transition-colors duration-300">
                {typeof metrics.ai_analysis === 'string' 
                  ? metrics.ai_analysis.split('\n')
                      .filter(line => {
                        // Убираем строки про совместимость с версиями 2022/2024
                        const lowerLine = line.toLowerCase()
                        return !lowerLine.includes('2022') && 
                               !lowerLine.includes('2024') && 
                               !lowerLine.includes('bachelor') && 
                               !lowerLine.includes('/base/') && 
                               !lowerLine.includes('совместимости') &&
                               !lowerLine.includes('compatibility')
                      })
                      .map((line, i) => (
                        <div key={i}>
                          {line.startsWith('Анализ:') || line.startsWith('Рекомендация:') ? (
                            <><strong className="text-white">{line.split(':')[0]}:</strong> {line.split(':').slice(1).join(':')}</>
                          ) : (
                            line
                          )}
                        </div>
                      ))
                  : metrics.ai_analysis
                }
              </div>
            </div>
          </div>
        </SpotlightCard>
      )}
    </div>
  )
}
