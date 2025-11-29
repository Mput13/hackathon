export default function ProblemFilters({ versions = [], filters = {}, onFilterChange, loading = false }) {
  // Issue types mapping
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

  return (
    <div className="bg-gray-card border border-gray-divider rounded-2xl p-6 mb-6 hover:border-accent-red/40 hover:shadow-[0_0_15px_-3px_rgba(220,38,38,0.15)] transition-all duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <h3 className="text-lg font-semibold text-white">ФИЛЬТРЫ ПРОБЛЕМ</h3>
        
        <div className="flex flex-wrap gap-4">
          {/* Version Filter */}
          <div>
            <select 
              value={filters.version || 'all'}
              onChange={(e) => onFilterChange('version', e.target.value === 'all' ? null : parseInt(e.target.value))}
              disabled={loading}
              className="bg-gray-modal border border-gray-divider rounded-xl py-2 px-3 text-white text-sm focus:outline-none focus:border-accent-red transition-colors hover:border-gray-500 disabled:opacity-50"
            >
              <option value="all">Все версии</option>
              {versions.map(version => (
                <option key={version.id} value={version.id}>{version.name}</option>
              ))}
            </select>
          </div>

          {/* Priority Filter (уровни проблемы) */}
          <div>
            <select 
              value={filters.priority || 'all'}
              onChange={(e) => onFilterChange('priority', e.target.value)}
              className="bg-gray-modal border border-gray-divider rounded-xl py-2 px-3 text-white text-sm focus:outline-none focus:border-accent-red transition-colors hover:border-gray-500"
            >
              <option value="all">Все уровни проблемы</option>
              <option value="P0">P0 - Критическая ошибка</option>
              <option value="P1">P1 - Предупреждение</option>
              <option value="P2">P2 - Совет по исправлению</option>
            </select>
          </div>

          {/* Issue Type Filter */}
          <div>
            <select 
              value={filters.issue_type || 'all'}
              onChange={(e) => onFilterChange('issue_type', e.target.value)}
              className="bg-gray-modal border border-gray-divider rounded-xl py-2 px-3 text-white text-sm focus:outline-none focus:border-accent-red transition-colors hover:border-gray-500"
            >
              <option value="all">Все типы</option>
              {Object.entries(ISSUE_TYPES).map(([code, label]) => (
                <option key={code} value={code}>{label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </div>
  )
}