import { useState, useCallback, useRef } from 'react'
import VersionSelector from '../components/Comparison/VersionSelector'
import ComparisonGrid from '../components/Comparison/ComparisonGrid'
import api from '../services/api'

export default function Comparison() {
  const [v1, setV1] = useState(null)
  const [v2, setV2] = useState(null)
  const [compareData, setCompareData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const abortControllerRef = useRef(null)

  const handleCompare = useCallback(async (version1, version2) => {
    // Prevent duplicate requests
    if (!version1 || !version2) return
    
    // Cancel previous request if exists
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }

    // Create new abort controller
    const abortController = new AbortController()
    abortControllerRef.current = abortController

    setV1(version1)
    setV2(version2)
    setLoading(true)
    setError(null)

    try {
      const data = await api.getCompare(version1, version2, abortController.signal)
      
      // Check if request was aborted
      if (abortController.signal.aborted) {
        return
      }
      
      console.log('[Comparison] Received data:', data)
      // Handle data structure - data might be wrapped in 'comparison' or direct
      const processedData = data.comparison || data
      console.log('[Comparison] Processed data:', processedData)
      setCompareData(processedData)
    } catch (err) {
      // Ignore abort errors
      if (err.name === 'AbortError' || abortController.signal.aborted) {
        return
      }
      
      console.error('Failed to fetch comparison:', err)
      setError(err.message)
      setCompareData(null)
    } finally {
      // Only update loading if this request wasn't aborted
      if (!abortController.signal.aborted) {
        setLoading(false)
      }
    }
  }, [])

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header Section */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white tracking-tight">Сравнение версий</h1>
        <p className="text-gray-400 text-sm mt-1 tracking-wide">Сравнение метрик между разными версиями</p>
      </div>
      
      <VersionSelector onCompare={handleCompare} />
      <ComparisonGrid 
        loading={loading}
        isEmpty={!compareData && !loading && !error}
        compareData={compareData}
        v1={v1}
        v2={v2}
        error={error}
      />
    </div>
  )
}
