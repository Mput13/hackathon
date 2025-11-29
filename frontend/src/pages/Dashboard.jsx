import { useState, useEffect } from 'react'
import MetricCards from '../components/Dashboard/MetricCards'
import ChartsGrid from '../components/Dashboard/ChartsGrid'
import Allnsights from '../components/Dashboard/Allnsights'
import CohortAnalysis from '../components/Dashboard/CohortAnalysis'
import { useVersions } from '../contexts/VersionsContext'
import api from '../services/api'

export default function Dashboard({ onNavigate }) {
  const { versions } = useVersions()
  const [selectedVersion, setSelectedVersion] = useState(null)
  const [dashboardData, setDashboardData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Auto-select latest version when versions are loaded
  useEffect(() => {
    if (versions.length > 0 && !selectedVersion) {
      setSelectedVersion(versions[versions.length - 1].id) // Select latest version
    }
  }, [versions, selectedVersion])

  // Load dashboard data when version is selected
  useEffect(() => {
    if (!selectedVersion) return

    let cancelled = false

    const fetchDashboard = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await api.getDashboard()
        
        if (cancelled) return
        
        // Filter data for selected version
        const versionData = data.version_stats?.find(v => v.id === selectedVersion)
        
        if (!cancelled) {
          if (versionData) {
            setDashboardData({
              version: versionData,
              recent_issues: data.recent_issues || []
            })
          } else {
            setDashboardData(null)
          }
        }
      } catch (err) {
        if (!cancelled) {
          console.error('Failed to fetch dashboard:', err)
          setError(err.message)
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchDashboard()

    return () => {
      cancelled = true
    }
  }, [selectedVersion])

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header Section */}
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">UX Панель управления</h1>
          <p className="text-gray-400 text-sm mt-1 tracking-wide">Мониторинг и анализ</p>
        </div>
        
        {/* Versions Selector */}
        <div className="flex gap-4 overflow-x-auto pb-4 pt-2 px-1">
          {versions.map(v => {
            const isActive = selectedVersion === v.id
            return (
              <button
                key={v.id}
                onClick={() => setSelectedVersion(v.id)}
                className={`
                  relative flex flex-col items-center justify-center 
                  w-20 h-20 rounded-2xl border transition-all duration-500 ease-out
                  ${isActive 
                    ? 'bg-gray-card border-accent-red shadow-[0_0_15px_rgba(220,38,38,0.5)] scale-100' 
                    : 'bg-gray-card/50 border-gray-divider hover:border-accent-red/50 hover:scale-105'
                  }
                `}
              >
                <span className={`text-lg font-bold transition-colors duration-300 ${isActive ? 'text-white' : 'text-gray-500'}`}>
                  {v.name?.split(' ')[0] || v.id}
                </span>
                <span className="text-[10px] text-gray-600 mt-0.5 font-medium uppercase tracking-wide">
                  {v.name?.split('(')[1]?.replace(')', '') || ''}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {error && (
        <div className="bg-accent-red/20 border border-accent-red/50 rounded-lg p-4 text-accent-red">
          Ошибка загрузки панели управления: {error}
        </div>
      )}

      <div className="animate-slideUp" style={{ animationDelay: '0.1s' }}>
        <MetricCards 
          loading={loading} 
          isEmpty={!dashboardData}
          data={dashboardData?.version}
        />
      </div>
      
      <div className="animate-slideUp" style={{ animationDelay: '0.2s' }}>
        <ChartsGrid 
          loading={loading}
          data={dashboardData?.version}
          versionId={selectedVersion}
        />
      </div>

      {/* New Section: Advanced Analysis */}
      <div className="animate-slideUp" style={{ animationDelay: '0.25s' }}>
        <CohortAnalysis versionId={selectedVersion} />
      </div>

      <div className="animate-slideUp" style={{ animationDelay: '0.3s' }}>
        <Allnsights 
          onViewAll={() => onNavigate && onNavigate('problems')}
          onIssueClick={() => onNavigate && onNavigate('problems')}
          recentIssues={dashboardData?.recent_issues}
          loading={loading}
        />
      </div>
    </div>
  )
}
