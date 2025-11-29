import { Doughnut } from 'react-chartjs-2'

export default function GoalTracker() {
  // Mock Data based on goals.yaml
  const goals = [
    { name: "Submitted Applications", current: 145, target: 200, id: "submitted_applications" },
    { name: "IT Master Form", current: 85, target: 100, id: "it_master_form" },
    { name: "Contact Views", current: 450, target: 400, id: "contacts_view" } // Overachieved
  ]

  return (
    <div className="bg-gray-card/80 backdrop-blur-md border border-gray-divider rounded-2xl p-6 shadow-lg hover:border-accent-emerald/40 hover:shadow-[0_0_15px_-3px_rgba(16,185,129,0.15)] transition-all duration-500">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-bold text-white tracking-wide">GOAL TRACKING</h3>
        <span className="text-xs text-accent-emerald font-bold uppercase">High Conversion</span>
      </div>

      <div className="space-y-6">
        {goals.map((goal, index) => {
          const percentage = Math.min((goal.current / goal.target) * 100, 100)
          const isAchieved = goal.current >= goal.target
          
          return (
            <div key={index} className="group">
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-300 font-medium">{goal.name}</span>
                <span className="font-mono text-white">
                  <span className={isAchieved ? "text-accent-emerald" : "text-accent-gold"}>
                    {goal.current}
                  </span>
                  <span className="text-gray-600"> / {goal.target}</span>
                </span>
              </div>
              
              {/* Progress Bar */}
              <div className="h-3 w-full bg-gray-800 rounded-full overflow-hidden border border-gray-divider">
                <div 
                  className={`h-full rounded-full transition-all duration-1000 ease-out relative overflow-hidden ${
                    isAchieved ? 'bg-accent-emerald' : 'bg-accent-gold'
                  }`} 
                  style={{ width: `${percentage}%` }}
                >
                  {/* Shine effect */}
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent w-full -translate-x-full animate-[shimmer_2s_infinite]"></div>
                </div>
              </div>
              
              <div className="flex justify-end mt-1">
                <span className="text-[10px] text-gray-500 font-medium">
                  {percentage.toFixed(0)}% Completed
                </span>
              </div>
            </div>
          )
        })}
      </div>

      <div className="mt-6 pt-4 border-t border-gray-divider">
        <div className="flex items-center justify-between">
          <div className="text-xs text-gray-400">Total Conversions</div>
          <div className="text-xl font-bold text-white">680</div>
        </div>
      </div>
    </div>
  )
}