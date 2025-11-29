import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  ArcElement
} from 'chart.js'
import { Line, Doughnut } from 'react-chartjs-2'
import SpotlightCard from '../UI/Common/SpotlightCard'
import SkeletonLoader from '../UI/Common/SkeletonLoader'
import EmptyState from '../UI/Common/EmptyState'
import { useVersions } from '../../contexts/VersionsContext'

ChartJS.register(ArcElement)

export default function ComparisonGrid({ loading = false, isEmpty = false, compareData = null, v1 = null, v2 = null, error = null }) {
  const { versions } = useVersions()

  const getVersionName = (id) => {
    const version = versions.find(v => v.id === id)
    return version?.name || `v${id}`
  }

  const getBarWidth = (val, max) => {
    return Math.min((val / max) * 100, 100)
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <SkeletonLoader type="chart" />
        <SkeletonLoader type="card" />
        <SkeletonLoader type="card" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <EmptyState 
          type="comparison"
          title="Ошибка загрузки сравнения"
          description={error}
        />
      </div>
    )
  }

  if (isEmpty || !compareData) {
    return (
      <div className="space-y-6">
        <EmptyState 
          type="comparison"
          title="Данные сравнения недоступны"
          description="Выберите две версии для сравнения их метрик и выявления улучшений."
        />
      </div>
    )
  }

  console.log('[ComparisonGrid] compareData:', compareData)

  // Extract data - handle both direct and nested structure
  const data = compareData.comparison || compareData
  
  const stats_v1 = data.stats_v1 || {}
  const stats_v2 = data.stats_v2 || {}
  const issues_diff = Array.isArray(data.issues_diff) ? data.issues_diff : []
  const pages_diff = Array.isArray(data.pages_diff) ? data.pages_diff : []
  const cohorts_diff = Array.isArray(data.cohorts_diff) ? data.cohorts_diff : []
  const device_split = data.device_split || []
  const browser_split = data.browser_split || []
  const os_split = data.os_split || []
  const paths_v1 = data.paths_v1 || []
  const paths_v2 = data.paths_v2 || []
  const alerts = Array.isArray(data.alerts) ? data.alerts : []
  const visits_diff = data.visits_diff !== undefined ? data.visits_diff : 0
  const bounce_diff = data.bounce_diff !== undefined ? data.bounce_diff : 0
  const duration_diff = data.duration_diff !== undefined ? data.duration_diff : 0
  const v1_cohorts = Array.isArray(data.v1_cohorts) ? data.v1_cohorts : []
  const v2_cohorts = Array.isArray(data.v2_cohorts) ? data.v2_cohorts : []

  // Get version info from comparison data
  const v1Info = data.v1 || { id: v1, name: getVersionName(v1) }
  const v2Info = data.v2 || { id: v2, name: getVersionName(v2) }

  console.log('[ComparisonGrid] Extracted data:', {
    stats_v1,
    stats_v2,
    visits_diff,
    bounce_diff,
    duration_diff,
    issues_diff: issues_diff.length,
    pages_diff: pages_diff.length,
    cohorts_diff: cohorts_diff.length,
    alerts: alerts.length
  })

  // Prepare metrics comparison using actual API data
  const metrics = [
    {
      metric: "Всего визитов",
      desc: "Объем трафика",
      v1: stats_v1.visits || 0,
      v2: stats_v2.visits || 0,
      diff: visits_diff,
      trend: visits_diff >= 0 ? "positive" : "negative",
      unit: ""
    },
    {
      metric: "Показатель отказов",
      desc: "Пользователи, ушедшие сразу",
      v1: stats_v1.bounce || stats_v1.bounce_rate || 0,
      v2: stats_v2.bounce || stats_v2.bounce_rate || 0,
      diff: bounce_diff,
      trend: bounce_diff <= 0 ? "positive" : "negative", // Lower is better
      unit: "%"
    },
    {
      metric: "Средняя длительность сессии",
      desc: "Время, проведенное на сайте",
      v1: stats_v1.duration || stats_v1.avg_duration || 0,
      v2: stats_v2.duration || stats_v2.avg_duration || 0,
      diff: duration_diff,
      trend: duration_diff >= 0 ? "positive" : "negative",
      unit: "s"
    }
  ]

  console.log('[ComparisonGrid] Metrics:', metrics)

  // Color palette for charts - harmonious orange, red, and yellow shades with good contrast
  const chartColors = [
    'rgba(255, 235, 59, 0.75)',   // Bright Yellow
    'rgba(255, 193, 7, 0.75)',    // Amber
    'rgba(255, 152, 0, 0.75)',    // Orange
    'rgba(255, 111, 0, 0.75)',    // Deep Orange
    'rgba(255, 87, 34, 0.75)',    // Orange Red
    'rgba(251, 140, 0, 0.75)',    // Dark Orange
    'rgba(245, 124, 0, 0.75)',    // Burnt Orange
    'rgba(230, 81, 0, 0.75)',     // Rust Orange
    'rgba(255, 61, 0, 0.75)',     // Red Orange
    'rgba(244, 67, 54, 0.75)',    // Red
    'rgba(229, 57, 53, 0.75)',    // Deep Red
    'rgba(211, 47, 47, 0.75)',    // Dark Red
    'rgba(198, 40, 40, 0.75)',    // Crimson
    'rgba(183, 28, 28, 0.75)',    // Dark Crimson
    'rgba(255, 202, 40, 0.75)',   // Golden Yellow
    'rgba(255, 193, 7, 0.75)',    // Gold
    'rgba(255, 160, 0, 0.75)',    // Orange Yellow
    'rgba(255, 143, 0, 0.75)',    // Tangerine
    'rgba(255, 112, 67, 0.75)',   // Light Orange Red
    'rgba(255, 82, 82, 0.75)',    // Light Red
  ]

  const chartBorderColors = [
    'rgb(255, 235, 59)',   // Bright Yellow
    'rgb(255, 193, 7)',    // Amber
    'rgb(255, 152, 0)',    // Orange
    'rgb(255, 111, 0)',    // Deep Orange
    'rgb(255, 87, 34)',    // Orange Red
    'rgb(251, 140, 0)',    // Dark Orange
    'rgb(245, 124, 0)',    // Burnt Orange
    'rgb(230, 81, 0)',     // Rust Orange
    'rgb(255, 61, 0)',     // Red Orange
    'rgb(244, 67, 54)',    // Red
    'rgb(229, 57, 53)',    // Deep Red
    'rgb(211, 47, 47)',    // Dark Red
    'rgb(198, 40, 40)',    // Crimson
    'rgb(183, 28, 28)',    // Dark Crimson
    'rgb(255, 202, 40)',   // Golden Yellow
    'rgb(255, 193, 7)',    // Gold
    'rgb(255, 160, 0)',    // Orange Yellow
    'rgb(255, 143, 0)',    // Tangerine
    'rgb(255, 112, 67)',   // Light Orange Red
    'rgb(255, 82, 82)',    // Light Red
  ]

  // Prepare split charts with different colors for each item
  const prepareSplitChart = (splitData, title) => {
    if (!splitData || splitData.length === 0) return null

    const labels = splitData.map(item => item.device || item.browser || item.os || 'Неизвестно')
    const v1Data = splitData.map(item => item.share_v1 || 0)
    const v2Data = splitData.map(item => item.share_v2 || 0)

    // Create color arrays for each dataset - each item gets a unique color
    const v1Colors = labels.map((_, i) => chartColors[i % chartColors.length])
    const v2Colors = labels.map((_, i) => chartColors[i % chartColors.length])
    const v1BorderColors = labels.map((_, i) => chartBorderColors[i % chartBorderColors.length])
    const v2BorderColors = labels.map((_, i) => chartBorderColors[i % chartBorderColors.length])

    return {
      labels,
      datasets: [
        {
          label: `${v1Info.name || getVersionName(v1)} Доля`,
          data: v1Data,
          backgroundColor: v1Colors,
          borderColor: v1BorderColors,
          borderWidth: 2
        },
        {
          label: `${v2Info.name || getVersionName(v2)} Доля`,
          data: v2Data,
          backgroundColor: v2Colors,
          borderColor: v2BorderColors,
          borderWidth: 2
        }
      ]
    }
  }

  // Prepare Doughnut chart data with different colors for each item
  const prepareDoughnutChart = (splitData) => {
    if (!splitData || splitData.length === 0) return null

    const labels = splitData.map(item => item.device || item.browser || item.os || 'Неизвестно')
    const v2Data = splitData.map(item => item.share_v2 || 0)

    // Each item gets a unique color from the palette
    const backgroundColors = labels.map((_, i) => chartColors[i % chartColors.length])
    const borderColors = labels.map((_, i) => chartBorderColors[i % chartBorderColors.length])

    return {
      labels,
      datasets: [
        {
          label: `${v2Info.name || getVersionName(v2)} Доля`,
          data: v2Data,
          backgroundColor: backgroundColors,
          borderColor: borderColors,
          borderWidth: 2
        }
      ]
    }
  }

  const deviceChartData = prepareDoughnutChart(device_split)
  const browserChartData = prepareDoughnutChart(browser_split)
  const osChartData = prepareDoughnutChart(os_split)

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top', labels: { color: '#9ca3af' } },
      tooltip: { mode: 'index', intersect: false }
    },
    scales: {
      x: { grid: { color: '#2D2D2D' }, ticks: { color: '#9ca3af' } },
      y: { grid: { color: '#2D2D2D' }, ticks: { color: '#9ca3af' } }
    }
  }

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom', labels: { color: '#9ca3af', padding: 15 } }
    }
  }

  return (
    <div className="space-y-6">
      {/* AI Summary Block - Moved to top */}
      <SpotlightCard 
        className="bg-gray-card/80 border border-accent-gold/30 rounded-2xl p-6" 
        glowColor="rgba(255, 215, 0, 0.15)"
      >
        <div className="relative z-10 flex items-start gap-4">
          <div className="p-3 bg-accent-gold/20 rounded-full text-accent-gold">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <h4 className="text-accent-gold font-bold text-lg mb-2">ИТОГИ СРАВНЕНИЯ</h4>
            <p className="text-gray-300 text-sm leading-relaxed">
              Сравнение {v1Info.name || getVersionName(v1)} и {v2Info.name || getVersionName(v2)} показывает 
              {visits_diff > 0 ? ' увеличение' : visits_diff < 0 ? ' уменьшение' : ' отсутствие изменений'} объема трафика ({visits_diff > 0 ? '+' : ''}{visits_diff} визитов).
              {bounce_diff < 0 
                ? ` Показатель отказов улучшился на ${Math.abs(bounce_diff).toFixed(1)}%, что указывает на лучшую вовлеченность пользователей.` 
                : bounce_diff > 0
                ? ` Показатель отказов увеличился на ${bounce_diff.toFixed(1)}%, что может указывать на проблемы с удобством использования.`
                : ' Показатель отказов остался стабильным.'}
              {duration_diff > 0 
                ? ` Длительность сессии увеличилась на ${duration_diff.toFixed(1)}с, показывая улучшенную вовлеченность.`
                : duration_diff < 0
                ? ` Длительность сессии уменьшилась на ${Math.abs(duration_diff).toFixed(1)}с, что может указывать на проблемы.`
                : ' Длительность сессии осталась стабильной.'}
            </p>
          </div>
        </div>
      </SpotlightCard>

      {/* Quick Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Bounce Rate Change */}
        <div className={`bg-gray-card border border-gray-divider rounded-xl p-4 text-center transition-all duration-300 ${
          bounce_diff > 0 
            ? 'hover:border-accent-red/50 hover:shadow-[0_0_15px_-3px_rgba(220,38,38,0.3)]' 
            : bounce_diff < 0 
            ? 'hover:border-accent-emerald/50 hover:shadow-[0_0_15px_-3px_rgba(16,185,129,0.3)]'
            : 'hover:border-gray-divider/70'
        }`}>
          <p className="text-xs text-gray-500 mb-1 uppercase tracking-wide">Изменение показателя отказов</p>
          <p className={`text-3xl font-bold font-mono mb-1 ${
            bounce_diff > 0 ? 'text-accent-red' : bounce_diff < 0 ? 'text-accent-emerald' : 'text-gray-400'
          }`}>
            {bounce_diff > 0 ? '+' : ''}{bounce_diff.toFixed(1)}%
          </p>
          <p className="text-xs text-gray-500">Меньше лучше</p>
        </div>

        {/* Avg Duration Change */}
        <div className={`bg-gray-card border border-gray-divider rounded-xl p-4 text-center transition-all duration-300 ${
          duration_diff > 0 
            ? 'hover:border-accent-emerald/50 hover:shadow-[0_0_15px_-3px_rgba(16,185,129,0.3)]' 
            : duration_diff < 0 
            ? 'hover:border-accent-red/50 hover:shadow-[0_0_15px_-3px_rgba(220,38,38,0.3)]'
            : 'hover:border-gray-divider/70'
        }`}>
          <p className="text-xs text-gray-500 mb-1 uppercase tracking-wide">Изменение средней длительности</p>
          <p className={`text-3xl font-bold font-mono mb-1 ${
            duration_diff > 0 ? 'text-accent-emerald' : duration_diff < 0 ? 'text-accent-red' : 'text-gray-400'
          }`}>
            {duration_diff > 0 ? '+' : ''}{duration_diff.toFixed(1)}s
          </p>
          <p className="text-xs text-gray-500">Зависит от контекста</p>
        </div>

        {/* Traffic Volume */}
        <div className="bg-gray-card border border-gray-divider rounded-xl p-4 text-center transition-all duration-300 hover:border-accent-gold/50 hover:shadow-[0_0_15px_-3px_rgba(255,215,0,0.3)]">
          <p className="text-xs text-gray-500 mb-1 uppercase tracking-wide">Объем трафика</p>
          <p className="text-3xl font-bold font-mono mb-1 text-white">
            {visits_diff > 0 ? '+' : ''}{visits_diff}
          </p>
          <p className="text-xs text-gray-500">Разница сессий</p>
        </div>
      </div>

      {/* Metrics Comparison */}
      <div className="bg-gray-card border border-gray-divider rounded-2xl p-6">
        <h3 className="text-lg font-bold text-white mb-6">
          СРАВНЕНИЕ МЕТРИК ({v1Info.name || getVersionName(v1)} vs {v2Info.name || getVersionName(v2)})
        </h3>
        
        <div className="space-y-6">
          {metrics.map((item, index) => {
            const maxVal = Math.max(item.v1, item.v2) * 1.2 || 1
            const glowClass = item.trend === 'positive' 
              ? 'hover:border-accent-emerald/50 hover:shadow-[0_0_15px_-3px_rgba(16,185,129,0.2)]' 
              : 'hover:border-accent-red/50 hover:shadow-[0_0_15px_-3px_rgba(220,38,38,0.2)]'

            return (
              <div key={index} className={`bg-gray-modal/50 rounded-xl p-4 border border-gray-divider/50 transition-all duration-300 ${glowClass}`}>
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h4 className="font-bold text-white text-lg">{item.metric}</h4>
                    <p className="text-sm text-gray-500">{item.desc}</p>
                  </div>
                  <div className={`text-right ${item.trend === 'positive' ? 'text-accent-emerald' : 'text-accent-red'}`}>
                    <div className="text-2xl font-bold font-mono">
                      {item.diff > 0 ? '+' : ''}{item.diff.toFixed(1)}{item.unit}
                    </div>
                    <div className="text-xs uppercase tracking-wide font-bold">Изменение</div>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="relative">
                    <div className="flex justify-between text-xs text-gray-400 mb-1">
                      <span>{v1Info.name || getVersionName(v1)}</span>
                      <span>{item.v1.toFixed(1)}{item.unit}</span>
                    </div>
                    <div className="h-3 w-full bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gray-500 rounded-full" 
                        style={{ width: `${getBarWidth(item.v1, maxVal)}%` }}
                      />
                    </div>
                  </div>

                  <div className="relative">
                    <div className="flex justify-between text-xs text-white mb-1 font-bold">
                      <span>{v2Info.name || getVersionName(v2)}</span>
                      <span>{item.v2.toFixed(1)}{item.unit}</span>
                    </div>
                    <div className="h-3 w-full bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full ${item.trend === 'positive' ? 'bg-accent-emerald' : 'bg-accent-red'}`} 
                        style={{ width: `${getBarWidth(item.v2, maxVal)}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Issues Diff */}
      {issues_diff.length > 0 && (
        <div className="bg-gray-card border border-gray-divider rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-bold text-white">ИЗМЕНЕНИЯ ПРОБЛЕМ</h3>
            <div className="text-xs text-gray-500">Новая/Ухудшилась/Улучшилась/Решена</div>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-700/50 text-gray-300 uppercase text-xs">
                <tr>
                  <th className="px-4 py-3 text-left">Тип</th>
                  <th className="px-4 py-3 text-left">Местоположение</th>
                  <th className="px-4 py-3 text-left">Статус</th>
                  <th className="px-4 py-3 text-right">Влияние Δ</th>
                  <th className="px-4 py-3 text-right">Влияние</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-divider">
                {issues_diff.slice(0, 20).map((issue, i) => {
                  // Issue types display mapping
                  const ISSUE_TYPES = {
                    'RAGE_CLICK': 'Беспорядочные клики',
                    'DEAD_CLICK': 'Мертвые клики',
                    'LOOPING': 'Навигационный цикл',
                    'FORM_ABANDON': 'Отказ от формы',
                    'HIGH_BOUNCE': 'Высокий показатель отказов',
                    'WANDERING': 'Блуждающие пользователи',
                    'NAVIGATION_BACK': 'Частое использование кнопки "Назад"',
                    'FORM_FIELD_ERRORS': 'Ошибки ввода в форме',
                    'FUNNEL_DROPOFF': 'Точка оттока воронки',
                    'SCAN_AND_DROP': 'Быстрый просмотр и уход',
                    'SEARCH_FAIL': 'Ошибка поиска'
                  }
                  
                  const getIssueTypeDisplay = (issueType) => {
                    return ISSUE_TYPES[issueType] || issueType
                  }
                  
                  const getStatusLabel = (status) => {
                    switch (status) {
                      case 'new': return 'Новая'
                      case 'worse': return 'Ухудшилась'
                      case 'improved': return 'Улучшилась'
                      case 'resolved': return 'Решена'
                      default: return status?.charAt(0).toUpperCase() + status?.slice(1) || 'Неизвестно'
                    }
                  }
                  
                  const getStatusColor = (status) => {
                    switch (status) {
                      case 'new': return 'text-accent-emerald'
                      case 'worse': return 'text-accent-red'
                      case 'improved': return 'text-accent-emerald'
                      case 'resolved': return 'text-gray-400'
                      default: return 'text-gray-400'
                    }
                  }
                  
                  return (
                    <tr key={issue.id || i} className="hover:bg-gray-modal/30 transition-colors">
                      <td className="px-4 py-3">
                        <div className="font-semibold text-white">{getIssueTypeDisplay(issue.issue_type)}</div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-white font-medium">{issue.location_readable || 'Неизвестно'}</div>
                        {issue.location_url && (
                          <div className="text-xs text-gray-500 font-mono mt-1 break-all max-w-md">
                            {issue.location_url}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`font-semibold ${getStatusColor(issue.status)}`}>
                          {getStatusLabel(issue.status)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className={`font-mono font-bold ${
                          issue.impact_diff > 0 ? 'text-accent-red' : 
                          issue.impact_diff < 0 ? 'text-accent-emerald' : 
                          'text-gray-400'
                        }`}>
                          {issue.impact_diff > 0 ? '+' : ''}{issue.impact_diff?.toFixed(1) || '0.0'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="font-mono text-white">{issue.impact_score?.toFixed(1) || '0.0'}</span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Split Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {deviceChartData && (
          <div className="bg-gray-card border border-gray-divider rounded-2xl p-6">
            <h3 className="text-lg font-bold text-white mb-4">РАСПРЕДЕЛЕНИЕ ПО УСТРОЙСТВАМ</h3>
            <div className="h-64">
              <Doughnut data={deviceChartData} options={doughnutOptions} />
            </div>
          </div>
        )}

        {browserChartData && (
          <div className="bg-gray-card border border-gray-divider rounded-2xl p-6">
            <h3 className="text-lg font-bold text-white mb-4">РАСПРЕДЕЛЕНИЕ ПО БРАУЗЕРАМ</h3>
            <div className="h-64">
              <Doughnut data={browserChartData} options={doughnutOptions} />
            </div>
          </div>
        )}
      </div>

      {/* Audience Segments Comparison */}
      {(v1_cohorts.length > 0 || v2_cohorts.length > 0) && (
        <div className="bg-gray-card border border-gray-divider rounded-2xl p-6">
          <div className="mb-6">
            <h3 className="text-lg font-bold text-white mb-2">ПОВЕДЕНЧЕСКИЕ ГРУППЫ ПОЛЬЗОВАТЕЛЕЙ</h3>
          </div>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* V1 Column */}
            {v1_cohorts.length > 0 && (
              <div className="bg-gray-modal/30 border border-gray-divider rounded-xl p-6">
                <div className="mb-4">
                  <h4 className="text-center font-bold text-gray-400 uppercase tracking-wider mb-2">{v1Info.name || getVersionName(v1)}</h4>
                  <p className="text-center text-sm text-gray-500">Всего визитов: {stats_v1.visits || 0}</p>
                </div>
                
                <div className="space-y-3">
                  {v1_cohorts.map((cohort, i) => (
                    <div key={i} className="bg-gray-card p-4 rounded-lg border-2 border-accent-emerald/50">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <div className="bg-accent-gold/20 border-2 border-accent-gold/50 rounded-lg w-10 h-10 flex items-center justify-center flex-shrink-0">
                              <span className="text-accent-gold font-bold text-[10px]">{(cohort.percentage || 0).toFixed(2)}%</span>
                            </div>
                            <h5 className="font-bold text-white text-sm">{cohort.name}</h5>
                          </div>
                        </div>
                      </div>
                      <div className="grid grid-cols-4 gap-2 text-xs text-gray-400">
                        <div>
                          <span className="block text-gray-500">Отказы</span>
                          <span className="font-medium text-white">{(cohort.avg_bounce_rate || 0).toFixed(1)}%</span>
                        </div>
                        <div>
                          <span className="block text-gray-500">Время</span>
                          <span className="font-medium text-white">{Math.round(cohort.avg_duration || 0)}с</span>
                        </div>
                        <div>
                          <span className="block text-gray-500">Глубина</span>
                          <span className="font-medium text-white">{cohort.metrics?.depth || 'Н/Д'}</span>
                        </div>
                        <div>
                          <span className="block text-gray-500">Пользователи</span>
                          <span className="font-medium text-white">{cohort.users_count || 0}</span>
                        </div>
                      </div>
                      {cohort.metrics?.top_goals && (
                        <div className="mt-2 pt-2 border-t border-gray-divider/30 text-xs">
                          <span className="text-accent-emerald font-medium">Топ цель:</span> {cohort.metrics.top_goals}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* V2 Column */}
            {v2_cohorts.length > 0 && (
              <div className="bg-gray-modal/30 border border-gray-divider rounded-xl p-6">
                <div className="mb-4">
                  <h4 className="text-center font-bold text-gray-400 uppercase tracking-wider mb-2">{v2Info.name || getVersionName(v2)}</h4>
                  <p className="text-center text-sm text-gray-500">Всего визитов: {stats_v2.visits || 0}</p>
                </div>
                
                <div className="space-y-3">
                  {v2_cohorts.map((cohort, i) => (
                    <div key={i} className="bg-gray-card p-4 rounded-lg border-2 border-accent-emerald/50">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <div className="bg-accent-gold/20 border-2 border-accent-gold/50 rounded-lg w-10 h-10 flex items-center justify-center flex-shrink-0">
                              <span className="text-accent-gold font-bold text-[10px]">{(cohort.percentage || 0).toFixed(2)}%</span>
                            </div>
                            <h5 className="font-bold text-white text-sm">{cohort.name}</h5>
                          </div>
                        </div>
                      </div>
                      <div className="grid grid-cols-4 gap-2 text-xs text-gray-400">
                        <div>
                          <span className="block text-gray-500">Отказы</span>
                          <span className="font-medium text-white">{(cohort.avg_bounce_rate || 0).toFixed(1)}%</span>
                        </div>
                        <div>
                          <span className="block text-gray-500">Время</span>
                          <span className="font-medium text-white">{Math.round(cohort.avg_duration || 0)}с</span>
                        </div>
                        <div>
                          <span className="block text-gray-500">Глубина</span>
                          <span className="font-medium text-white">{cohort.metrics?.depth || 'Н/Д'}</span>
                        </div>
                        <div>
                          <span className="block text-gray-500">Пользователи</span>
                          <span className="font-medium text-white">{cohort.users_count || 0}</span>
                        </div>
                      </div>
                      {cohort.metrics?.top_goals && (
                        <div className="mt-2 pt-2 border-t border-gray-divider/30 text-xs">
                          <span className="text-accent-emerald font-medium">Топ цель:</span> {cohort.metrics.top_goals}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
