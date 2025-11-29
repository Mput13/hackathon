export default function EmptyState({ 
  type = 'default',
  title = 'No data available',
  description = 'There is no data to display at the moment.',
  icon,
  action,
  className = ''
}) {
  // Empty state для проблем
  if (type === 'problems') {
    return (
      <div className={`bg-gray-card border border-gray-divider rounded-2xl p-12 text-center ${className}`}>
        <div className="flex justify-center mb-4">
          <div className="p-4 bg-gray-modal rounded-full">
            <svg className="w-12 h-12 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
        </div>
        <h3 className="text-xl font-bold text-white mb-2">{title}</h3>
        <p className="text-gray-400 text-sm mb-6 max-w-md mx-auto">{description}</p>
        {action && action}
      </div>
    )
  }

  // Empty state для сравнения
  if (type === 'comparison') {
    return (
      <div className={`bg-gray-card border border-gray-divider rounded-2xl p-12 text-center ${className}`}>
        <div className="flex justify-center mb-4">
          <div className="p-4 bg-gray-modal rounded-full">
            <svg className="w-12 h-12 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
            </svg>
          </div>
        </div>
        <h3 className="text-xl font-bold text-white mb-2">{title}</h3>
        <p className="text-gray-400 text-sm mb-6 max-w-md mx-auto">{description}</p>
        {action && action}
      </div>
    )
  }

  // Empty state для графиков
  if (type === 'chart') {
    return (
      <div className={`bg-gray-card border border-gray-divider rounded-2xl p-12 flex flex-col items-center justify-center min-h-[300px] ${className}`}>
        <div className="p-4 bg-gray-modal rounded-full mb-4">
          {icon || (
            <svg className="w-12 h-12 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          )}
        </div>
        <h3 className="text-lg font-bold text-white mb-2">{title}</h3>
        <p className="text-gray-400 text-sm text-center max-w-sm">{description}</p>
        {action && <div className="mt-6">{action}</div>}
      </div>
    )
  }

  // Empty state для метрик
  if (type === 'metrics') {
    return (
      <div className={`bg-gray-card border border-gray-divider rounded-2xl p-8 text-center ${className}`}>
        <div className="p-3 bg-gray-modal rounded-full inline-flex mb-4">
          <svg className="w-8 h-8 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <h3 className="text-lg font-bold text-white mb-2">{title}</h3>
        <p className="text-gray-400 text-sm">{description}</p>
      </div>
    )
  }

  // Empty state для воронок
  if (type === 'funnels') {
    return (
      <div className={`bg-gray-card border border-gray-divider rounded-2xl p-12 text-center ${className}`}>
        <div className="flex justify-center mb-4">
          <div className="p-4 bg-gray-modal rounded-full">
            <svg className="w-12 h-12 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
        </div>
        <h3 className="text-xl font-bold text-white mb-2">{title}</h3>
        <p className="text-gray-400 text-sm mb-6 max-w-md mx-auto">{description}</p>
        {action && action}
      </div>
    )
  }

  // Default empty state
  return (
    <div className={`bg-gray-card border border-gray-divider rounded-2xl p-12 text-center ${className}`}>
      <div className="flex justify-center mb-4">
        <div className="p-4 bg-gray-modal rounded-full">
          {icon || (
            <svg className="w-12 h-12 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
          )}
        </div>
      </div>
      <h3 className="text-xl font-bold text-white mb-2">{title}</h3>
      <p className="text-gray-400 text-sm mb-6 max-w-md mx-auto">{description}</p>
      {action && action}
    </div>
  )
}

