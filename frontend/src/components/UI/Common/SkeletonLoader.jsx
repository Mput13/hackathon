export default function SkeletonLoader({ type = 'card', className = '' }) {
  // Skeleton для метрик
  if (type === 'metric') {
    return (
      <div className={`bg-gray-card/80 backdrop-blur-md border border-gray-divider rounded-2xl p-6 animate-pulse ${className}`}>
        <div className="h-4 bg-gray-modal rounded w-1/3 mb-4"></div>
        <div className="h-8 bg-gray-modal rounded w-1/2 mb-2"></div>
        <div className="h-3 bg-gray-modal rounded w-1/4"></div>
      </div>
    )
  }

  // Skeleton для графиков
  if (type === 'chart') {
    return (
      <div className={`bg-gray-card/80 backdrop-blur-md border border-gray-divider rounded-2xl p-6 animate-pulse ${className}`}>
        <div className="h-5 bg-gray-modal rounded w-1/4 mb-6"></div>
        <div className="h-64 w-full bg-gray-modal rounded"></div>
      </div>
    )
  }

  // Skeleton для списков
  if (type === 'list') {
    return (
      <div className={`space-y-3 ${className}`}>
        {[1, 2, 3].map(i => (
          <div key={i} className="bg-gray-modal/50 rounded-xl p-4 border border-gray-divider animate-pulse">
            <div className="flex items-center gap-4">
              <div className="w-3 h-3 bg-gray-700 rounded-full"></div>
              <div className="flex-1">
                <div className="h-4 bg-gray-700 rounded w-3/4 mb-2"></div>
                <div className="h-3 bg-gray-700 rounded w-1/2"></div>
              </div>
              <div className="h-6 bg-gray-700 rounded w-20"></div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  // Skeleton для таблиц
  if (type === 'table') {
    return (
      <div className={`bg-gray-card border border-gray-divider rounded-2xl p-6 animate-pulse ${className}`}>
        <div className="h-6 bg-gray-modal rounded w-1/4 mb-6"></div>
        <div className="space-y-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="border border-gray-divider rounded-xl p-4">
              <div className="flex items-center gap-4">
                <div className="w-1.5 h-12 bg-gray-700 rounded-full"></div>
                <div className="flex-1">
                  <div className="h-5 bg-gray-700 rounded w-1/3 mb-2"></div>
                  <div className="h-4 bg-gray-700 rounded w-2/3"></div>
                </div>
                <div className="h-6 bg-gray-700 rounded w-20"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  // Default card skeleton
  return (
    <div className={`bg-gray-card/80 backdrop-blur-md border border-gray-divider rounded-2xl p-6 animate-pulse ${className}`}>
      <div className="h-5 bg-gray-modal rounded w-1/3 mb-4"></div>
      <div className="h-32 bg-gray-modal rounded"></div>
    </div>
  )
}

