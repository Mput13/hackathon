import SpotlightCard from './SpotlightCard'
import CountUp from './CountUp'

export default function MetricCard({ title, value, trend, trendType = "neutral", glowColor = "gold", className = "" }) {
  // Parse value to extract number and suffix (for percentages, seconds, etc.)
  const parseValue = (val) => {
    if (val === 'N/A' || val === null || val === undefined) {
      return { number: 0, suffix: '', isString: true }
    }
    
    if (typeof val === 'string') {
      // Check for percentage
      if (val.includes('%')) {
        const num = parseFloat(val.replace('%', ''))
        return { number: isNaN(num) ? 0 : num, suffix: '%', isString: false }
      }
      // Check for seconds
      if (val.includes('сек')) {
        const num = parseFloat(val.replace(' сек', '').replace('сек', ''))
        return { number: isNaN(num) ? 0 : num, suffix: ' сек', isString: false }
      }
      // If it's a plain string, return as is
      return { number: 0, suffix: val, isString: true }
    }
    
    // If it's a number, return as is
    return { number: typeof val === 'number' ? val : parseFloat(val) || 0, suffix: '', isString: false }
  }

  const parsedValue = parseValue(value)

  const trendColors = {
    positive: "text-accent-emerald",
    negative: "text-accent-red", 
    neutral: "text-gray-400",
    warning: "text-accent-gold"
  }

  const trendIcons = {
    positive: (
      <svg className="w-3 h-3 inline-block mr-1 transform rotate-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 10l7-7m0 0l7 7m-7-7v18" />
      </svg>
    ),
    negative: (
      <svg className="w-3 h-3 inline-block mr-1 transform rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 10l7-7m0 0l7 7m-7-7v18" />
      </svg>
    ), 
    neutral: (
      <svg className="w-3 h-3 inline-block mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M17 8l4 4m0 0l-4 4m4-4H3" />
      </svg>
    ),
    warning: (
      <svg className="w-3 h-3 inline-block mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    )
  }

  // Map internal color names to RGBA for spotlight
  const spotlightColors = {
    gold: "rgba(255, 215, 0, 0.2)",
    red: "rgba(220, 38, 38, 0.2)",
    emerald: "rgba(16, 185, 129, 0.2)"
  }

  const glowStyles = {
    gold: "hover:border-accent-gold/40 hover:shadow-[0_0_15px_-3px_rgba(255,215,0,0.15)]",
    red: "hover:border-accent-red/40 hover:shadow-[0_0_15px_-3px_rgba(220,38,38,0.15)]",
    emerald: "hover:border-accent-emerald/40 hover:shadow-[0_0_15px_-3px_rgba(16,185,129,0.15)]"
  }

  return (
    <SpotlightCard 
      glowColor={spotlightColors[glowColor]} 
      className={`bg-gray-card/80 backdrop-blur-md border border-gray-divider rounded-2xl p-6 transition-all duration-500 ${glowStyles[glowColor]} ${className}`}
    >
      <div className="relative z-10">
        <h3 className="text-gray-400 text-sm font-medium mb-2 uppercase tracking-wider">{title}</h3>
        <div className="flex items-end justify-between">
          <span className="text-3xl font-bold text-white tracking-tight">
            {parsedValue.isString ? (
              <span>{parsedValue.suffix}</span>
            ) : (
              <CountUp end={parsedValue.number} suffix={parsedValue.suffix} />
            )}
          </span>
          {trend && (
            <div className="text-right">
              <div className={`text-sm font-medium flex items-center justify-end ${trendColors[trendType]}`}>
                {trendIcons[trendType]} {trend}
              </div>
            </div>
          )}
        </div>
      </div>
    </SpotlightCard>
  )
}