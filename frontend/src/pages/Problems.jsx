import { useState, useEffect, useRef, useCallback } from 'react'
import { useVersions } from '../contexts/VersionsContext'
import ProblemFilters from '../components/Problems/ProblemFilters'
import ProblemsTable from '../components/Problems/ProblemsTable'
import api from '../services/api'

export default function Problems() {
  const { versions, loading: versionsLoading } = useVersions()
  const [filters, setFilters] = useState({
    version: null,
    priority: 'all', // Изменено с severity на priority
    issue_type: 'all'
  })
  const [issues, setIssues] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const abortControllerRef = useRef(null)

  // Fetch issues when filters change
  const fetchIssues = useCallback(async () => {
    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }

    const abortController = new AbortController()
    abortControllerRef.current = abortController

    setLoading(true)
    setError(null)

    try {
      const params = {}
      if (filters.version && filters.version !== 'all') {
        params.version = filters.version
      }
      // Фильтрация по приоритету (P0, P2)
      // API не поддерживает priority напрямую, поэтому фильтруем на клиенте
      // Не добавляем priority в params, будем фильтровать после получения данных
      if (filters.issue_type && filters.issue_type !== 'all') {
        params.issue_type = filters.issue_type
      }

      const data = await api.getIssues(params, abortController.signal)
      
      if (abortController.signal.aborted) {
        return
      }

      // Handle response structure: {results: [...]} or array
      let issuesList = Array.isArray(data) ? data : (data.results || [])
      
      // Фильтрация по приоритету на клиенте (если выбран)
      if (filters.priority && filters.priority !== 'all') {
        issuesList = issuesList.filter(issue => {
          const issuePriority = issue.priority?.toUpperCase()
          const filterPriority = filters.priority.toUpperCase()
          return issuePriority === filterPriority
        })
      }
      
      setIssues(issuesList)
    } catch (err) {
      if (err.name === 'AbortError' || abortController.signal.aborted) {
        return
      }
      console.error('Failed to fetch issues:', err)
      setError(err.message)
      setIssues([])
    } finally {
      if (!abortController.signal.aborted) {
        setLoading(false)
      }
    }
  }, [filters])

  // Auto-select latest version when versions are loaded
  useEffect(() => {
    if (versions.length > 0 && !filters.version) {
      setFilters(prev => ({
        ...prev,
        version: versions[versions.length - 1].id
      }))
    }
  }, [versions, filters.version])

  // Fetch issues when filters change
  useEffect(() => {
    if (filters.version) {
      fetchIssues()
    }
  }, [filters, fetchIssues])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  const handleFilterChange = (filterType, value) => {
    setFilters(prev => ({
      ...prev,
      [filterType]: value
    }))
  }

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header Section */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white tracking-tight">Отслеживание проблем</h1>
        <p className="text-gray-400 text-sm mt-1 tracking-wide">Отслеживание и анализ проблем пользовательского опыта</p>
      </div>
      
      <ProblemFilters 
        versions={versions}
        filters={filters}
        onFilterChange={handleFilterChange}
        loading={versionsLoading}
      />
      
      <div className="grid grid-cols-1 gap-6">
        <div className="w-full">
          <ProblemsTable 
            issues={issues}
            loading={loading}
            error={error}
            isEmpty={!loading && issues.length === 0 && !error}
          />
        </div>
      </div>
    </div>
  )
}