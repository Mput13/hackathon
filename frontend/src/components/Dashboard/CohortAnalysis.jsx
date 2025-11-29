import { useState, useEffect } from 'react'
import { Bubble } from 'react-chartjs-2'
import SkeletonLoader from '../UI/Common/SkeletonLoader'
import EmptyState from '../UI/Common/EmptyState'
import api from '../../services/api'

export default function CohortAnalysis({ versionId = null }) {
  const [cohorts, setCohorts] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selectedCohorts, setSelectedCohorts] = useState(new Set()) // Set of cohort indices to show

  useEffect(() => {
    if (!versionId) {
      setCohorts([])
      setLoading(false)
      return
    }

    let cancelled = false

    const fetchCohorts = async () => {
      setLoading(true)
      setError(null)
      
      try {
        const data = await api.getCohorts(versionId)
        
        if (cancelled) return
        
        // Transform backend data to chart format
        // Backend returns: {id, name, percentage (0-100), users_count, avg_bounce_rate, avg_duration, ...}
        const transformedCohorts = Array.isArray(data) ? data.map(cohort => ({
          name: cohort.name,
          bounce: (cohort.avg_bounce_rate || 0) * 100, // Backend returns 0-1, convert to %
          duration: cohort.avg_duration || 0,
          users: cohort.users_count || 0,
          percentage: (cohort.percentage || 0) / 100 // Backend returns 0-100, convert to 0-1
        })) : []
        
        if (!cancelled) {
          setCohorts(transformedCohorts)
          // По умолчанию выбираем все когорты
          setSelectedCohorts(new Set(transformedCohorts.map((_, i) => i)))
        }
      } catch (err) {
        if (!cancelled) {
          console.error('[CohortAnalysis] Failed to fetch cohorts:', err)
          setError(err.message)
          setCohorts([])
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchCohorts()

    return () => {
      cancelled = true
    }
  }, [versionId])

  // Toggle cohort visibility
  const toggleCohort = (index) => {
    setSelectedCohorts(prev => {
      const newSet = new Set(prev)
      if (newSet.has(index)) {
        newSet.delete(index)
      } else {
        newSet.add(index)
      }
      return newSet
    })
  }

  // Prepare Bubble Chart Data (only for visible cohorts)
  const data = {
    datasets: cohorts
      .map((cohort, originalIndex) => ({ cohort, originalIndex }))
      .filter(({ originalIndex }) => selectedCohorts.has(originalIndex))
      .map(({ cohort, originalIndex }, filteredIndex) => ({
        label: cohort.name,
        data: [{
          x: cohort.duration,
          y: cohort.bounce,
          r: Math.sqrt(cohort.users) * 0.8 // Scale bubble size
        }],
        backgroundColor: [
          'rgba(220, 38, 38, 0.6)',  // Red
          'rgba(255, 215, 0, 0.6)',  // Gold
          'rgba(153, 27, 27, 0.7)',  // Dark Red
          'rgba(255, 179, 0, 0.6)',  // Amber
          'rgba(239, 68, 68, 0.6)',  // Light Red
        ][originalIndex % 5],
        borderColor: '#1A1A1A',
        borderWidth: 1,
        hoverBorderWidth: 0,
        hoverBorderColor: 'transparent'
      }))
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: 2000,
      easing: 'easeOutQuart'
    },
    scales: {
      x: {
        title: { display: true, text: 'Средняя длительность сессии', color: '#9ca3af' },
        grid: { color: '#2D2D2D' },
        ticks: { color: '#9ca3af' }
      },
      y: {
        title: { display: true, text: 'Показатель отказов (%)', color: '#9ca3af' },
        grid: { color: '#2D2D2D' },
        ticks: { color: '#9ca3af' },
        reverse: true // Lower bounce rate is higher up (better)
      }
    },
    plugins: {
      legend: { display: false }, // Too many cohorts for legend
      tooltip: {
        callbacks: {
          label: (ctx) => {
            const point = ctx.raw
            return `${ctx.dataset.label}: ${point.r.toFixed(0)} users (${point.y.toFixed(1)}% Bounce)`
          }
        }
      }
    }
  }

  if (loading) {
    return (
      <div className="bg-gray-card/80 backdrop-blur-md border border-gray-divider rounded-2xl p-6">
        <SkeletonLoader type="chart" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-gray-card/80 backdrop-blur-md border border-gray-divider rounded-2xl p-6">
        <EmptyState 
          type="cohorts"
          title="Ошибка загрузки когорт"
          description={error}
        />
      </div>
    )
  }

  if (!versionId || cohorts.length === 0) {
    return (
      <div className="bg-gray-card/80 backdrop-blur-md border border-gray-divider rounded-2xl p-6">
        <EmptyState 
          type="cohorts"
          title="Данные когорт отсутствуют"
          description="Данные когорт недоступны для этой версии. Когорты рассчитываются во время загрузки данных."
        />
      </div>
    )
  }

  const totalUsers = cohorts.reduce((a, b) => a + b.users, 0)

  return (
    <div className="bg-gray-card/80 backdrop-blur-md border border-gray-divider rounded-2xl p-6 shadow-lg hover:border-accent-gold/40 hover:shadow-[0_0_15px_-3px_rgba(255,215,0,0.15)] transition-all duration-500">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-bold text-white tracking-wide">ПОВЕДЕНЧЕСКИЕ ГРУППЫ ПОЛЬЗОВАТЕЛЕЙ</h3>
          <p className="text-xs text-gray-500 mt-1">
            Анализ {totalUsers.toLocaleString()} пользователей через YandexGPT
          </p>
        </div>
      </div>
      
      <div className="h-96 w-full">
        <Bubble options={options} data={data} />
      </div>

      <div className="mt-4">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-sm text-gray-400">Выберите когорты для отображения:</p>
          <div className="flex gap-2">
            <button
              onClick={() => setSelectedCohorts(new Set(cohorts.map((_, i) => i)))}
              className="text-xs px-3 py-1 bg-gray-modal border border-gray-divider rounded-lg text-gray-300 hover:bg-gray-700 transition-colors"
            >
              Выбрать все
            </button>
            <button
              onClick={() => setSelectedCohorts(new Set())}
              className="text-xs px-3 py-1 bg-gray-modal border border-gray-divider rounded-lg text-gray-300 hover:bg-gray-700 transition-colors"
            >
              Снять все
            </button>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {cohorts.map((cohort, i) => {
            const isSelected = selectedCohorts.has(i)
            return (
              <div 
                key={i} 
                className={`
                  bg-gray-modal/50 p-4 rounded-xl border transition-all duration-300
                  ${isSelected 
                    ? 'border-accent-gold/50 hover:border-accent-gold hover:bg-gray-modal' 
                    : 'border-gray-divider/30 hover:border-gray-divider/50 opacity-50'
                  }
                  cursor-pointer
                `}
                onClick={() => toggleCohort(i)}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleCohort(i)}
                      onClick={(e) => e.stopPropagation()}
                      className="w-4 h-4 rounded border-gray-divider bg-gray-back cursor-pointer flex-shrink-0"
                      style={{ 
                        accentColor: '#1A1A1A',
                        color: '#1A1A1A'
                      }}
                    />
                    <span className="text-sm font-bold text-white truncate">{cohort.name}</span>
                  </div>
                  <span className="text-xs text-gray-400 ml-2 flex-shrink-0">{(cohort.percentage * 100).toFixed(0)}%</span>
                </div>
                <div className="w-full bg-gray-700 h-2 rounded-full overflow-hidden">
                  <div className="bg-accent-gold h-full transition-all duration-300" style={{ width: `${cohort.percentage * 100}%` }}></div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
