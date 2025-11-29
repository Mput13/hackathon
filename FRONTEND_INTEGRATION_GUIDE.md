# Руководство по интеграции фронтенда: Метрики и компоненты сравнения

## 📋 Содержание
1. [Обзор архитектуры](#обзор-архитектуры)
2. [API Endpoints для сравнения](#api-endpoints-для-сравнения)
3. [Структура данных метрик](#структура-данных-метрик)
4. [Компоненты сравнения версий](#компоненты-сравнения-версий)
5. [Примеры интеграции](#примеры-интеграции)

---

## Обзор архитектуры

### Текущая реализация (Django Templates)
Система использует Django-шаблоны для отображения, но также предоставляет полноценные JSON API endpoints для интеграции с современным фронтендом (React, Vue, Angular и т.д.).

### Архитектура данных
```
Backend (Django) → API Endpoints (JSON) → Frontend (React/Vue/Angular)
```

---

## API Endpoints для сравнения

### 1. Получение списка версий

**GET** `/analytics/api/versions/`

**Ответ:**
```json
{
  "versions": [
    {
      "id": 1,
      "name": "v1.0 (2022)",
      "release_date": "2022-01-01",
      "is_active": true
    },
    {
      "id": 2,
      "name": "v2.0 (2024)",
      "release_date": "2024-01-01",
      "is_active": true
    }
  ]
}
```

### 2. Сравнение двух версий (основной endpoint)

**GET** `/analytics/api/compare/?v1={version_id}&v2={version_id}`

**Параметры:**
- `v1` (обязательный) - ID первой версии для сравнения
- `v2` (обязательный) - ID второй версии для сравнения

**Ответ:**
```json
{
  "comparison": {
    "v1": {
      "id": 1,
      "name": "v1.0 (2022)"
    },
    "v2": {
      "id": 2,
      "name": "v2.0 (2024)"
    },
    
    // Основные метрики разницы
    "visits_diff": 500,           // Разница в количестве визитов
    "bounce_diff": -5.2,         // Разница в bounce rate (процентные пункты)
    "duration_diff": 30.5,        // Разница в средней длительности (секунды)
    
    // Детальные статистики по версиям
    "stats_v1": {
      "visits": 3000,
      "bounce": 45.2,             // Процент
      "duration": 245.5           // Секунды
    },
    "stats_v2": {
      "visits": 3500,
      "bounce": 40.0,
      "duration": 276.0
    },
    
    // AI-анализ сравнения (текстовая сводка)
    "ai_analysis": "Резюме: Версия v2.0 показывает улучшение...",
    
    // Разбивка по устройствам
    "device_split": [
      {
        "device": "desktop",
        "visits_v1": 1500,
        "visits_v2": 1800,
        "share_v1": 50.0,         // Процент от общего трафика
        "share_v2": 51.4,
        "share_diff": 1.4,        // Изменение доли (процентные пункты)
        "bounce_v1": 40.0,
        "bounce_v2": 35.0,
        "bounce_diff": -5.0,      // Улучшение (отрицательное = хорошо)
        "duration_v1": 300.0,
        "duration_v2": 320.0,
        "duration_diff": 20.0
      },
      {
        "device": "mobile",
        "visits_v1": 1200,
        "visits_v2": 1400,
        "share_v1": 40.0,
        "share_v2": 40.0,
        "share_diff": 0.0,
        "bounce_v1": 50.0,
        "bounce_v2": 45.0,
        "bounce_diff": -5.0,
        "duration_v1": 180.0,
        "duration_v2": 200.0,
        "duration_diff": 20.0
      }
    ],
    
    // Разбивка по браузерам (топ-5)
    "browser_split": [
      {
        "browser": "Chrome",
        "visits_v1": 2000,
        "visits_v2": 2400,
        "share_v1": 66.7,
        "share_v2": 68.6,
        "share_diff": 1.9,
        "bounce_v1": 42.0,
        "bounce_v2": 38.0,
        "bounce_diff": -4.0,
        "duration_v1": 250.0,
        "duration_v2": 280.0,
        "duration_diff": 30.0
      }
    ],
    
    // Разбивка по операционным системам (топ-5)
    "os_split": [
      {
        "os": "Windows",
        "visits_v1": 1800,
        "visits_v2": 2100,
        "share_v1": 60.0,
        "share_v2": 60.0,
        "share_diff": 0.0,
        "bounce_v1": 43.0,
        "bounce_v2": 39.0,
        "bounce_diff": -4.0,
        "duration_v1": 260.0,
        "duration_v2": 290.0,
        "duration_diff": 30.0
      }
    ],
    
    // Алерты (критические изменения)
    "alerts": [
      {
        "type": "NEW_CRITICAL",
        "message": "Обнаружена новая критическая проблема на странице...",
        "url": "https://example.com/page",
        "severity": "critical"
      },
      {
        "type": "EXIT_INCREASE",
        "message": "Exit rate вырос на 15 p.p. на Главной странице",
        "url": "https://example.com/",
        "severity": "warning"
      }
    ],
    
    // Сравнение UX Issues
    "issues_diff": [
      {
        "id": 1,
        "issue_type": "HIGH_BOUNCE",
        "severity": "CRITICAL",
        "location_url": "https://example.com/page",
        "location_readable": "Главная страница",
        "impact_score": 8.5,
        "affected_sessions": 150,
        "status": "new",              // new, worse, improved, stable, resolved
        "impact_diff": 8.5,           // Изменение impact score
        "trend": "worse",
        "priority": "HIGH",
        "recommended_specialists": ["UX Designer", "Frontend Developer"],
        "detected_version_name": "v2.0 (2024)"
      },
      {
        "id": 2,
        "issue_type": "SLOW_PAGE",
        "severity": "WARNING",
        "location_url": "https://example.com/slow",
        "location_readable": "Страница загрузки",
        "impact_score": 5.0,
        "affected_sessions": 80,
        "status": "improved",
        "impact_diff": -2.0,
        "trend": "improved",
        "priority": "MEDIUM",
        "recommended_specialists": ["Backend Developer"],
        "detected_version_name": "v2.0 (2024)"
      }
    ],
    
    // Сравнение страниц
    "pages_diff": [
      {
        "status": "changed",          // new, removed, changed, stable
        "exit_diff": 5.2,             // Изменение exit rate (процентные пункты)
        "time_diff": 15.0,            // Изменение времени на странице (секунды)
        "readable": "Главная страница",
        "v1": {
          "url": "https://example.com/",
          "page_title": "Главная",
          "exit_rate": 45.0,
          "avg_time_on_page": 120.0,
          "avg_scroll_depth": 65.0,
          "total_views": 1000,
          "unique_visitors": 800,
          "dominant_cohort": "Активные исследователи",
          "dominant_device": "desktop"
        },
        "v2": {
          "url": "https://example.com/",
          "page_title": "Главная",
          "exit_rate": 50.2,
          "avg_time_on_page": 135.0,
          "avg_scroll_depth": 70.0,
          "total_views": 1200,
          "unique_visitors": 950,
          "dominant_cohort": "Активные исследователи",
          "dominant_device": "desktop"
        }
      }
    ],
    
    // Сравнение когорт (сегментов аудитории)
    "cohorts_diff": [
      {
        "name": "Активные исследователи",
        "status": "changed",          // new, removed, changed
        "v1": {
          "name": "Активные исследователи",
          "percentage": 35.5,         // Процент от общей аудитории
          "avg_bounce_rate": 25.0,
          "avg_duration": 320.0,
          "users_count": 1065,
          "metrics": {
            "depth": 4.2,
            "top_goals": "Поиск рейтингов, Просмотр программ"
          },
          "conversion_rates": {
            "funnel_1": 60.0,
            "funnel_2": 45.0
          }
        },
        "v2": {
          "name": "Активные исследователи",
          "percentage": 38.0,
          "avg_bounce_rate": 22.0,
          "avg_duration": 350.0,
          "users_count": 1330,
          "metrics": {
            "depth": 4.5,
            "top_goals": "Поиск рейтингов, Просмотр программ, Подача заявления"
          },
          "conversion_rates": {
            "funnel_1": 65.0,
            "funnel_2": 50.0
          }
        }
      }
    ],
    
    // Когорты для каждой версии (детальная информация)
    "v1_cohorts": [
      {
        "name": "Активные исследователи",
        "percentage": 35.5,
        "avg_bounce_rate": 25.0,
        "avg_duration": 320.0,
        "users_count": 1065,
        "metrics": {
          "depth": 4.2,
          "top_goals": "Поиск рейтингов, Просмотр программ"
        },
        "conversion_rates": {
          "funnel_1": 60.0,
          "funnel_2": 45.0
        }
      }
    ],
    "v2_cohorts": [
      {
        "name": "Активные исследователи",
        "percentage": 38.0,
        "avg_bounce_rate": 22.0,
        "avg_duration": 350.0,
        "users_count": 1330,
        "metrics": {
          "depth": 4.5,
          "top_goals": "Поиск рейтингов, Просмотр программ, Подача заявления"
        },
        "conversion_rates": {
          "funnel_1": 65.0,
          "funnel_2": 50.0
        }
      }
    ]
  }
}
```

---

## Структура данных метрик

### Основные метрики (Key Metrics)

#### 1. Visits (Визиты)
- **Тип**: `integer`
- **Описание**: Общее количество сессий/визитов
- **Единица измерения**: Количество сессий
- **Интерпретация**: Больше = лучше (больше трафика)

#### 2. Bounce Rate (Показатель отказов)
- **Тип**: `float`
- **Описание**: Процент пользователей, покинувших сайт после просмотра одной страницы
- **Единица измерения**: Процент (0-100)
- **Интерпретация**: Меньше = лучше (меньше отказов)
- **Формула**: `(bounced_sessions / total_sessions) * 100`

#### 3. Duration (Длительность сессии)
- **Тип**: `float`
- **Описание**: Средняя длительность сессии
- **Единица измерения**: Секунды
- **Интерпретация**: Больше = лучше (пользователи дольше на сайте), но контекстно-зависимо

### Метрики разницы (Delta Metrics)

Все метрики разницы вычисляются как: `v2_value - v1_value`

#### Интерпретация:
- **visits_diff > 0**: Рост трафика (хорошо)
- **bounce_diff < 0**: Улучшение (меньше отказов)
- **bounce_diff > 0**: Ухудшение (больше отказов)
- **duration_diff > 0**: Увеличение времени (обычно хорошо, но зависит от контекста)

### Метрики разбивки (Split Metrics)

#### Device Split (Разбивка по устройствам)
```typescript
interface DeviceSplit {
  device: 'desktop' | 'mobile' | 'tablet' | 'tv' | 'unknown';
  visits_v1: number;
  visits_v2: number;
  share_v1: number;        // Процент от общего трафика v1
  share_v2: number;        // Процент от общего трафика v2
  share_diff: number;      // Изменение доли (процентные пункты)
  bounce_v1: number;       // Bounce rate для v1 (%)
  bounce_v2: number;       // Bounce rate для v2 (%)
  bounce_diff: number;     // Изменение bounce rate (процентные пункты)
  duration_v1: number;    // Средняя длительность для v1 (секунды)
  duration_v2: number;    // Средняя длительность для v2 (секунды)
  duration_diff: number;   // Изменение длительности (секунды)
}
```

#### Browser Split (Разбивка по браузерам)
Аналогичная структура, но поле `browser` вместо `device`:
```typescript
interface BrowserSplit {
  browser: string;  // 'Chrome', 'Firefox', 'Safari', etc.
  // ... остальные поля как в DeviceSplit
}
```

#### OS Split (Разбивка по ОС)
Аналогичная структура, но поле `os` вместо `device`:
```typescript
interface OSSplit {
  os: string;  // 'Windows', 'macOS', 'Linux', 'Android', 'iOS', etc.
  // ... остальные поля как в DeviceSplit
}
```

### Метрики Issues (Проблемы UX)

```typescript
interface IssueDiff {
  id: number;
  issue_type: 'HIGH_BOUNCE' | 'SLOW_PAGE' | 'HIGH_EXIT' | 'LOW_ENGAGEMENT' | 'ROUTING_ISSUE';
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  location_url: string;
  location_readable: string;  // Человекочитаемое название страницы
  impact_score: number;       // 0-10, чем выше, тем серьезнее
  affected_sessions: number;  // Количество затронутых сессий
  status: 'new' | 'worse' | 'improved' | 'stable' | 'resolved';
  impact_diff: number;       // Изменение impact score
  trend: 'new' | 'worse' | 'improved' | 'stable';
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  recommended_specialists: string[];  // ['UX Designer', 'Frontend Developer']
  detected_version_name: string;
}
```

**Статусы Issues:**
- `new` - Проблема появилась в v2
- `worse` - Проблема существовала в v1, но ухудшилась в v2 (impact_diff > 1)
- `improved` - Проблема существовала в v1, но улучшилась в v2 (impact_diff < -1)
- `stable` - Проблема без значительных изменений (-1 <= impact_diff <= 1)
- `resolved` - Проблема была в v1, но исчезла в v2

### Метрики страниц (Pages)

```typescript
interface PageDiff {
  status: 'new' | 'removed' | 'changed' | 'stable';
  exit_diff: number;        // Изменение exit rate (процентные пункты)
  time_diff: number;        // Изменение времени на странице (секунды)
  readable: string;         // Человекочитаемое название
  v1: PageMetrics | null;
  v2: PageMetrics | null;
}

interface PageMetrics {
  url: string;
  page_title: string;
  exit_rate: number;        // Процент выходов со страницы
  avg_time_on_page: number; // Среднее время на странице (секунды)
  avg_scroll_depth: number; // Средняя глубина прокрутки (%)
  total_views: number;
  unique_visitors: number;
  dominant_cohort: string;  // Доминирующая когорта
  dominant_device: string;  // Доминирующее устройство
}
```

**Статусы страниц:**
- `new` - Страница появилась в v2
- `removed` - Страница была в v1, но удалена в v2
- `changed` - Значительные изменения (|exit_diff| > 5 или |time_diff| > 5)
- `stable` - Без значительных изменений

### Метрики когорт (Cohorts)

```typescript
interface CohortDiff {
  name: string;
  status: 'new' | 'removed' | 'changed';
  v1: CohortMetrics | null;
  v2: CohortMetrics | null;
}

interface CohortMetrics {
  name: string;
  percentage: number;           // Процент от общей аудитории
  avg_bounce_rate: number;      // Средний bounce rate (%)
  avg_duration: number;         // Средняя длительность (секунды)
  users_count: number;          // Количество пользователей
  metrics: {
    depth: number;               // Средняя глубина просмотра (страниц)
    top_goals?: string;         // Топ целей/воронок
  };
  conversion_rates: {
    [funnel_id: string]: number; // Конверсия по воронкам (%)
  };
}
```

---

## Компоненты сравнения версий

### 1. Селектор версий (Version Selector)

**Функциональность:**
- Выбор двух версий для сравнения
- Автоматический выбор последних двух версий, если не указаны

**UI Компонент:**
```tsx
// React пример
interface VersionSelectorProps {
  versions: Version[];
  selectedV1: number | null;
  selectedV2: number | null;
  onCompare: (v1: number, v2: number) => void;
}

const VersionSelector: React.FC<VersionSelectorProps> = ({
  versions,
  selectedV1,
  selectedV2,
  onCompare
}) => {
  const [v1, setV1] = useState(selectedV1);
  const [v2, setV2] = useState(selectedV2);

  return (
    <div className="version-selector">
      <select value={v1 || ''} onChange={(e) => setV1(Number(e.target.value))}>
        {versions.map(v => (
          <option key={v.id} value={v.id}>{v.name}</option>
        ))}
      </select>
      <span>VS</span>
      <select value={v2 || ''} onChange={(e) => setV2(Number(e.target.value))}>
        {versions.map(v => (
          <option key={v.id} value={v.id}>{v.name}</option>
        ))}
      </select>
      <button onClick={() => onCompare(v1!, v2!)}>Сравнить</button>
    </div>
  );
};
```

### 2. Карточки основных метрик (Key Metrics Cards)

**Отображение:**
- 3 карточки: Bounce Rate Change, Avg Duration Change, Traffic Volume
- Цветовая индикация: зеленый = улучшение, красный = ухудшение

**Компонент:**
```tsx
interface MetricCardProps {
  title: string;
  value: number;
  unit: string;
  isPositive: boolean;  // true = улучшение
  hint?: string;
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  isPositive,
  hint
}) => {
  const colorClass = isPositive ? 'text-green-500' : 'text-red-500';
  const sign = value > 0 ? '+' : '';
  
  return (
    <div className="metric-card">
      <p className="text-sm text-gray-500">{title}</p>
      <p className={`text-4xl font-bold ${colorClass}`}>
        {sign}{value}{unit}
      </p>
      {hint && <p className="text-xs text-gray-400">{hint}</p>}
    </div>
  );
};

// Использование:
<MetricCard
  title="Bounce Rate Change"
  value={comparison.bounce_diff}
  unit="%"
  isPositive={comparison.bounce_diff < 0}
  hint="Lower is better"
/>
```

### 3. AI-анализ (AI Analysis Summary)

**Отображение:**
- Блок с градиентным фоном
- Текстовая сводка от AI
- Иконка AI

**Компонент:**
```tsx
interface AIAnalysisProps {
  analysis: string | null;
}

const AIAnalysis: React.FC<AIAnalysisProps> = ({ analysis }) => {
  if (!analysis) return null;
  
  return (
    <div className="ai-analysis bg-gradient-to-r from-indigo-50 to-purple-50">
      <div className="flex items-start">
        <AIIcon />
        <div>
          <h3>🤖 AI-анализ сравнения</h3>
          <div className="whitespace-pre-line">{analysis}</div>
        </div>
      </div>
    </div>
  );
};
```

### 4. Таблицы разбивки (Split Tables)

**Компоненты:**
- Device Split Table
- Browser Split Table
- OS Split Table

**Структура таблицы:**
```
| Категория | Share Δ (p.p.) | Bounce Δ (p.p.) | Duration Δ (s) |
|-----------|----------------|-----------------|----------------|
| Desktop   | +1.4 (50%→51%) | -5.0 (40%→35%)  | +20.0 (300→320)|
```

**Компонент:**
```tsx
interface SplitTableProps {
  title: string;
  data: (DeviceSplit | BrowserSplit | OSSplit)[];
  categoryField: 'device' | 'browser' | 'os';
}

const SplitTable: React.FC<SplitTableProps> = ({ title, data, categoryField }) => {
  return (
    <div className="split-table">
      <h4>{title}</h4>
      <table>
        <thead>
          <tr>
            <th>{categoryField}</th>
            <th>Share Δ (p.p.)</th>
            <th>Bounce Δ (p.p.)</th>
            <th>Duration Δ (s)</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, idx) => (
            <tr key={idx}>
              <td>{row[categoryField]}</td>
              <td className={getColorClass(row.share_diff, true)}>
                {formatDelta(row.share_diff)} ({row.share_v1}% → {row.share_v2}%)
              </td>
              <td className={getColorClass(row.bounce_diff, false)}>
                {formatDelta(row.bounce_diff)} ({row.bounce_v1}% → {row.bounce_v2}%)
              </td>
              <td className={getColorClass(row.duration_diff, true)}>
                {formatDelta(row.duration_diff)} ({row.duration_v1}s → {row.duration_v2}s)
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

function getColorClass(value: number, isPositiveGood: boolean): string {
  if (value === 0) return '';
  const isGood = isPositiveGood ? value > 0 : value < 0;
  return isGood ? 'text-green-600' : 'text-red-600';
}

function formatDelta(value: number): string {
  return value > 0 ? `+${value.toFixed(1)}` : value.toFixed(1);
}
```

### 5. Алерты (Alerts)

**Типы алертов:**
- `NEW_CRITICAL` - Новая критическая проблема
- `EXIT_INCREASE` - Рост exit rate

**Компонент:**
```tsx
interface Alert {
  type: string;
  message: string;
  url?: string;
  severity: 'critical' | 'warning';
}

const AlertsList: React.FC<{ alerts: Alert[] }> = ({ alerts }) => {
  return (
    <div className="alerts-list">
      <h4>Alerts</h4>
      {alerts.map((alert, idx) => (
        <div
          key={idx}
          className={`alert ${
            alert.severity === 'critical'
              ? 'bg-red-50 border-red-200 text-red-700'
              : 'bg-amber-50 border-amber-200 text-amber-700'
          }`}
        >
          <div className="font-semibold">{alert.type}</div>
          <div>{alert.message}</div>
          {alert.url && <div className="text-xs">{alert.url}</div>}
        </div>
      ))}
    </div>
  );
};
```

### 6. Таблица Issues (Issues Diff Table)

**Компонент:**
```tsx
interface IssuesTableProps {
  issues: IssueDiff[];
}

const IssuesTable: React.FC<IssuesTableProps> = ({ issues }) => {
  const getStatusBadge = (status: string) => {
    const styles = {
      new: 'bg-green-100 text-green-700',
      resolved: 'bg-gray-100 text-gray-600',
      worse: 'bg-red-100 text-red-700',
      improved: 'bg-blue-100 text-blue-700',
      stable: 'bg-yellow-50 text-yellow-700'
    };
    return styles[status] || '';
  };

  return (
    <table>
      <thead>
        <tr>
          <th>Type</th>
          <th>Location</th>
          <th>Status</th>
          <th>Impact Δ</th>
          <th>Impact</th>
        </tr>
      </thead>
      <tbody>
        {issues.map(issue => (
          <tr key={issue.id}>
            <td>{issue.issue_type}</td>
            <td>
              <div>{issue.location_readable}</div>
              <div className="text-xs text-gray-400">{issue.location_url}</div>
            </td>
            <td>
              <span className={`badge ${getStatusBadge(issue.status)}`}>
                {issue.status}
              </span>
            </td>
            <td className={issue.impact_diff > 0 ? 'text-red-600' : 'text-green-600'}>
              {issue.impact_diff > 0 ? '+' : ''}{issue.impact_diff}
            </td>
            <td>{issue.impact_score.toFixed(2)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};
```

### 7. Таблица страниц (Pages Diff Table)

**Компонент:**
```tsx
const PagesTable: React.FC<{ pages: PageDiff[] }> = ({ pages }) => {
  return (
    <table>
      <thead>
        <tr>
          <th>Page</th>
          <th>Status</th>
          <th>Exit Δ (p.p.)</th>
          <th>Time Δ (s)</th>
        </tr>
      </thead>
      <tbody>
        {pages.map((page, idx) => (
          <tr key={idx}>
            <td>
              <div>{page.readable}</div>
              <div className="text-xs text-gray-400">
                {page.v2?.url || page.v1?.url}
              </div>
            </td>
            <td>
              <span className={`badge ${getStatusBadge(page.status)}`}>
                {page.status}
              </span>
            </td>
            <td className={page.exit_diff > 0 ? 'text-red-600' : 'text-green-600'}>
              {page.exit_diff > 0 ? '+' : ''}{page.exit_diff}
            </td>
            <td className={page.time_diff > 0 ? 'text-green-600' : 'text-red-600'}>
              {page.time_diff > 0 ? '+' : ''}{page.time_diff}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};
```

### 8. Когорты (Cohorts)

**Компонент:**
```tsx
const CohortsList: React.FC<{ cohorts: CohortDiff[] }> = ({ cohorts }) => {
  return (
    <div className="cohorts-list">
      {cohorts.map((cohort, idx) => (
        <div key={idx} className={`cohort-card ${getStatusClass(cohort.status)}`}>
          <div>
            <p className="font-semibold">{cohort.name}</p>
            <p className="text-xs text-gray-500">
              {cohort.v1 && `v1: ${cohort.v1.percentage.toFixed(2)}%`}
              {cohort.v2 && ` v2: ${cohort.v2.percentage.toFixed(2)}%`}
            </p>
          </div>
          <span className={`badge ${getStatusBadge(cohort.status)}`}>
            {cohort.status}
          </span>
        </div>
      ))}
    </div>
  );
};
```

### 9. Детальный вид по версиям (Detailed Split View)

**Компонент для отображения когорт каждой версии:**
```tsx
const DetailedCohortsView: React.FC<{
  v1Cohorts: CohortMetrics[];
  v2Cohorts: CohortMetrics[];
  v1Name: string;
  v2Name: string;
}> = ({ v1Cohorts, v2Cohorts, v1Name, v2Name }) => {
  return (
    <div className="grid grid-cols-2 gap-6">
      {/* V1 Column */}
      <div className="bg-gray-50 p-6 rounded-xl">
        <h3>{v1Name}</h3>
        <div className="space-y-4">
          <div className="bg-white p-4 rounded-lg">
            <p>Total Visits</p>
            <p className="text-xl font-bold">{/* stats_v1.visits */}</p>
          </div>
          <div>
            <h4>Audience Segments (AI)</h4>
            {v1Cohorts.map((cohort, idx) => (
              <div key={idx} className="cohort-card">
                <div className="flex justify-between">
                  <h5>{cohort.name}</h5>
                  <span>{cohort.percentage.toFixed(2)}%</span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <span>Bounce</span>
                    <span>{cohort.avg_bounce_rate.toFixed(1)}%</span>
                  </div>
                  <div>
                    <span>Time</span>
                    <span>{cohort.avg_duration.toFixed(0)}s</span>
                  </div>
                  <div>
                    <span>Depth</span>
                    <span>{cohort.metrics.depth}</span>
                  </div>
                </div>
                {cohort.metrics.top_goals && (
                  <div>
                    <span>Top Goals:</span> {cohort.metrics.top_goals}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* V2 Column */}
      <div className="bg-indigo-50 p-6 rounded-xl">
        {/* Аналогичная структура для v2 */}
      </div>
    </div>
  );
};
```

### 10. Топ путей (Top Paths)

**Компонент:**
```tsx
interface Path {
  path: string;           // "Page A -> Page B"
  steps: string[];        // ["Page A", "Page B"]
  count: number;          // Количество прохождений
  unique_users: number;   // Уникальные пользователи
}

const TopPaths: React.FC<{
  v1Paths: Path[];
  v2Paths: Path[];
  v1Name: string;
  v2Name: string;
}> = ({ v1Paths, v2Paths, v1Name, v2Name }) => {
  return (
    <div className="grid grid-cols-2 gap-6">
      <div>
        <h5>{v1Name}</h5>
        {v1Paths.map((path, idx) => (
          <div key={idx} className="path-card">
            <div className="text-indigo-600 font-medium">{path.path}</div>
            <div className="text-xs text-gray-500">
              Count: {path.count}, Users: {path.unique_users}
            </div>
          </div>
        ))}
      </div>
      <div>
        <h5>{v2Name}</h5>
        {v2Paths.map((path, idx) => (
          <div key={idx} className="path-card">
            <div className="text-indigo-700 font-medium">{path.path}</div>
            <div className="text-xs text-gray-600">
              Count: {path.count}, Users: {path.unique_users}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

---

## Примеры интеграции

### React + TypeScript

```tsx
// types.ts
export interface ComparisonData {
  v1: { id: number; name: string };
  v2: { id: number; name: string };
  visits_diff: number;
  bounce_diff: number;
  duration_diff: number;
  stats_v1: { visits: number; bounce: number; duration: number };
  stats_v2: { visits: number; bounce: number; duration: number };
  ai_analysis: string | null;
  device_split: DeviceSplit[];
  browser_split: BrowserSplit[];
  os_split: OSSplit[];
  alerts: Alert[];
  issues_diff: IssueDiff[];
  pages_diff: PageDiff[];
  cohorts_diff: CohortDiff[];
  v1_cohorts: CohortMetrics[];
  v2_cohorts: CohortMetrics[];
}

// api.ts
export const fetchComparison = async (
  v1: number,
  v2: number
): Promise<ComparisonData> => {
  const response = await fetch(
    `/analytics/api/compare/?v1=${v1}&v2=${v2}`
  );
  const data = await response.json();
  return data.comparison;
};

// ComparisonPage.tsx
import React, { useState, useEffect } from 'react';
import { fetchComparison } from './api';
import { ComparisonData } from './types';

const ComparisonPage: React.FC = () => {
  const [v1, setV1] = useState<number | null>(null);
  const [v2, setV2] = useState<number | null>(null);
  const [comparison, setComparison] = useState<ComparisonData | null>(null);
  const [loading, setLoading] = useState(false);

  const handleCompare = async () => {
    if (!v1 || !v2) return;
    setLoading(true);
    try {
      const data = await fetchComparison(v1, v2);
      setComparison(data);
    } catch (error) {
      console.error('Error fetching comparison:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="comparison-page">
      <VersionSelector
        onV1Change={setV1}
        onV2Change={setV2}
        onCompare={handleCompare}
      />
      
      {loading && <div>Loading...</div>}
      
      {comparison && (
        <>
          <AIAnalysis analysis={comparison.ai_analysis} />
          
          <div className="metrics-cards">
            <MetricCard
              title="Bounce Rate Change"
              value={comparison.bounce_diff}
              unit="%"
              isPositive={comparison.bounce_diff < 0}
            />
            <MetricCard
              title="Avg Duration Change"
              value={comparison.duration_diff}
              unit="s"
              isPositive={comparison.duration_diff > 0}
            />
            <MetricCard
              title="Traffic Volume"
              value={comparison.visits_diff}
              unit=""
              isPositive={comparison.visits_diff > 0}
            />
          </div>

          <SplitTable
            title="Device Split"
            data={comparison.device_split}
            categoryField="device"
          />
          
          <SplitTable
            title="Browser Split"
            data={comparison.browser_split}
            categoryField="browser"
          />
          
          <SplitTable
            title="OS Split"
            data={comparison.os_split}
            categoryField="os"
          />

          <AlertsList alerts={comparison.alerts} />
          
          <IssuesTable issues={comparison.issues_diff} />
          
          <PagesTable pages={comparison.pages_diff} />
          
          <CohortsList cohorts={comparison.cohorts_diff} />
          
          <DetailedCohortsView
            v1Cohorts={comparison.v1_cohorts}
            v2Cohorts={comparison.v2_cohorts}
            v1Name={comparison.v1.name}
            v2Name={comparison.v2.name}
          />
        </>
      )}
    </div>
  );
};
```

### Vue 3 + TypeScript

```vue
<template>
  <div class="comparison-page">
    <VersionSelector
      :versions="versions"
      @compare="handleCompare"
    />
    
    <div v-if="loading">Loading...</div>
    
    <div v-if="comparison">
      <AIAnalysis :analysis="comparison.ai_analysis" />
      
      <div class="metrics-cards">
        <MetricCard
          title="Bounce Rate Change"
          :value="comparison.bounce_diff"
          unit="%"
          :is-positive="comparison.bounce_diff < 0"
        />
        <!-- ... другие карточки -->
      </div>
      
      <!-- ... остальные компоненты -->
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { fetchComparison } from './api';
import type { ComparisonData } from './types';

const comparison = ref<ComparisonData | null>(null);
const loading = ref(false);

const handleCompare = async (v1: number, v2: number) => {
  loading.value = true;
  try {
    const data = await fetchComparison(v1, v2);
    comparison.value = data;
  } catch (error) {
    console.error('Error:', error);
  } finally {
    loading.value = false;
  }
};
</script>
```

### Angular + TypeScript

```typescript
// comparison.service.ts
@Injectable({ providedIn: 'root' })
export class ComparisonService {
  constructor(private http: HttpClient) {}

  getComparison(v1: number, v2: number): Observable<ComparisonData> {
    return this.http.get<{ comparison: ComparisonData }>(
      `/analytics/api/compare/`,
      { params: { v1: v1.toString(), v2: v2.toString() } }
    ).pipe(
      map(response => response.comparison)
    );
  }
}

// comparison.component.ts
@Component({
  selector: 'app-comparison',
  templateUrl: './comparison.component.html'
})
export class ComparisonComponent {
  comparison$ = new BehaviorSubject<ComparisonData | null>(null);
  loading = false;

  constructor(private comparisonService: ComparisonService) {}

  compare(v1: number, v2: number) {
    this.loading = true;
    this.comparisonService.getComparison(v1, v2).subscribe({
      next: data => {
        this.comparison$.next(data);
        this.loading = false;
      },
      error: error => {
        console.error('Error:', error);
        this.loading = false;
      }
    });
  }
}
```

---

## Рекомендации по стилизации

### Цветовая схема

1. **Улучшения (положительные изменения):**
   - Bounce rate снижение: `text-green-600`, `bg-green-50`
   - Duration увеличение: `text-green-600`, `bg-green-50`
   - Visits увеличение: `text-green-600`, `bg-green-50`

2. **Ухудшения (отрицательные изменения):**
   - Bounce rate рост: `text-red-600`, `bg-red-50`
   - Duration снижение: `text-red-600`, `bg-red-50`
   - Visits снижение: `text-red-600`, `bg-red-50`

3. **Статусы:**
   - `new`: `bg-green-100 text-green-700`
   - `worse`: `bg-red-100 text-red-700`
   - `improved`: `bg-blue-100 text-blue-700`
   - `stable`: `bg-yellow-50 text-yellow-700`
   - `resolved`: `bg-gray-100 text-gray-600`

4. **Severity:**
   - `critical`: `bg-red-100 text-red-700 border-red-200`
   - `warning`: `bg-amber-50 text-amber-700 border-amber-200`

### Tailwind CSS классы (используемые в проекте)

```css
/* Карточки */
.bg-white, .rounded-xl, .shadow-sm, .border, .border-gray-100

/* Градиенты */
.bg-gradient-to-r, .from-indigo-50, .to-purple-50

/* Цвета текста */
.text-gray-500, .text-gray-700, .text-gray-900
.text-green-500, .text-green-600, .text-green-700
.text-red-500, .text-red-600, .text-red-700
.text-indigo-600, .text-indigo-700

/* Отступы */
.p-6, .p-4, .mb-6, .gap-6

/* Сетка */
.grid, .grid-cols-1, .md:grid-cols-2, .lg:grid-cols-3
```

---

## Обработка ошибок

```typescript
// api.ts
export const fetchComparison = async (
  v1: number,
  v2: number
): Promise<ComparisonData> => {
  try {
    const response = await fetch(
      `/analytics/api/compare/?v1=${v1}&v2=${v2}`
    );
    
    if (!response.ok) {
      if (response.status === 400) {
        throw new Error('Необходимо выбрать две версии для сравнения');
      }
      if (response.status === 404) {
        throw new Error('Версия не найдена');
      }
      throw new Error('Ошибка загрузки данных');
    }
    
    const data = await response.json();
    
    if (!data.comparison) {
      throw new Error('Неверный формат ответа');
    }
    
    return data.comparison;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Неизвестная ошибка');
  }
};
```

---

## Оптимизация производительности

1. **Ленивая загрузка компонентов:**
   - Загружать тяжелые компоненты (таблицы) только при необходимости
   - Использовать виртуализацию для больших списков

2. **Кэширование:**
   - Кэшировать результаты сравнения на клиенте
   - Использовать React Query / SWR / Apollo для кэширования

3. **Debounce для селекторов:**
   - Добавить задержку перед запросом при изменении версий

---

## Заключение

Данное руководство описывает полную структуру API и компонентов для интеграции системы сравнения версий с современным фронтендом. Все endpoints возвращают JSON и готовы к использованию в React, Vue, Angular или любом другом фреймворке.

**Основные точки интеграции:**
1. `/analytics/api/versions/` - получение списка версий
2. `/analytics/api/compare/?v1=X&v2=Y` - основное сравнение
3. Компоненты UI для отображения метрик и разниц

**Следующие шаги:**
1. Выбрать фреймворк (React/Vue/Angular)
2. Создать типы TypeScript на основе структур данных
3. Реализовать компоненты согласно примерам
4. Добавить обработку ошибок и loading states
5. Применить стилизацию согласно рекомендациям

