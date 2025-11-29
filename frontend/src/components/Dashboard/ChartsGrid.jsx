import { useState, useEffect, useMemo } from 'react'
import { Line, Doughnut } from 'react-chartjs-2'
import SkeletonLoader from '../UI/Common/SkeletonLoader'
import EmptyState from '../UI/Common/EmptyState'
import api from '../../services/api'

export default function ChartsGrid({ loading = false, data = null, versionId = null }) {
  const [dailyStats, setDailyStats] = useState(null)
  const [loadingStats, setLoadingStats] = useState(false)
  const [selectedMonth, setSelectedMonth] = useState(null)

  // Load daily stats when version changes
  useEffect(() => {
    if (!versionId) {
      setDailyStats(null)
      setSelectedMonth(null)
      return
    }

    let cancelled = false

    const fetchDailyStats = async () => {
      setLoadingStats(true)
      setSelectedMonth(null) // Reset month selection when version changes
      try {
        const stats = await api.getDailyStats(versionId)
        if (!cancelled) {
          setDailyStats(stats)
        }
      } catch (err) {
        if (!cancelled) {
          console.error('Failed to fetch daily stats:', err)
          setDailyStats([])
        }
      } finally {
        if (!cancelled) {
          setLoadingStats(false)
        }
      }
    }

    fetchDailyStats()

    return () => {
      cancelled = true
    }
  }, [versionId])

  // Get available months from daily stats
  const availableMonths = useMemo(() => {
    if (!dailyStats || dailyStats.length === 0) return []
    
    const months = new Map()
    dailyStats.forEach(stat => {
      try {
        const date = new Date(stat.date)
        if (isNaN(date.getTime())) {
          return
        }
        const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
        const monthLabel = date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
        if (!months.has(monthKey)) {
          months.set(monthKey, { key: monthKey, label: monthLabel, count: 0 })
        }
        months.get(monthKey).count++
      } catch (e) {
        // Skip invalid dates
      }
    })
    
    return Array.from(months.values()).sort((a, b) => a.key.localeCompare(b.key))
  }, [dailyStats])

  // Auto-select latest month when months are available and no month is selected
  useEffect(() => {
    if (availableMonths.length > 0 && !selectedMonth && dailyStats) {
      setSelectedMonth(availableMonths[availableMonths.length - 1].key) // Select latest month
    }
  }, [availableMonths, selectedMonth, dailyStats])

  // Filter daily stats by selected month, or show all if no month selected
  const filteredDailyStats = useMemo(() => {
    if (!dailyStats || dailyStats.length === 0) return []
    
    // If no month selected or only one month available, show all data
    if (!selectedMonth || availableMonths.length <= 1) {
      return dailyStats
    }
    
    return dailyStats.filter(stat => {
      try {
        const date = new Date(stat.date)
        if (isNaN(date.getTime())) return false
        const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
        return monthKey === selectedMonth
      } catch {
        return false
      }
    })
  }, [dailyStats, selectedMonth, availableMonths])

  const colors = {
    red: '#DC2626',
    redLight: '#EF4444',
    redDark: '#991B1B',
    gold: '#FFD700',
    goldLight: '#FFB300',
    goldDark: '#FFCC00',
  }

  // Prepare device split chart
  const deviceData = data?.device_split ? {
    labels: data.device_split.map(d => d.device),
    datasets: [{
      data: data.device_split.map(d => d.share),
      backgroundColor: [
        'rgba(255, 215, 0, 0.8)',
        'rgba(220, 38, 38, 0.8)',
        'rgba(255, 179, 0, 0.8)',
        'rgba(239, 68, 68, 0.8)',
        'rgba(153, 27, 27, 0.8)',
      ],
      borderColor: '#1A1A1A',
      borderWidth: 2,
    }]
  } : null

  // Prepare browser split chart
  const browserData = data?.browser_split ? {
    labels: data.browser_split.map(b => b.browser),
    datasets: [{
      data: data.browser_split.map(b => b.share),
      backgroundColor: [
        'rgba(255, 215, 0, 0.8)',
        'rgba(220, 38, 38, 0.8)',
        'rgba(255, 179, 0, 0.8)',
        'rgba(239, 68, 68, 0.8)',
        'rgba(153, 27, 27, 0.8)',
      ],
      borderColor: '#1A1A1A',
      borderWidth: 2,
    }]
  } : null

  // Prepare daily stats line chart
  const lineData = filteredDailyStats && filteredDailyStats.length > 0 ? {
    labels: filteredDailyStats.map((d) => {
      try {
        const date = new Date(d.date)
        if (isNaN(date.getTime())) return d.date || ''
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      } catch {
        return d.date || ''
      }
    }),
    datasets: [
      {
        label: 'Всего сессий',
        data: filteredDailyStats.map(d => d.total_sessions || 0),
        borderColor: colors.gold,
        backgroundColor: (context) => {
          const ctx = context.chart.ctx;
          const gradient = ctx.createLinearGradient(0, 0, 0, 300);
          gradient.addColorStop(0, 'rgba(255, 215, 0, 0.2)');
          gradient.addColorStop(1, 'rgba(255, 215, 0, 0)');
          return gradient;
        },
        fill: true,
        tension: 0.4,
        yAxisID: 'y',
      },
      {
        label: 'Показатель отказов (%)',
        data: filteredDailyStats.map(d => d.bounce_rate || 0),
        borderColor: colors.red,
        backgroundColor: (context) => {
          const ctx = context.chart.ctx;
          const gradient = ctx.createLinearGradient(0, 0, 0, 300);
          gradient.addColorStop(0, 'rgba(220, 38, 38, 0.2)');
          gradient.addColorStop(1, 'rgba(220, 38, 38, 0)');
          return gradient;
        },
        fill: true,
        tension: 0.4,
        yAxisID: 'y1',
      }
    ]
  } : null

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: { color: '#9ca3af' }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        grid: { color: '#2D2D2D' },
        ticks: { color: '#9ca3af' }
      },
      y1: {
        type: 'linear',
        position: 'right',
        beginAtZero: true,
        max: 100,
        grid: { drawOnChartArea: false },
        ticks: { color: '#9ca3af' }
      },
      x: {
        grid: { color: '#2D2D2D' },
        ticks: { color: '#9ca3af' }
      }
    }
  }

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: { color: '#9ca3af', padding: 15 }
      }
    }
  }

  if (loading || loadingStats) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {[1, 2].map(i => (
          <SkeletonLoader key={i} type="chart" />
        ))}
      </div>
    )
  }

  if (!data) {
    return (
      <div className="mb-8">
        <EmptyState 
          type="charts"
          title="Данные графиков недоступны"
          description="Данные графиков недоступны для этой версии."
        />
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
      {/* Daily Stats Line Chart */}
      {lineData ? (
        <div className="bg-gray-card border border-gray-divider rounded-2xl p-6">
          <div className="flex flex-col gap-4 mb-4">
            <h3 className="text-lg font-bold text-white">ПРОСМОТРЫ ПО ДАТАМ</h3>
            {availableMonths.length > 1 && (
              <div className="flex flex-wrap gap-2">
                {availableMonths.map(month => (
                  <button
                    key={month.key}
                    onClick={() => setSelectedMonth(month.key)}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition-all duration-300 whitespace-nowrap ${
                      selectedMonth === month.key
                        ? 'bg-accent-gold/20 text-accent-gold border-accent-gold/50 shadow-[0_0_10px_rgba(255,215,0,0.2)]'
                        : 'bg-gray-modal text-gray-400 border-gray-divider hover:border-gray-500 hover:text-gray-300'
                    }`}
                  >
                    {month.label.split(' ')[0]}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="h-64">
            <Line data={lineData} options={chartOptions} />
          </div>
        </div>
      ) : dailyStats && dailyStats.length === 0 ? (
        <div className="bg-gray-card border border-gray-divider rounded-2xl p-6 flex items-center justify-center h-64">
          <p className="text-gray-500">Ежедневная статистика недоступна для этой версии</p>
        </div>
      ) : (
        <div className="bg-gray-card border border-gray-divider rounded-2xl p-6 flex items-center justify-center h-64">
          <p className="text-gray-500">Загрузка ежедневной статистики...</p>
        </div>
      )}

      {/* Device Split */}
      {deviceData ? (
        <div className="bg-gray-card border border-gray-divider rounded-2xl p-6">
          <h3 className="text-lg font-bold text-white mb-4">РАСПРЕДЕЛЕНИЕ ПО УСТРОЙСТВАМ</h3>
          <div className="h-64">
            <Doughnut data={deviceData} options={doughnutOptions} />
          </div>
        </div>
      ) : (
        <div className="bg-gray-card border border-gray-divider rounded-2xl p-6 flex items-center justify-center h-64">
          <p className="text-gray-500">Данные об устройствах недоступны</p>
        </div>
      )}

      {/* Browser Split */}
      {browserData && (
        <div className="bg-gray-card border border-gray-divider rounded-2xl p-6 lg:col-span-2">
          <h3 className="text-lg font-bold text-white mb-4">РАСПРЕДЕЛЕНИЕ ПО БРАУЗЕРАМ</h3>
          <div className="h-64">
            <Doughnut data={browserData} options={doughnutOptions} />
          </div>
        </div>
      )}
    </div>
  )
}
