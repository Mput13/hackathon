import { createContext, useContext, useState, useEffect } from 'react'
import api from '../services/api'

const VersionsContext = createContext()

export function VersionsProvider({ children }) {
  const [versions, setVersions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchVersions = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await api.getVersions()
        setVersions(data)
      } catch (err) {
        console.error('Failed to fetch versions:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchVersions()
  }, [])

  return (
    <VersionsContext.Provider value={{ versions, loading, error }}>
      {children}
    </VersionsContext.Provider>
  )
}

export function useVersions() {
  const context = useContext(VersionsContext)
  if (!context) {
    throw new Error('useVersions must be used within VersionsProvider')
  }
  return context
}

