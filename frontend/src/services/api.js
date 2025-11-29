const API_BASE = '/api'

/**
 * API Client for backend endpoints
 */
class ApiClient {
  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`
    
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        signal: options.signal, // Support AbortController
      })

      if (!response.ok) {
        const errorText = await response.text()
        // Don't log error if request was aborted
        if (options.signal?.aborted || response.status === 0) {
          console.warn(`[API] Request to ${url} was aborted or failed without response.`)
        } else {
          console.error(`[API] Error ${response.status} for ${url}:`, errorText)
        }
        throw new Error(`API Error ${response.status}: ${errorText}`)
      }

      const data = await response.json()
      return data
    } catch (error) {
      // Don't log abort errors
      if (error.name === 'AbortError') {
        console.warn(`[API] Request to ${endpoint} was aborted.`)
      } else {
        console.error(`[API] Request failed: ${endpoint}`, error)
      }
      throw error
    }
  }

  // Versions
  async getVersions() {
    const data = await this.request('/versions/')
    return Array.isArray(data) ? data : data.versions || []
  }

  // Dashboard
  async getDashboard() {
    return await this.request('/dashboard/')
  }

  // Compare
  async getCompare(v1 = null, v2 = null, signal = null) {
    const params = new URLSearchParams()
    if (v1) params.append('v1', v1)
    if (v2) params.append('v2', v2)
    const queryString = params.toString()
    return await this.request(`/compare/${queryString ? `?${queryString}` : ''}`, { signal })
  }

  // Issues
  async getIssues(params = {}) {
    const queryString = new URLSearchParams(params).toString()
    return await this.request(`/issues/${queryString ? `?${queryString}` : ''}`)
  }

  // Daily Stats
  async getDailyStats(versionId) {
    const data = await this.request(`/daily-stats/?version=${versionId}`)
    return Array.isArray(data) ? data : data.series || []
  }

  // Cohorts
  async getCohorts(versionId) {
    const data = await this.request(`/cohorts/?version=${versionId}`)
    return Array.isArray(data) ? data : data.results || []
  }

  // Pages
  async getPages(params = {}) {
    const queryString = new URLSearchParams(params).toString()
    return await this.request(`/pages/${queryString ? `?${queryString}` : ''}`)
  }

  // Paths
  async getPaths(params = {}) {
    const queryString = new URLSearchParams(params).toString()
    return await this.request(`/paths/${queryString ? `?${queryString}` : ''}`)
  }

  // Issue History
  async getIssueHistory(params = {}) {
    const queryString = new URLSearchParams(params).toString()
    return await this.request(`/issue-history/${queryString ? `?${queryString}` : ''}`)
  }

  // Funnels
  async getFunnels(versionId) {
    const data = await this.request(`/funnels/?version=${versionId}`)
    // Backend returns {count, results} or array
    return Array.isArray(data) ? data : (data.results || [])
  }

  async getFunnelDetail(funnelId) {
    const data = await this.request(`/funnels/${funnelId}/`)
    // Backend returns {funnel: {...}} or direct object
    return data.funnel || data
  }

  async getFunnelByCohorts(funnelId) {
    try {
      return await this.request(`/funnels/${funnelId}/by-cohorts/`)
    } catch (error) {
      // 404 means cohorts not calculated yet
      if (error.message.includes('404')) {
        return null
      }
      throw error
    }
  }

  // Create funnel
  async createFunnel(funnelData) {
    return await this.request('/funnels/', {
      method: 'POST',
      body: JSON.stringify(funnelData)
    })
  }

  // Get goals
  async getGoals() {
    try {
      // Пробуем сначала /goals/, потом /api/goals/
      const data = await this.request('/goals/')
      console.log('[API] Goals response from /goals/:', data)
      if (Array.isArray(data)) {
        return data
      }
      if (data && data.goals && Array.isArray(data.goals)) {
        return data.goals
      }
      if (data && Array.isArray(data.results)) {
        return data.results
      }
      return []
    } catch (error) {
      console.warn('[API] /goals/ failed, trying /api/goals/:', error.message)
      // Если /goals/ не работает, пробуем /api/goals/
      try {
        const data = await this.request('/api/goals/')
        console.log('[API] Goals response from /api/goals/:', data)
        if (Array.isArray(data)) {
          return data
        }
        if (data && data.goals && Array.isArray(data.goals)) {
          return data.goals
        }
        if (data && Array.isArray(data.results)) {
          return data.results
        }
        return []
      } catch (e) {
        console.error('[API] Failed to load goals from both endpoints:', e)
        throw e
      }
    }
  }
}

export default new ApiClient()

