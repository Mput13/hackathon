import { useState, useEffect } from 'react'
import api from '../../services/api'

export default function CreateFunnelModal({ versionId, versionName, isOpen, onClose, onSuccess }) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    steps: [{ type: 'url', url: '', name: '', code: '' }],
    require_sequence: true,
    allow_skip_steps: false
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [goals, setGoals] = useState([])
  const [loadingGoals, setLoadingGoals] = useState(false)

  // Загружаем список целей при открытии модального окна
  useEffect(() => {
    if (isOpen) {
      loadGoals()
    }
  }, [isOpen])

  const loadGoals = async () => {
    setLoadingGoals(true)
    try {
      const goalsList = await api.getGoals()
      console.log('[CreateFunnelModal] Loaded goals:', goalsList)
      if (Array.isArray(goalsList) && goalsList.length > 0) {
        setGoals(goalsList)
      } else {
        console.warn('[CreateFunnelModal] Goals list is empty or not an array')
        setGoals([])
      }
    } catch (err) {
      console.error('Failed to load goals:', err)
      setGoals([])
    } finally {
      setLoadingGoals(false)
    }
  }

  const handleAddStep = () => {
    setFormData(prev => ({
      ...prev,
      steps: [...prev.steps, { type: 'url', url: '', name: '', code: '' }]
    }))
  }

  const handleRemoveStep = (index) => {
    if (formData.steps.length <= 1) return
    setFormData(prev => ({
      ...prev,
      steps: prev.steps.filter((_, i) => i !== index)
    }))
  }

  const handleStepChange = (index, field, value) => {
    setFormData(prev => ({
      ...prev,
      steps: prev.steps.map((step, i) => {
        if (i === index) {
          const updated = { ...step, [field]: value }
          // При смене типа шага очищаем неиспользуемые поля
          if (field === 'type') {
            if (value === 'url') {
              updated.code = ''
            } else {
              updated.url = ''
            }
          }
          // При выборе цели автоматически заполняем название шага
          if (field === 'code' && value) {
            const selectedGoal = goals.find(g => g.code === value)
            if (selectedGoal && !updated.name) {
              updated.name = selectedGoal.name
            }
          }
          return updated
        }
        return step
      })
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      // Валидация
      if (!formData.name.trim()) {
        setError('Название воронки обязательно')
        setLoading(false)
        return
      }

      if (formData.steps.length < 1) {
        setError('Необходимо минимум 1 шаг')
        setLoading(false)
        return
      }

      // Проверяем, что все шаги заполнены
      const incompleteSteps = formData.steps.some((step, index) => {
        if (!step.name?.trim()) {
          setError(`Шаг ${index + 1}: название обязательно`)
          return true
        }
        if (step.type === 'url' && !step.url?.trim()) {
          setError(`Шаг ${index + 1}: URL обязателен для шага типа URL`)
          return true
        }
        if (step.type === 'goal' && !step.code?.trim()) {
          setError(`Шаг ${index + 1}: код цели обязателен для шага типа Goal`)
          return true
        }
        return false
      })
      
      if (incompleteSteps) {
        setLoading(false)
        return
      }

      const funnelData = {
        version: versionId,  // Используем 'version' согласно документации
        name: formData.name.trim(),
        description: formData.description.trim(),
        steps: formData.steps.map(step => {
          const stepData = {
            type: step.type,
            name: step.name.trim()
          }
          if (step.type === 'url') {
            stepData.url = step.url.trim()
          } else if (step.type === 'goal') {
            stepData.code = step.code.trim()
          }
          return stepData
        }),
        require_sequence: formData.require_sequence,
        allow_skip_steps: formData.allow_skip_steps,
        is_preset: false
      }

      await api.createFunnel(funnelData)
      
      // Сброс формы
      setFormData({
        name: '',
        description: '',
        steps: [{ type: 'url', url: '', name: '', code: '' }],
        require_sequence: true,
        allow_skip_steps: false
      })
      
      onSuccess?.()
      onClose()
    } catch (err) {
      console.error('Failed to create funnel:', err)
      setError(err.message || 'Ошибка при создании воронки')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative bg-gray-card border border-gray-divider rounded-2xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto z-10">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white">Создать новую воронку</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-accent-red/20 border border-accent-red/50 rounded-lg text-accent-red text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Version Info */}
          <div className="p-3 bg-gray-modal/50 rounded-lg border border-gray-divider/50">
            <p className="text-sm text-gray-400">Версия:</p>
            <p className="text-white font-semibold">{versionName}</p>
          </div>

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Название воронки *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              className="w-full bg-gray-modal border border-gray-divider rounded-xl py-2 px-4 text-white focus:outline-none focus:border-accent-gold transition-colors"
              placeholder="Например: Заявка на поступление"
              required
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Описание
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              className="w-full bg-gray-modal border border-gray-divider rounded-xl py-2 px-4 text-white focus:outline-none focus:border-accent-gold transition-colors resize-none"
              rows={3}
              placeholder="Описание воронки (необязательно)"
            />
          </div>

          {/* Steps */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <label className="block text-sm font-medium text-gray-400">
                Шаги воронки * (минимум 1)
              </label>
              <button
                type="button"
                onClick={handleAddStep}
                className="px-3 py-1 bg-accent-gold/20 text-accent-gold rounded-lg hover:bg-accent-gold/30 transition-colors text-sm font-semibold"
              >
                + Добавить шаг
              </button>
            </div>
            
            <div className="space-y-3">
              {formData.steps.map((step, index) => (
                <div key={index} className="p-4 bg-gray-modal/50 rounded-xl border border-gray-divider/50">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-semibold text-white">Шаг {index + 1}</span>
                    {formData.steps.length > 1 && (
                      <button
                        type="button"
                        onClick={() => handleRemoveStep(index)}
                        className="text-accent-red hover:text-accent-redLight transition-colors text-sm"
                      >
                        Удалить
                      </button>
                    )}
                  </div>
                  <div className="space-y-2">
                    {/* Step Type */}
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Тип шага *</label>
                      <select
                        value={step.type}
                        onChange={(e) => handleStepChange(index, 'type', e.target.value)}
                        className="w-full bg-gray-back border border-gray-divider rounded-lg py-2 px-3 text-white text-sm focus:outline-none focus:border-accent-gold transition-colors"
                      >
                        <option value="url">URL (посещение страницы)</option>
                        <option value="goal">Goal (достижение цели)</option>
                      </select>
                    </div>

                    {/* Step Name */}
                    <input
                      type="text"
                      value={step.name}
                      onChange={(e) => handleStepChange(index, 'name', e.target.value)}
                      className="w-full bg-gray-back border border-gray-divider rounded-lg py-2 px-3 text-white text-sm focus:outline-none focus:border-accent-gold transition-colors"
                      placeholder="Название шага"
                      required
                    />

                    {/* URL or Goal Code based on type */}
                    {step.type === 'url' ? (
                      <input
                        type="text"
                        value={step.url}
                        onChange={(e) => handleStepChange(index, 'url', e.target.value)}
                        className="w-full bg-gray-back border border-gray-divider rounded-lg py-2 px-3 text-white text-sm focus:outline-none focus:border-accent-gold transition-colors font-mono"
                        placeholder="URL (например: /apply/form или https://priem.mai.ru/bachelor/programs/)"
                        required
                      />
                    ) : (
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Код цели *</label>
                        {loadingGoals ? (
                          <div className="text-sm text-gray-400">Загрузка целей...</div>
                        ) : goals.length === 0 ? (
                          <div className="text-sm text-gray-400">
                            Список целей пуст. Проверьте, что файл goals.yaml существует на сервере.
                          </div>
                        ) : (
                          <select
                            value={step.code || ''}
                            onChange={(e) => {
                              const selectedCode = e.target.value
                              handleStepChange(index, 'code', selectedCode)
                              // Автоматически заполняем название, если оно пустое
                              if (selectedCode) {
                                const selectedGoal = goals.find(g => g.code === selectedCode)
                                if (selectedGoal) {
                                  const currentName = formData.steps[index].name
                                  if (!currentName || currentName.trim() === '') {
                                    handleStepChange(index, 'name', selectedGoal.name)
                                  }
                                }
                              }
                            }}
                            className="w-full bg-gray-back border border-gray-divider rounded-lg py-2 px-3 text-white text-sm focus:outline-none focus:border-accent-gold transition-colors"
                            style={{ appearance: 'none', WebkitAppearance: 'none', MozAppearance: 'none' }}
                            required
                          >
                            <option value="">-- Выберите цель --</option>
                            {goals.map(goal => (
                              <option key={goal.code} value={goal.code}>
                                {goal.name} ({goal.code})
                              </option>
                            ))}
                          </select>
                        )}
                        {step.code && (
                          <div className="mt-1 text-xs text-gray-400">
                            Выбрано: <span className="text-accent-gold">{step.code}</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Options */}
          <div className="space-y-3">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.require_sequence}
                onChange={(e) => setFormData(prev => ({ ...prev, require_sequence: e.target.checked }))}
                className="w-4 h-4 rounded border-gray-divider bg-gray-modal text-accent-gold focus:ring-accent-gold focus:ring-offset-0"
              />
              <span className="text-sm text-gray-300">Требовать последовательность шагов</span>
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.allow_skip_steps}
                onChange={(e) => setFormData(prev => ({ ...prev, allow_skip_steps: e.target.checked }))}
                className="w-4 h-4 rounded border-gray-divider bg-gray-modal text-accent-gold focus:ring-accent-gold focus:ring-offset-0"
              />
              <span className="text-sm text-gray-300">Разрешить пропуск шагов</span>
            </label>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-divider">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2 border border-gray-divider text-gray-400 rounded-xl hover:border-gray-600 hover:bg-gray-modal transition-all duration-300"
              disabled={loading}
            >
              Отмена
            </button>
            <button
              type="submit"
              className="px-6 py-2 bg-accent-gold text-white font-bold rounded-xl hover:bg-accent-goldLight transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={loading}
            >
              {loading ? 'Создание...' : 'Создать воронку'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
