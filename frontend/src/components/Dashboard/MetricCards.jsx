import { useState, useEffect } from 'react'
import MetricCard from '../UI/Common/MetricCard'
import SkeletonLoader from '../UI/Common/SkeletonLoader'
import EmptyState from '../UI/Common/EmptyState'

export default function MetricCards({ loading = false, isEmpty = false, data = null }) {
  const [isLoading, setIsLoading] = useState(loading)

  useEffect(() => {
    setIsLoading(loading)
  }, [loading])

  // Calculate metrics from dashboard data
  const getMetrics = () => {
    if (!data) {
      return null
    }
    
    // Бэкенд возвращает bounce_rate уже в процентах (0-100), avg_duration в секундах
    // Проверяем, что значения существуют (включая 0)
    const bounceRate = (data.bounce_rate !== undefined && data.bounce_rate !== null) ? Number(data.bounce_rate) : null
    const avgDuration = (data.avg_duration !== undefined && data.avg_duration !== null) ? Number(data.avg_duration) : null
    
    return {
      conversion: bounceRate !== null ? (100 - bounceRate).toFixed(1) + '%' : 'N/A',
      bounce: bounceRate !== null ? bounceRate.toFixed(1) + '%' : 'N/A',
      avgSession: avgDuration !== null ? Math.round(avgDuration) + ' сек' : 'N/A',
      problems: data.issue_count || 0,
      visits: data.total_visits || 0
    }
  }

  const metrics = getMetrics()

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {[1, 2, 3, 4].map(i => (
          <SkeletonLoader key={i} type="metric" />
        ))}
      </div>
    )
  }

  if (isEmpty || !metrics) {
    return (
      <div className="mb-8">
        <EmptyState 
          type="metrics"
          title="Метрики недоступны"
          description="Данные метрик недоступны в данный момент. Пожалуйста, попробуйте позже."
        />
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <MetricCard 
        title="ВСЕГО ВИЗИТОВ" 
        value={metrics.visits.toLocaleString()}
        trend=""
        trendType="neutral"
        glowColor="gold"
      />
      <MetricCard 
        title="ПОКАЗАТЕЛЬ ОТКАЗОВ" 
        value={metrics.bounce}
        trend=""
        trendType="neutral"
        glowColor="red"
      />
      <MetricCard 
        title="СРЕДНЯЯ СЕССИЯ" 
        value={metrics.avgSession}
        trend=""
        trendType="neutral"
        glowColor="gold"
      />
      <MetricCard 
        title="АКТИВНЫЕ ПРОБЛЕМЫ" 
        value={metrics.problems}
        trend=""
        trendType="neutral"
        glowColor="red"
      />
    </div>
  )
}
