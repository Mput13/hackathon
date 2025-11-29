import { useState } from 'react'
import SpotlightCard from '../UI/Common/SpotlightCard'
import SkeletonLoader from '../UI/Common/SkeletonLoader'
import EmptyState from '../UI/Common/EmptyState'

export default function ProblemsTable({ issues = [], loading = false, isEmpty = false, error = null }) {
  const [expandedRow, setExpandedRow] = useState(null)

  // Issue types display mapping
  const ISSUE_TYPES = {
    'RAGE_CLICK': 'Rage Clicks',
    'DEAD_CLICK': 'Dead Clicks',
    'LOOPING': 'Navigation Loop',
    'FORM_ABANDON': 'Form Abandonment',
    'HIGH_BOUNCE': 'High Bounce Rate',
    'WANDERING': 'Wandering Users',
    'NAVIGATION_BACK': 'Frequent Back Button Usage',
    'FORM_FIELD_ERRORS': 'Form Input Errors',
    'FUNNEL_DROPOFF': 'Funnel Drop-off Point',
    'SCAN_AND_DROP': 'Scan And Drop',
    'SEARCH_FAIL': 'Search Fail'
  }

  const getIssueTypeDisplay = (issueType) => {
    return ISSUE_TYPES[issueType] || issueType
  }

  const getSeverityBadge = (severity) => {
    const styles = {
      CRITICAL: 'bg-accent-red/20 text-accent-red border-accent-red/30',
      WARNING: 'bg-accent-red/20 text-accent-red border-accent-red/30', // WARNING теперь красный
      INFO: 'bg-gray-modal/50 text-gray-300 border-gray-divider'
    }
    return styles[severity] || styles.INFO
  }

  const getSeverityGlow = (severity) => {
    if (severity === 'CRITICAL' || severity === 'WARNING') {
      return 'hover:border-accent-red/50 hover:shadow-[0_0_15px_-3px_rgba(220,38,38,0.2)]'
    }
    return 'hover:border-gray-divider'
  }

  const getSeveritySpotlightColor = (severity) => {
    if (severity === 'CRITICAL' || severity === 'WARNING') {
      return 'rgba(220, 38, 38, 0.15)'
    }
    return 'rgba(255, 255, 255, 0.1)'
  }

  const getTrendBadge = (trend) => {
    const styles = {
      'new': 'bg-accent-emerald/20 text-accent-emerald border-accent-emerald/30', // Новые проблемы - зеленые
      'worse': 'bg-accent-red/20 text-accent-red border-accent-red/30',
      'improved': 'bg-accent-emerald/20 text-accent-emerald border-accent-emerald/30',
      'stable': 'bg-gray-600/20 text-gray-400 border-gray-600/30'
    }
    return styles[trend] || styles.stable
  }

  const getPriorityBadge = (priority) => {
    if (!priority) return 'bg-gray-700/50 text-gray-300 border-gray-600'
    const priorityUpper = priority.toUpperCase()
    // P0 - критическая ошибка (красный), P1 - предупреждение (желтый), P2 - совет (зеленый)
    if (priorityUpper === 'P0' || priority === '0') {
      return 'bg-accent-red/20 text-accent-red border-accent-red/30'
    } else if (priorityUpper === 'P1' || priority === '1') {
      return 'bg-yellow-500/20 text-yellow-500 border-yellow-500/30'
    } else if (priorityUpper === 'P2' || priority === '2') {
      return 'bg-accent-emerald/20 text-accent-emerald border-accent-emerald/30'
    }
    return 'bg-gray-700/50 text-gray-300 border-gray-600'
  }

  // Функция для получения glow эффекта при наведении на основе priority
  const getPriorityGlowHover = (priority) => {
    if (!priority) return ''
    const priorityUpper = priority.toUpperCase()
    if (priorityUpper === 'P0' || priority === '0') {
      return 'hover:shadow-[0_0_25px_rgba(220,38,38,0.4)]'
    } else if (priorityUpper === 'P1' || priority === '1') {
      return 'hover:shadow-[0_0_25px_rgba(234,179,8,0.4)]'
    } else if (priorityUpper === 'P2' || priority === '2') {
      return 'hover:shadow-[0_0_25px_rgba(16,185,129,0.4)]'
    }
    return ''
  }

  // Функция для получения severity на основе priority
  const getSeverityFromPriority = (priority) => {
    if (!priority) return null
    const priorityUpper = priority.toUpperCase()
    if (priorityUpper === 'P0' || priority === '0') {
      return 'CRITICAL'
    } else if (priorityUpper === 'P1' || priority === '1') {
      return 'WARNING'
    } else if (priorityUpper === 'P2' || priority === '2') {
      return 'INFO'
    }
    return null
  }

  if (loading) {
    return (
      <div className="bg-gray-card border border-gray-divider rounded-2xl p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-bold text-white">ОБНАРУЖЕННЫЕ UX ПРОБЛЕМЫ</h3>
        </div>
        <SkeletonLoader type="table" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-gray-card border border-gray-divider rounded-2xl p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-bold text-white">ОБНАРУЖЕННЫЕ UX ПРОБЛЕМЫ</h3>
        </div>
        <EmptyState 
          type="problems"
          title="Ошибка загрузки проблем"
          description={error}
        />
      </div>
    )
  }

  if (isEmpty) {
    return (
      <div className="bg-gray-card border border-gray-divider rounded-2xl p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-bold text-white">ОБНАРУЖЕННЫЕ UX ПРОБЛЕМЫ</h3>
        </div>
        <EmptyState 
          type="problems"
          title="Проблемы не обнаружены"
          description="Отличные новости! В данный момент не обнаружено проблем с UX. Система автоматически уведомит вас при обнаружении новых проблем."
        />
      </div>
    )
  }

  return (
    <div className="bg-gray-card border border-gray-divider rounded-2xl p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-bold text-white">ОБНАРУЖЕННЫЕ UX ПРОБЛЕМЫ</h3>
        <div className="text-xs text-gray-500">
          Сортировка по влиянию на бизнес
        </div>
      </div>

      <div className="space-y-4">
        {issues.map(issue => {
          // Определяем severity на основе priority, если severity не указан
          const effectiveSeverity = issue.severity || getSeverityFromPriority(issue.priority) || 'INFO'
          const isCriticalOrWarning = effectiveSeverity === 'CRITICAL' || effectiveSeverity === 'WARNING'
          
          return (
          <div 
            key={issue.id} 
            className={`border rounded-xl transition-all duration-300 overflow-hidden ${
              expandedRow === issue.id 
                ? `${isCriticalOrWarning ? 'border-accent-red/50 bg-gray-modal shadow-lg shadow-accent-red/5' : 'border-gray-divider/50 bg-gray-modal shadow-lg'}` 
                : `border-gray-divider bg-gray-modal/50 cursor-pointer hover:scale-[1.02] ${issue.priority ? getPriorityGlowHover(issue.priority) : getSeverityGlow(effectiveSeverity)}`
            }`}
            onClick={() => setExpandedRow(expandedRow === issue.id ? null : issue.id)}
          >
            {/* Summary Row */}
            <div className="p-4 flex items-center justify-between gap-4">
              <div className="flex items-center gap-4 flex-1">
                  <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="font-bold text-white text-lg">{getIssueTypeDisplay(issue.issue_type)}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getSeverityBadge(effectiveSeverity)}`}>
                      {effectiveSeverity}
                    </span>
                    {issue.trend_label && (
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getTrendBadge(issue.trend)}`}>
                        {issue.trend_label}
                      </span>
                    )}
                    {issue.priority && (
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getPriorityBadge(issue.priority)}`} title="Уровень проблемы">
                        {issue.priority === 'P0' ? 'P0 - Критическая ошибка' : 
                         issue.priority === 'P1' ? 'P1 - Предупреждение' : 
                         issue.priority === 'P2' ? 'P2 - Совет по исправлению' : 
                         `Уровень: ${issue.priority}`}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-400 mb-1">{issue.description}</p>
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span className="text-accent-gold">{issue.readable_location || issue.location_url}</span>
                    {issue.version && (
                      <span className="text-gray-600">• Версия: {issue.version.name}</span>
                    )}
                  </div>
                </div>
              </div>

              <div className="text-right min-w-[100px]">
                <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Оценка влияния</div>
                <div className="flex items-center justify-end gap-2">
                  <span className="text-xl font-bold text-white">{issue.impact_score?.toFixed(1) || '0'}</span>
                  <span className="text-gray-600">/ 10</span>
                </div>
                {issue.affected_sessions !== undefined && (
                  <div className="text-xs text-gray-500 mt-1">
                    {issue.affected_sessions} сессий
                  </div>
                )}
              </div>
            </div>

            {/* Expanded Details (AI Insights Flow) */}
            {expandedRow === issue.id && (
              <div className="bg-black/30 border-t border-gray-divider p-6 animate-fadeIn cursor-auto" onClick={e => e.stopPropagation()}>
                
                {/* Metadata Tags */}
                {(issue.recommended_specialists && issue.recommended_specialists.length > 0) && (
                  <div className="mb-4">
                    <h4 className="text-gray-500 text-[10px] uppercase font-bold tracking-wider mb-2">Рекомендуемые специалисты</h4>
                    <div className="flex flex-wrap gap-2">
                      {issue.recommended_specialists.map((specialist, idx) => (
                        <span key={idx} className="px-2 py-1 rounded text-xs bg-gray-700/50 text-gray-300 border border-gray-600">
                          {specialist}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* AI Hypothesis and Fix - Parse JSON if needed */}
                {(() => {
                  let hypothesis = null
                  let fix = null
                  
                  // Try to parse ai_hypothesis or ai_solution as JSON
                  const parseAIData = (text) => {
                    if (!text) return null
                    try {
                      // Try parsing as JSON string
                      const parsed = typeof text === 'string' ? JSON.parse(text) : text
                      if (parsed && typeof parsed === 'object') {
                        if (parsed.hypothesis && parsed.fix) {
                          return { hypothesis: parsed.hypothesis, fix: parsed.fix }
                        }
                        // Also check for other possible field names
                        if (parsed.hypothesis || parsed.fix) {
                          return { hypothesis: parsed.hypothesis || null, fix: parsed.fix || null }
                        }
                      }
                    } catch (e) {
                      // Not JSON, will treat as plain text below
                    }
                    return null
                  }
                  
                  // Try to parse from ai_solution first (most likely to contain JSON)
                  const parsedData = parseAIData(issue.ai_solution) || parseAIData(issue.ai_hypothesis)
                  
                  if (parsedData) {
                    hypothesis = parsedData.hypothesis
                    fix = parsedData.fix
                  } else {
                    // Fallback to original fields if not JSON
                    hypothesis = issue.ai_hypothesis
                    fix = issue.ai_solution
                  }
                  
                  return (
                    <>
                      {hypothesis && (
                        <div className="mb-6">
                          <h4 className="text-gray-500 text-[10px] uppercase font-bold tracking-wider mb-2">AI Гипотеза</h4>
                          <div className="bg-gray-card p-4 rounded-lg border border-accent-red/50 shadow-[0_0_15px_rgba(220,38,38,0.2)]">
                            <div className="flex items-center gap-2 mb-2 text-accent-red font-bold text-xs uppercase">
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
                              Причина проблемы
                            </div>
                            <p className="text-white text-sm leading-relaxed">
                              {hypothesis}
                            </p>
                          </div>
                        </div>
                      )}
                      {fix && (
                        <div className="mb-6">
                          <h4 className="text-gray-500 text-[10px] uppercase font-bold tracking-wider mb-2">Рекомендуемое решение</h4>
                          <div className="bg-gray-card p-4 rounded-lg border border-accent-emerald/50 shadow-[0_0_15px_rgba(16,185,129,0.2)]">
                            <div className="flex items-center gap-2 mb-2 text-accent-emerald font-bold text-xs uppercase">
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                              AI Рекомендация
                            </div>
                            <p className="text-white text-sm leading-relaxed">
                              {fix}
                            </p>
                          </div>
                        </div>
                      )}
                    </>
                  )
                })()}

                {/* Impact Details */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                  <div>
                    <h4 className="text-gray-500 text-[10px] uppercase font-bold tracking-wider mb-2">Влияние на бизнес</h4>
                    <div className={`bg-gray-card p-4 rounded-lg border ${isCriticalOrWarning ? 'border-accent-red/30' : 'border-gray-divider'} h-full`}>
                      <div className={`flex items-center gap-2 mb-2 ${isCriticalOrWarning ? 'text-accent-red' : 'text-gray-400'} font-bold text-xs uppercase`}>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                        Проблема
                      </div>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-gray-400 text-sm">Оценка влияния:</span>
                          <span className="text-white font-bold">{issue.impact_score?.toFixed(1) || '0'}/10</span>
                        </div>
                        {issue.affected_sessions !== undefined && (
                          <div className="flex justify-between">
                            <span className="text-gray-400 text-sm">Затронуто сессий:</span>
                            <span className="text-white font-bold">{issue.affected_sessions}</span>
                          </div>
                        )}
                        {issue.location_url && (
                          <div className="mt-2 pt-2 border-t border-gray-divider">
                            <span className="text-gray-400 text-xs">URL:</span>
                            <code className="block text-accent-gold text-xs mt-1 break-all">{issue.location_url}</code>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 className="text-gray-500 text-[10px] uppercase font-bold tracking-wider mb-2">Дополнительная информация</h4>
                    <div className={`bg-gray-card p-4 rounded-lg border ${isCriticalOrWarning ? 'border-accent-red/30' : 'border-gray-divider'} h-full`}>
                      <div className="space-y-2 text-sm">
                        {issue.version && (
                          <div className="flex justify-between">
                            <span className="text-gray-400">Версия:</span>
                            <span className="text-white">{issue.version.name}</span>
                          </div>
                        )}
                        {issue.priority && (
                          <div className="flex justify-between items-center">
                            <span className="text-gray-400">Уровень проблемы:</span>
                            <span className={`px-2 py-1 rounded text-xs font-bold border ${getPriorityBadge(issue.priority)}`}>
                              {issue.priority === 'P0' ? 'P0 - Критическая ошибка' : 
                               issue.priority === 'P1' ? 'P1 - Предупреждение' : 
                               issue.priority === 'P2' ? 'P2 - Совет по исправлению' : 
                               issue.priority}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>


              </div>
            )}
          </div>
          )
        })}
      </div>
    </div>
  )
}