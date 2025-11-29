import { useState } from 'react'
import FunnelsList from '../components/Funnels/FunnelsList'
import FunnelDetail from '../components/Funnels/FunnelDetail'
import FunnelVersionSelector from '../components/Funnels/FunnelVersionSelector'
import CreateFunnelModal from '../components/Funnels/CreateFunnelModal'
import EmptyState from '../components/UI/Common/EmptyState'

export default function Funnels() {
  const [selectedFunnelId, setSelectedFunnelId] = useState(null)
  const [versionId, setVersionId] = useState(1) // Mock: default to first version
  const [versionName, setVersionName] = useState('v2.0 (2024)') // Mock version name
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  const handleVersionChange = (newVersionId, newVersionName) => {
    setVersionId(newVersionId)
    setVersionName(newVersionName)
    setSelectedFunnelId(null)
  }

  const handleFunnelSelect = (funnelId) => {
    console.log('Opening funnel:', funnelId)
    setSelectedFunnelId(funnelId)
  }

  const handleBackToList = () => {
    setSelectedFunnelId(null)
  }

  const handleFunnelCreated = () => {
    setRefreshKey(prev => prev + 1) // Trigger refresh
  }

  if (selectedFunnelId) {
    return (
      <div className="animate-fadeIn">
        <FunnelDetail 
          funnelId={selectedFunnelId}
          onBack={handleBackToList}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header Section */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white tracking-tight">Воронки конверсии</h1>
        <p className="text-gray-400 text-sm mt-1 tracking-wide">Анализ пути пользователя и показателей конверсии</p>
      </div>
      
      <FunnelVersionSelector 
        selectedVersionId={versionId}
        onVersionChange={handleVersionChange}
      />
      {versionId ? (
        <>
          <FunnelsList 
            key={refreshKey}
            versionId={versionId}
            versionName={versionName}
            onFunnelSelect={handleFunnelSelect}
            onCreateClick={() => setShowCreateModal(true)}
          />
          <CreateFunnelModal
            versionId={versionId}
            versionName={versionName}
            isOpen={showCreateModal}
            onClose={() => setShowCreateModal(false)}
            onSuccess={handleFunnelCreated}
          />
        </>
      ) : (
        <EmptyState 
          type="funnels"
          title="Выберите версию"
          description="Пожалуйста, выберите версию для просмотра воронок конверсии."
        />
      )}
    </div>
  )
}
