import SkeletonLoader from '../UI/Common/SkeletonLoader'
import EmptyState from '../UI/Common/EmptyState'

export default function Allnsights({ onViewAll, onIssueClick, recentIssues = [], loading = false }) {

  if (loading) {
    return (
      <div className="mb-8">
        <SkeletonLoader type="card" />
      </div>
    )
  }

  if (!recentIssues || recentIssues.length === 0) {
    return (
      <div className="mb-8">
        <EmptyState 
          type="insights"
          title="No Recent Issues"
          description="No recent issues found for this version."
        />
      </div>
    )
  }

  return (
    <div className="bg-gray-card border border-gray-divider rounded-2xl p-6 mb-8 hover:border-gray-divider/80 transition-all duration-500">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-bold text-white">ПОСЛЕДНИЕ ИНСАЙТЫ</h2>
          <p className="text-xs text-gray-500 mt-1">Latest UX issues detected by AI</p>
        </div>
        {onViewAll && (
          <button
            onClick={onViewAll}
            className="text-accent-gold hover:text-accent-goldLight transition-colors text-sm font-semibold flex items-center gap-2 hover:gap-3"
          >
            <span>Показать все</span>
            <svg className="w-4 h-4 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        )}
      </div>

      <div className="space-y-4">
        {recentIssues.slice(0, 5).map((issue) => {
          // Parse AI data (hypothesis and fix)
          const parseAIData = (text) => {
            if (!text) return null
            try {
              const parsed = typeof text === 'string' ? JSON.parse(text) : text
              if (parsed && typeof parsed === 'object') {
                if (parsed.hypothesis && parsed.fix) {
                  return { hypothesis: parsed.hypothesis, fix: parsed.fix }
                }
                if (parsed.hypothesis || parsed.fix) {
                  return { hypothesis: parsed.hypothesis || null, fix: parsed.fix || null }
                }
              }
            } catch (e) {
              // Not JSON, will treat as plain text below
            }
            return null
          }
          
          // Try to parse from ai_solution first, then ai_hypothesis
          const parsedSolution = parseAIData(issue.ai_solution)
          const parsedHypothesis = parseAIData(issue.ai_hypothesis)
          
          // Use parsed data if available, otherwise use raw fields
          const hypothesis = parsedHypothesis ? parsedHypothesis.hypothesis : 
                           parsedSolution ? parsedSolution.hypothesis : 
                           issue.ai_hypothesis
          
          const fix = parsedSolution ? parsedSolution.fix : 
                     parsedHypothesis ? parsedHypothesis.fix : 
                     issue.ai_solution

          return (
            <div
              key={issue.id}
              className="w-full text-left p-5 rounded-xl border border-gray-divider bg-gray-modal"
            >
              <div className="space-y-4">
                {/* Название проблемы - увеличенный шрифт */}
                {/* Используем description, если readable_location выглядит как хеш или идентификатор */}
                {(() => {
                  const readableLoc = issue.readable_location || issue.location_url
                  const isHashLike = readableLoc && readableLoc.length > 20 && 
                                   /^[A-Za-z0-9]+$/.test(readableLoc.replace(/\s/g, '')) &&
                                   /[A-Z]/.test(readableLoc) && /[a-z]/.test(readableLoc) && /[0-9]/.test(readableLoc)
                  
                  if (isHashLike && issue.description) {
                    // Если location выглядит как хеш, используем описание
                    return <h3 className="text-lg font-bold text-white">{issue.description}</h3>
                  }
                  
                  return <h3 className="text-lg font-bold text-white">{readableLoc || issue.description || 'Неизвестная страница'}</h3>
                })()}
                
                {/* Метаданные проблемы */}
                <div className="flex flex-wrap items-center gap-4 text-sm text-gray-400">
                  {issue.version && (
                    <span className="flex items-center gap-1">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                      </svg>
                      Версия: {issue.version.name || issue.detected_version_name || 'Неизвестно'}
                    </span>
                  )}
                  {issue.affected_sessions !== undefined && issue.affected_sessions !== null && (
                    <span className="flex items-center gap-1">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                      </svg>
                      {issue.affected_sessions} сессий
                    </span>
                  )}
                  {issue.impact_score !== undefined && issue.impact_score !== null && (
                    <span className="flex items-center gap-1">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                      </svg>
                      Оценка влияния: {issue.impact_score.toFixed(1)}/10
                    </span>
                  )}
                  {issue.severity && (
                    <span className={`px-2 py-1 text-xs rounded border ${
                      issue.severity === 'CRITICAL' ? 'bg-accent-red/20 text-accent-red border-accent-red/30' :
                      issue.severity === 'HIGH' ? 'bg-accent-red/15 text-accent-redLight border-accent-red/25' :
                      issue.severity === 'MEDIUM' ? 'bg-accent-gold/20 text-accent-gold border-accent-gold/30' :
                      'bg-gray-modal text-gray-300 border-gray-divider'
                    }`}>
                      {issue.severity}
                    </span>
                  )}
                  {issue.priority && (
                    <span className="px-2 py-1 bg-gray-modal text-gray-300 text-xs rounded border border-gray-divider">
                      {issue.priority === 'P0' || issue.priority === '0' ? 'P0 - Критическая ошибка' : 
                       issue.priority === 'P1' || issue.priority === '1' ? 'P1 - Предупреждение' : 
                       issue.priority === 'P2' || issue.priority === '2' ? 'P2 - Совет по исправлению' : 
                       issue.priority}
                    </span>
                  )}
                </div>
                
                {/* Красный блок - гипотеза (hypothesis) */}
                {hypothesis && (
                  <div className="p-4 rounded-lg border border-gray-divider bg-gray-modal hover:border-accent-red/50 hover:shadow-[0_0_15px_rgba(220,38,38,0.3)] transition-all duration-300">
                    <h4 className="text-xs font-bold text-accent-red uppercase tracking-wider mb-2">Гипотеза</h4>
                    <p className="text-sm text-white leading-relaxed">{hypothesis}</p>
                  </div>
                )}
                
                {/* Зеленый блок - исправление (fix) */}
                {fix && (
                  <div className="p-4 rounded-lg border border-gray-divider bg-gray-modal hover:border-accent-emerald/50 hover:shadow-[0_0_15px_rgba(16,185,129,0.3)] transition-all duration-300">
                    <h4 className="text-xs font-bold text-accent-emerald uppercase tracking-wider mb-2">Исправление</h4>
                    <p className="text-sm text-white leading-relaxed">{fix}</p>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
