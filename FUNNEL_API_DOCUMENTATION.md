# Документация API: Создание воронок и управление шагами

Данная документация описывает работу с системой создания воронок конверсии и добавления шагов для интеграции с фронтендом.

## Содержание

1. [Общая архитектура](#общая-архитектура)
2. [Модель данных](#модель-данных)
3. [Создание воронки](#создание-воронки)
4. [Структура шагов](#структура-шагов)
5. [API эндпоинты](#api-эндпоинты)
6. [Примеры запросов](#примеры-запросов)
7. [Валидация](#валидация)
8. [Обработка ошибок](#обработка-ошибок)

---

## Общая архитектура

### Что такое воронка конверсии?

Воронка конверсии — это последовательность шагов, которые пользователь должен пройти для достижения цели (например, заполнение формы заявки, просмотр программы обучения и т.д.).

### Типы воронок

- **Предустановленные (preset)** — системные воронки, созданные автоматически на основе анализа данных. Редактировать нельзя.
- **Кастомные (custom)** — пользовательские воронки, создаваемые вручную через интерфейс или API.

### Типы шагов

Шаг воронки может быть двух типов:
1. **URL шаг** — посещение определенной страницы (например, `/apply/form`)
2. **Goal шаг** — достижение цели из Yandex Metrica (например, клик по кнопке, отправка формы)

---

## Модель данных

### Модель ConversionFunnel

```python
{
    "id": int,                    # Уникальный идентификатор
    "version": int,               # ID версии продукта (ProductVersion)
    "name": str,                  # Название воронки (макс. 200 символов)
    "description": str,           # Описание воронки (опционально)
    "steps": [                    # Массив шагов (JSON)
        {
            "type": "url" | "goal",
            "name": str,          # Название шага
            "url": str,           # Для type="url"
            "code": str           # Для type="goal" - код цели из goals.yaml
        }
    ],
    "require_sequence": bool,     # Требовать последовательность шагов (по умолчанию: true)
    "allow_skip_steps": bool,     # Разрешить пропуск шагов (по умолчанию: false)
    "is_preset": bool,            # Предустановленная воронка (нельзя редактировать)
    "created_at": datetime,
    "updated_at": datetime
}
```

### Ограничения

- Название воронки должно быть уникальным в рамках одной версии продукта
- Воронка должна содержать минимум 1 шаг
- Предустановленные воронки нельзя редактировать или удалять

---

## Создание воронки

### Текущая реализация (HTML форма)

В текущей реализации создание воронки происходит через HTML форму, которая отправляет POST запрос.

**Эндпоинт:** `POST /analytics/funnels/create/`

**Параметры запроса:**
- `version` (int, обязательный) — ID версии продукта
- `name` (str, обязательный) — название воронки
- `description` (str, опционально) — описание
- `require_sequence` (bool, опционально) — требовать последовательность (по умолчанию: true)
- `allow_skip_steps` (bool, опционально) — разрешить пропуск (по умолчанию: false)
- `steps_json` (str, обязательный) — JSON строка с массивом шагов

**Пример запроса (form-data):**
```
version: 1
name: Подача заявки на IT-магистратуру
description: Воронка для отслеживания процесса подачи заявки
require_sequence: true
allow_skip_steps: false
steps_json: [{"type":"goal","code":"it_master_button","name":"Кнопка IT-магистратура"},{"type":"url","url":"/apply/form","name":"Форма заявки"},{"type":"goal","code":"submitted_applications","name":"Отправленные заявки"}]
```

### Логика создания (views_funnels.py)

```python
def funnel_create(request):
    if request.method == 'POST':
        form = CreateFunnelForm(request.POST)
        
        # Получаем шаги из JSON
        steps_json = request.POST.get('steps_json', '[]')
        try:
            steps = json.loads(steps_json)
        except json.JSONDecodeError:
            steps = []
        
        if form.is_valid() and steps:
            funnel = form.save(commit=False)
            funnel.is_preset = False  # Кастомная воронка
            funnel.steps = steps
            funnel.save()
            
            return redirect('funnel_detail', funnel_id=funnel.id)
        else:
            if not steps:
                form.add_error(None, 'Добавьте хотя бы один шаг воронки')
```

**Важные моменты:**
1. Шаги передаются как JSON строка в поле `steps_json`
2. Воронка создается с `is_preset=False` (кастомная)
3. Обязательна валидация: минимум 1 шаг
4. При успехе происходит редирект на страницу просмотра воронки

---

## Структура шагов

### Формат JSON шага

Каждый шаг — это объект со следующей структурой:

#### URL шаг

```json
{
    "type": "url",
    "name": "Форма заявки",
    "url": "/apply/form"
}
```

**Поля:**
- `type` (обязательный): `"url"`
- `name` (обязательный): Название шага для отображения
- `url` (обязательный): URL страницы (может быть относительным или абсолютным)

**Примеры URL:**
- `"/apply/form"` — относительный путь
- `"https://priem.mai.ru/apply/form"` — абсолютный URL
- `"/base/programs/"` — путь с параметрами будет нормализован

#### Goal шаг

```json
{
    "type": "goal",
    "name": "Кнопка IT-магистратура",
    "code": "it_master_button"
}
```

**Поля:**
- `type` (обязательный): `"goal"`
- `name` (обязательный): Название шага для отображения
- `code` (обязательный): Код цели из файла `goals.yaml`

**Доступные коды целей:**

Цели определяются в файле `goals.yaml`. Примеры:
- `it_master_button` — Кнопка IT-магистратура
- `submitted_applications` — Отправленные заявки
- `contacts_view` — Просмотр контактов
- `apply_it_button` — Кнопка "Поступить" IT-магистратура
- и другие...

Для получения полного списка целей используйте API:
```python
GET /analytics/api/goals/  # (требуется реализация)
```

Или загрузите через `GoalParser`:
```python
goal_parser = GoalParser()
goals = goal_parser.get_goals()  # Возвращает список всех целей
```

### Пример полной воронки с шагами

```json
[
    {
        "type": "goal",
        "code": "it_master_button",
        "name": "Кнопка IT-магистратура"
    },
    {
        "type": "url",
        "url": "/apply/form",
        "name": "Форма заявки"
    },
    {
        "type": "goal",
        "code": "submitted_applications",
        "name": "Отправленные заявки"
    }
]
```

### Порядок шагов

Шаги в массиве должны быть упорядочены в том порядке, в котором пользователь должен их пройти. Порядок имеет значение при расчете метрик, если `require_sequence=true`.

---

## API эндпоинты

### Существующие эндпоинты

#### 1. Получить список воронок для версии

**GET** `/analytics/api/funnels/?version={version_id}`

**Параметры:**
- `version` (обязательный) — ID версии продукта

**Ответ:**
```json
{
    "count": 2,
    "results": [
        {
            "id": 1,
            "name": "Поиск рейтингов",
            "description": "Самая популярная воронка",
            "steps_count": 2,
            "steps": [
                {"type": "url", "url": "https://priem.mai.ru/", "name": "Главная страница"},
                {"type": "url", "url": "https://priem.mai.ru/rating/", "name": "Страница рейтингов"}
            ],
            "is_preset": true,
            "has_metrics": true,
            "total_entered": 1000,
            "total_completed": 500,
            "overall_conversion": 50.0,
            "calculated_at": "2024-01-15T10:30:00"
        }
    ]
}
```

#### 2. Получить детальную информацию о воронке

**GET** `/analytics/api/funnels/{funnel_id}/`

**Ответ:**
```json
{
    "funnel": {
        "id": 1,
        "name": "Поиск рейтингов",
        "description": "Самая популярная воронка",
        "version": {
            "id": 1,
            "name": "2024"
        },
        "steps": [
            {"type": "url", "url": "https://priem.mai.ru/", "name": "Главная страница"},
            {"type": "url", "url": "https://priem.mai.ru/rating/", "name": "Страница рейтингов"}
        ],
        "require_sequence": true,
        "allow_skip_steps": false,
        "is_preset": true,
        "metrics": {
            "total_entered": 1000,
            "total_completed": 500,
            "overall_conversion": 50.0,
            "step_metrics": [...]
        },
        "calculated_at": "2024-01-15T10:30:00"
    }
}
```

#### 3. Метрики воронки по когортам

**GET** `/analytics/api/funnels/{funnel_id}/by-cohorts/`

**Ответ:**
```json
{
    "funnel": {
        "id": 1,
        "name": "Поиск рейтингов",
        "version": "2024"
    },
    "overall_metrics": {
        "total_entered": 1000,
        "total_completed": 500,
        "overall_conversion": 50.0
    },
    "cohort_breakdown": {
        "cohort_1": {...},
        "cohort_2": {...}
    },
    "calculated_at": "2024-01-15T10:30:00"
}
```

### Рекомендуемые эндпоинты для реализации

Для полноценной интеграции с фронтендом рекомендуется реализовать следующие REST API эндпоинты:

#### 1. Создание воронки (POST)

**POST** `/analytics/api/funnels/`

**Тело запроса (JSON):**
```json
{
    "version": 1,
    "name": "Подача заявки на IT-магистратуру",
    "description": "Воронка для отслеживания процесса подачи заявки",
    "require_sequence": true,
    "allow_skip_steps": false,
    "steps": [
        {
            "type": "goal",
            "code": "it_master_button",
            "name": "Кнопка IT-магистратура"
        },
        {
            "type": "url",
            "url": "/apply/form",
            "name": "Форма заявки"
        },
        {
            "type": "goal",
            "code": "submitted_applications",
            "name": "Отправленные заявки"
        }
    ]
}
```

**Ответ (успех):**
```json
{
    "success": true,
    "funnel": {
        "id": 5,
        "name": "Подача заявки на IT-магистратуру",
        "description": "Воронка для отслеживания процесса подачи заявки",
        "version": {
            "id": 1,
            "name": "2024"
        },
        "steps": [...],
        "require_sequence": true,
        "allow_skip_steps": false,
        "is_preset": false,
        "created_at": "2024-01-15T12:00:00",
        "updated_at": "2024-01-15T12:00:00"
    }
}
```

**Ответ (ошибка):**
```json
{
    "success": false,
    "errors": {
        "name": ["Это поле обязательно."],
        "steps": ["Добавьте хотя бы один шаг воронки"]
    }
}
```

#### 2. Обновление воронки (PUT/PATCH)

**PUT** `/analytics/api/funnels/{funnel_id}/`

**Тело запроса:** аналогично созданию (все поля опциональны)

**Ограничения:**
- Можно обновлять только кастомные воронки (`is_preset=false`)
- При обновлении шагов удаляются старые метрики (нужен пересчет)

**Ответ:**
```json
{
    "success": true,
    "funnel": {...},
    "message": "Метрики будут пересчитаны при следующем расчете"
}
```

#### 3. Удаление воронки (DELETE)

**DELETE** `/analytics/api/funnels/{funnel_id}/`

**Ответ:**
```json
{
    "success": true,
    "message": "Воронка успешно удалена"
}
```

**Ограничения:**
- Можно удалять только кастомные воронки

#### 4. Получение списка целей (GET)

**GET** `/analytics/api/goals/`

**Ответ:**
```json
{
    "count": 20,
    "goals": [
        {
            "code": "it_master_button",
            "name": "Кнопка IT-магистратура",
            "ym_goal_id": 53631805
        },
        {
            "code": "submitted_applications",
            "name": "Отправленные заявки",
            "ym_goal_id": 39570505
        }
    ]
}
```

---

## Примеры запросов

### JavaScript/TypeScript (Fetch API)

#### Создание воронки

```javascript
async function createFunnel(funnelData) {
    const response = await fetch('/analytics/funnels/create/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCsrfToken() // Django CSRF token
        },
        body: new URLSearchParams({
            version: funnelData.version.toString(),
            name: funnelData.name,
            description: funnelData.description || '',
            require_sequence: funnelData.require_sequence ? 'true' : 'false',
            allow_skip_steps: funnelData.allow_skip_steps ? 'true' : 'false',
            steps_json: JSON.stringify(funnelData.steps)
        })
    });
    
    if (response.redirected) {
        // Успешное создание - редирект на страницу воронки
        const funnelId = extractFunnelIdFromUrl(response.url);
        return { success: true, funnelId };
    } else {
        // Ошибка валидации
        const html = await response.text();
        // Парсим ошибки из HTML формы
        return { success: false, errors: parseFormErrors(html) };
    }
}

// Пример использования
const newFunnel = {
    version: 1,
    name: 'Подача заявки на IT-магистратуру',
    description: 'Воронка для отслеживания процесса подачи заявки',
    require_sequence: true,
    allow_skip_steps: false,
    steps: [
        {
            type: 'goal',
            code: 'it_master_button',
            name: 'Кнопка IT-магистратура'
        },
        {
            type: 'url',
            url: '/apply/form',
            name: 'Форма заявки'
        },
        {
            type: 'goal',
            code: 'submitted_applications',
            name: 'Отправленные заявки'
        }
    ]
};

createFunnel(newFunnel)
    .then(result => {
        if (result.success) {
            console.log('Воронка создана, ID:', result.funnelId);
        } else {
            console.error('Ошибки:', result.errors);
        }
    });
```

#### Получение списка воронок

```javascript
async function getFunnels(versionId) {
    const response = await fetch(`/analytics/api/funnels/?version=${versionId}`);
    const data = await response.json();
    return data;
}

// Использование
getFunnels(1).then(data => {
    console.log(`Найдено воронок: ${data.count}`);
    data.results.forEach(funnel => {
        console.log(`- ${funnel.name} (${funnel.steps_count} шагов)`);
    });
});
```

#### Получение детальной информации о воронке

```javascript
async function getFunnelDetail(funnelId) {
    const response = await fetch(`/analytics/api/funnels/${funnelId}/`);
    const data = await response.json();
    return data.funnel;
}

// Использование
getFunnelDetail(1).then(funnel => {
    console.log('Название:', funnel.name);
    console.log('Шаги:', funnel.steps);
    if (funnel.metrics) {
        console.log('Конверсия:', funnel.metrics.overall_conversion + '%');
    }
});
```

### React пример

```jsx
import React, { useState } from 'react';

function FunnelCreator() {
    const [funnel, setFunnel] = useState({
        version: 1,
        name: '',
        description: '',
        require_sequence: true,
        allow_skip_steps: false,
        steps: []
    });
    
    const [errors, setErrors] = useState({});
    
    const addStep = (step) => {
        setFunnel(prev => ({
            ...prev,
            steps: [...prev.steps, step]
        }));
    };
    
    const removeStep = (index) => {
        setFunnel(prev => ({
            ...prev,
            steps: prev.steps.filter((_, i) => i !== index)
        }));
    };
    
    const handleSubmit = async (e) => {
        e.preventDefault();
        
        if (funnel.steps.length === 0) {
            setErrors({ steps: 'Добавьте хотя бы один шаг' });
            return;
        }
        
        const formData = new FormData();
        formData.append('version', funnel.version);
        formData.append('name', funnel.name);
        formData.append('description', funnel.description);
        formData.append('require_sequence', funnel.require_sequence);
        formData.append('allow_skip_steps', funnel.allow_skip_steps);
        formData.append('steps_json', JSON.stringify(funnel.steps));
        
        // Добавляем CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        try {
            const response = await fetch('/analytics/funnels/create/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                },
                body: formData
            });
            
            if (response.redirected) {
                // Успех - редирект
                window.location.href = response.url;
            } else {
                // Ошибка
                const html = await response.text();
                // Парсим и показываем ошибки
                setErrors(parseErrors(html));
            }
        } catch (error) {
            console.error('Ошибка при создании воронки:', error);
        }
    };
    
    return (
        <form onSubmit={handleSubmit}>
            <input
                type="text"
                value={funnel.name}
                onChange={(e) => setFunnel({...funnel, name: e.target.value})}
                placeholder="Название воронки"
                required
            />
            
            {/* Компонент для добавления шагов */}
            <StepsEditor
                steps={funnel.steps}
                onAdd={addStep}
                onRemove={removeStep}
            />
            
            {errors.steps && <div className="error">{errors.steps}</div>}
            
            <button type="submit">Создать воронку</button>
        </form>
    );
}

function StepsEditor({ steps, onAdd, onRemove }) {
    const [stepType, setStepType] = useState('url');
    const [stepName, setStepName] = useState('');
    const [stepUrl, setStepUrl] = useState('');
    const [stepGoalCode, setStepGoalCode] = useState('');
    
    const handleAdd = () => {
        const step = {
            type: stepType,
            name: stepName
        };
        
        if (stepType === 'url') {
            step.url = stepUrl;
        } else {
            step.code = stepGoalCode;
        }
        
        onAdd(step);
        
        // Сброс полей
        setStepName('');
        setStepUrl('');
        setStepGoalCode('');
    };
    
    return (
        <div>
            <h3>Шаги воронки</h3>
            
            {steps.map((step, index) => (
                <div key={index}>
                    <span>{step.name}</span>
                    <button onClick={() => onRemove(index)}>Удалить</button>
                </div>
            ))}
            
            <div>
                <select value={stepType} onChange={(e) => setStepType(e.target.value)}>
                    <option value="url">URL</option>
                    <option value="goal">Goal</option>
                </select>
                
                <input
                    type="text"
                    value={stepName}
                    onChange={(e) => setStepName(e.target.value)}
                    placeholder="Название шага"
                />
                
                {stepType === 'url' ? (
                    <input
                        type="text"
                        value={stepUrl}
                        onChange={(e) => setStepUrl(e.target.value)}
                        placeholder="/path/to/page"
                    />
                ) : (
                    <input
                        type="text"
                        value={stepGoalCode}
                        onChange={(e) => setStepGoalCode(e.target.value)}
                        placeholder="goal_code"
                    />
                )}
                
                <button type="button" onClick={handleAdd}>Добавить шаг</button>
            </div>
        </div>
    );
}
```

---

## Валидация

### Валидация на уровне формы (CreateFunnelForm)

Форма валидирует следующие поля:

1. **version** — должен существовать в базе данных
2. **name** — обязательное поле, максимум 200 символов
3. **description** — опционально
4. **require_sequence** — булево значение
5. **allow_skip_steps** — булево значение

### Валидация шагов

Шаги валидируются программно в представлении:

1. **Минимум 1 шаг** — воронка должна содержать хотя бы один шаг
2. **Корректный JSON** — `steps_json` должен быть валидным JSON
3. **Структура шага:**
   - Для `type: "url"` — обязательны поля `name` и `url`
   - Для `type: "goal"` — обязательны поля `name` и `code`
4. **Существование цели** — код цели из `goals.yaml` должен существовать (проверяется при создании через команду, но не через форму)

### Уникальность названия

Название воронки должно быть уникальным в рамках одной версии продукта. Django автоматически проверяет это через `unique_together = ('version', 'name')`.

---

## Обработка ошибок

### Типичные ошибки

#### 1. Отсутствие шагов

**Ошибка:** `"Добавьте хотя бы один шаг воронки"`

**Решение:** Убедитесь, что массив `steps` не пустой перед отправкой.

#### 2. Невалидный JSON шагов

**Ошибка:** `JSONDecodeError` при парсинге `steps_json`

**Решение:** Проверьте, что `steps_json` является валидной JSON строкой:
```javascript
try {
    JSON.parse(stepsJson);
} catch (e) {
    console.error('Invalid JSON:', e);
}
```

#### 3. Дубликат названия воронки

**Ошибка:** `"Funnel with this Version and Name already exists."`

**Решение:** Используйте уникальное название для воронки в рамках версии.

#### 4. Попытка редактирования preset воронки

**Ошибка:** `"Предустановленные воронки нельзя редактировать."`

**Решение:** Проверьте `is_preset` перед попыткой редактирования.

#### 5. Несуществующая версия

**Ошибка:** `"Version not found"`

**Решение:** Убедитесь, что переданный `version_id` существует.

### Коды HTTP статусов

- `200 OK` — успешный запрос
- `400 Bad Request` — ошибка валидации
- `404 Not Found` — воронка/версия не найдена
- `403 Forbidden` — попытка редактирования preset воронки
- `500 Internal Server Error` — серверная ошибка

---

## Рекомендации по реализации

### 1. Создание REST API эндпоинтов

Для удобной интеграции рекомендуется добавить REST API эндпоинты:

```python
# analytics/views_funnels.py

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

@csrf_exempt
@require_http_methods(["POST"])
def api_funnel_create(request):
    """REST API: создание воронки"""
    try:
        data = json.loads(request.body)
        
        # Валидация
        if not data.get('version'):
            return JsonResponse({'error': 'version is required'}, status=400)
        if not data.get('name'):
            return JsonResponse({'error': 'name is required'}, status=400)
        if not data.get('steps') or len(data['steps']) == 0:
            return JsonResponse({'error': 'At least one step is required'}, status=400)
        
        # Проверка версии
        try:
            version = ProductVersion.objects.get(id=data['version'])
        except ProductVersion.DoesNotExist:
            return JsonResponse({'error': 'Version not found'}, status=404)
        
        # Проверка уникальности названия
        if ConversionFunnel.objects.filter(version=version, name=data['name']).exists():
            return JsonResponse({'error': 'Funnel with this name already exists'}, status=400)
        
        # Создание воронки
        funnel = ConversionFunnel.objects.create(
            version=version,
            name=data['name'],
            description=data.get('description', ''),
            steps=data['steps'],
            require_sequence=data.get('require_sequence', True),
            allow_skip_steps=data.get('allow_skip_steps', False),
            is_preset=False
        )
        
        return JsonResponse({
            'success': True,
            'funnel': {
                'id': funnel.id,
                'name': funnel.name,
                'description': funnel.description,
                'steps': funnel.steps,
                'require_sequence': funnel.require_sequence,
                'allow_skip_steps': funnel.allow_skip_steps,
                'is_preset': funnel.is_preset,
                'created_at': funnel.created_at.isoformat(),
                'updated_at': funnel.updated_at.isoformat()
            }
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
```

### 2. Добавление в urls.py

```python
# analytics/urls.py

urlpatterns = [
    # ... существующие маршруты ...
    path('api/funnels/', views.api_funnels, name='api_funnels'),
    path('api/funnels/create/', views.api_funnel_create, name='api_funnel_create'),  # Новый
    path('api/funnels/<int:funnel_id>/', views.api_funnel_detail, name='api_funnel_detail'),
    path('api/funnels/<int:funnel_id>/update/', views.api_funnel_update, name='api_funnel_update'),  # Новый
    path('api/funnels/<int:funnel_id>/delete/', views.api_funnel_delete, name='api_funnel_delete'),  # Новый
]
```

### 3. Получение списка целей

```python
def api_goals(request):
    """JSON: список всех доступных целей"""
    goal_parser = GoalParser()
    goals = goal_parser.get_goals()
    
    results = []
    for goal in goals:
        results.append({
            'code': goal.get('code'),
            'name': goal.get('name'),
            'ym_goal_id': goal.get('ym_goal_id')
        })
    
    return JsonResponse({'count': len(results), 'goals': results})
```

---

## Чек-лист для фронтенда

- [ ] Получение списка версий продукта (`/api/versions/`)
- [ ] Получение списка доступных целей (требуется реализация `/api/goals/`)
- [ ] Интерфейс для добавления/удаления шагов воронки
- [ ] Валидация шагов на клиенте (минимум 1 шаг, корректные поля)
- [ ] Отправка формы создания воронки
- [ ] Обработка ошибок валидации
- [ ] Отображение списка созданных воронок
- [ ] Редактирование кастомных воронок
- [ ] Удаление кастомных воронок (с подтверждением)
- [ ] Проверка `is_preset` перед редактированием/удалением

---

## Дополнительная информация

### Нормализация URL

URL шагов нормализуются при сохранении:
- Удаляются фрагменты (`#section`)
- Очищаются query параметры (опционально)
- Приводится к единому формату

См. функцию `normalize_url()` в `analytics/funnel_utils.py`.

### Расчет метрик

После создания воронки метрики не рассчитываются автоматически. Для расчета используйте команду:

```bash
python manage.py calculate_funnels --version 2024
```

Или через API (требуется реализация).

### Связь с когортами

Воронки можно анализировать по когортам пользователей. Для этого:

1. Создайте когорту пользователей
2. Рассчитайте метрики воронки с разбивкой по когортам:
   ```bash
   python manage.py calculate_funnels --version 2024 --by-cohorts
   ```
3. Получите метрики через API:
   ```
   GET /analytics/api/funnels/{funnel_id}/by-cohorts/
   ```

---

## Контакты и поддержка

При возникновении вопросов или проблем обращайтесь к разработчикам бэкенда.

**Файлы для изучения:**
- `analytics/models.py` — модель данных
- `analytics/views_funnels.py` — логика создания/редактирования
- `analytics/forms.py` — формы валидации
- `analytics/funnel_utils.py` — утилиты для работы с воронками
- `goals.yaml` — конфигурация целей
