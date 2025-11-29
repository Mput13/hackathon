/**
 * Полный пример React компонента для сравнения версий
 * Используйте этот файл как основу для интеграции
 */

import React, { useState, useEffect } from 'react';

// ==================== Types ====================

interface Version {
  id: number;
  name: string;
  release_date: string;
  is_active: boolean;
}

interface DeviceSplit {
  device: string;
  visits_v1: number;
  visits_v2: number;
  share_v1: number;
  share_v2: number;
  share_diff: number;
  bounce_v1: number;
  bounce_v2: number;
  bounce_diff: number;
  duration_v1: number;
  duration_v2: number;
  duration_diff: number;
}

interface IssueDiff {
  id: number;
  issue_type: string;
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  location_url: string;
  location_readable: string;
  impact_score: number;
  affected_sessions: number;
  status: 'new' | 'worse' | 'improved' | 'stable' | 'resolved';
  impact_diff: number;
  trend: string;
  priority: string;
  recommended_specialists: string[];
  detected_version_name: string;
}

interface PageDiff {
  status: 'new' | 'removed' | 'changed' | 'stable';
  exit_diff: number;
  time_diff: number;
  readable: string;
  v1: any | null;
  v2: any | null;
}

interface Alert {
  type: string;
  message: string;
  url?: string;
  severity: 'critical' | 'warning';
}

interface ComparisonData {
  v1: { id: number; name: string };
  v2: { id: number; name: string };
  visits_diff: number;
  bounce_diff: number;
  duration_diff: number;
  stats_v1: { visits: number; bounce: number; duration: number };
  stats_v2: { visits: number; bounce: number; duration: number };
  ai_analysis: string | null;
  device_split: DeviceSplit[];
  browser_split: DeviceSplit[];
  os_split: DeviceSplit[];
  alerts: Alert[];
  issues_diff: IssueDiff[];
  pages_diff: PageDiff[];
}

// ==================== API Functions ====================

const API_BASE = '/analytics/api';

async function fetchVersions(): Promise<Version[]> {
  const response = await fetch(`${API_BASE}/versions/`);
  if (!response.ok) throw new Error('Failed to fetch versions');
  const data = await response.json();
  return data.versions;
}

async function fetchComparison(v1: number, v2: number): Promise<ComparisonData> {
  const response = await fetch(`${API_BASE}/compare/?v1=${v1}&v2=${v2}`);
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
  return data.comparison;
}

// ==================== Helper Functions ====================

function formatDelta(value: number, unit: string = ''): string {
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(1)}${unit}`;
}

function getColorClass(value: number, isPositiveGood: boolean): string {
  if (value === 0) return 'text-gray-600';
  const isGood = isPositiveGood ? value > 0 : value < 0;
  return isGood ? 'text-green-600' : 'text-red-600';
}

function getStatusBadgeClass(status: string): string {
  const styles: Record<string, string> = {
    new: 'bg-green-100 text-green-700',
    resolved: 'bg-gray-100 text-gray-600',
    worse: 'bg-red-100 text-red-700',
    improved: 'bg-blue-100 text-blue-700',
    stable: 'bg-yellow-50 text-yellow-700',
    changed: 'bg-yellow-100 text-yellow-700',
    removed: 'bg-gray-100 text-gray-600',
  };
  return styles[status] || 'bg-gray-100 text-gray-600';
}

// ==================== Components ====================

interface VersionSelectorProps {
  versions: Version[];
  selectedV1: number | null;
  selectedV2: number | null;
  onV1Change: (id: number) => void;
  onV2Change: (id: number) => void;
  onCompare: () => void;
}

const VersionSelector: React.FC<VersionSelectorProps> = ({
  versions,
  selectedV1,
  selectedV2,
  onV1Change,
  onV2Change,
  onCompare,
}) => {
  return (
    <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 mb-6 flex items-center justify-between">
      <div className="flex items-center space-x-4">
        <select
          value={selectedV1 || ''}
          onChange={(e) => onV1Change(Number(e.target.value))}
          className="form-select rounded-md border-gray-300 shadow-sm p-2 border"
        >
          <option value="">Выберите версию 1</option>
          {versions.map((v) => (
            <option key={v.id} value={v.id}>
              {v.name}
            </option>
          ))}
        </select>
        <span className="text-gray-400 font-bold">VS</span>
        <select
          value={selectedV2 || ''}
          onChange={(e) => onV2Change(Number(e.target.value))}
          className="form-select rounded-md border-gray-300 shadow-sm p-2 border"
        >
          <option value="">Выберите версию 2</option>
          {versions.map((v) => (
            <option key={v.id} value={v.id}>
              {v.name}
            </option>
          ))}
        </select>
        <button
          onClick={onCompare}
          disabled={!selectedV1 || !selectedV2}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Analyze Difference
        </button>
      </div>
    </div>
  );
};

interface MetricCardProps {
  title: string;
  value: number;
  unit: string;
  isPositive: boolean;
  hint?: string;
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  isPositive,
  hint,
}) => {
  const colorClass = isPositive ? 'text-green-500' : 'text-red-500';
  const sign = value > 0 ? '+' : '';

  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 text-center">
      <p className="text-sm text-gray-500 mb-1">{title}</p>
      <p className={`text-4xl font-bold ${colorClass}`}>
        {sign}{value.toFixed(1)}{unit}
      </p>
      {hint && <p className="text-xs text-gray-400 mt-2">{hint}</p>}
    </div>
  );
};

interface AIAnalysisProps {
  analysis: string | null;
}

const AIAnalysis: React.FC<AIAnalysisProps> = ({ analysis }) => {
  if (!analysis) return null;

  return (
    <div className="bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-200 rounded-xl p-6 mb-6">
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg
            className="w-6 h-6 text-indigo-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
        </div>
        <div className="ml-4 flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">
            🤖 AI-анализ сравнения
          </h3>
          <div className="text-sm text-gray-700 whitespace-pre-line space-y-2">
            {analysis}
          </div>
        </div>
      </div>
    </div>
  );
};

interface SplitTableProps {
  title: string;
  data: DeviceSplit[];
  categoryField: 'device' | 'browser' | 'os';
}

const SplitTable: React.FC<SplitTableProps> = ({ title, data, categoryField }) => {
  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-sm font-bold text-gray-700 uppercase tracking-wider">
          {title}
        </h4>
        <div className="text-xs text-gray-500">Share, Bounce, Time (Δ)</div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
            <tr>
              <th className="px-3 py-2 text-left">
                {categoryField === 'device' ? 'Device' : categoryField === 'browser' ? 'Browser' : 'OS'}
              </th>
              <th className="px-3 py-2 text-right">Share Δ (p.p.)</th>
              <th className="px-3 py-2 text-right">Bounce Δ (p.p.)</th>
              <th className="px-3 py-2 text-right">Duration Δ (s)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-3 py-4 text-center text-gray-400">
                  No data
                </td>
              </tr>
            ) : (
              data.map((row, idx) => (
                <tr key={idx} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-medium text-gray-800">
                    {row[categoryField].charAt(0).toUpperCase() + row[categoryField].slice(1)}
                  </td>
                  <td
                    className={`px-3 py-2 text-right ${getColorClass(row.share_diff, true)}`}
                  >
                    {formatDelta(row.share_diff)}
                    <span className="text-xs text-gray-400 ml-1">
                      ({row.share_v1.toFixed(1)}% → {row.share_v2.toFixed(1)}%)
                    </span>
                  </td>
                  <td
                    className={`px-3 py-2 text-right ${getColorClass(row.bounce_diff, false)}`}
                  >
                    {formatDelta(row.bounce_diff)}
                    <span className="text-xs text-gray-400 ml-1">
                      ({row.bounce_v1.toFixed(1)}% → {row.bounce_v2.toFixed(1)}%)
                    </span>
                  </td>
                  <td
                    className={`px-3 py-2 text-right ${getColorClass(row.duration_diff, true)}`}
                  >
                    {formatDelta(row.duration_diff)}
                    <span className="text-xs text-gray-400 ml-1">
                      ({row.duration_v1.toFixed(1)}s → {row.duration_v2.toFixed(1)}s)
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

interface AlertsListProps {
  alerts: Alert[];
}

const AlertsList: React.FC<AlertsListProps> = ({ alerts }) => {
  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-sm font-bold text-gray-700 uppercase tracking-wider">
          Alerts
        </h4>
        <div className="text-xs text-gray-500">
          New critical issues / exit spikes
        </div>
      </div>
      <div className="space-y-2 text-sm">
        {alerts.length === 0 ? (
          <div className="text-gray-400 text-xs">No alerts</div>
        ) : (
          alerts.map((alert, idx) => (
            <div
              key={idx}
              className={`p-3 rounded border ${
                alert.severity === 'critical'
                  ? 'border-red-200 bg-red-50 text-red-700'
                  : 'border-amber-200 bg-amber-50 text-amber-700'
              }`}
            >
              <div className="font-semibold">{alert.type}</div>
              <div>{alert.message}</div>
              {alert.url && (
                <div className="text-xs text-gray-500 break-all mt-1">
                  {alert.url}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

interface IssuesTableProps {
  issues: IssueDiff[];
}

const IssuesTable: React.FC<IssuesTableProps> = ({ issues }) => {
  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-sm font-bold text-gray-700 uppercase tracking-wider">
          Issues Diff (top)
        </h4>
        <div className="text-xs text-gray-500">
          New/Worse/Improved/Resolved
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
            <tr>
              <th className="px-3 py-2 text-left">Type</th>
              <th className="px-3 py-2 text-left">Location</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-right">Impact Δ</th>
              <th className="px-3 py-2 text-right">Impact</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {issues.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-4 text-center text-gray-400">
                  No issues to compare
                </td>
              </tr>
            ) : (
              issues.map((issue) => (
                <tr key={issue.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2">{issue.issue_type}</td>
                  <td className="px-3 py-2">
                    <div className="text-indigo-600 font-medium">
                      {issue.location_readable}
                    </div>
                    <div className="text-xs text-gray-400 font-mono">
                      {issue.location_url}
                    </div>
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className={`px-2 py-1 rounded-full text-xs ${getStatusBadgeClass(
                        issue.status
                      )}`}
                    >
                      {issue.status}
                    </span>
                  </td>
                  <td
                    className={`px-3 py-2 text-right ${
                      issue.impact_diff > 0 ? 'text-red-600' : 'text-green-600'
                    }`}
                  >
                    {issue.impact_diff > 0 ? '+' : ''}
                    {issue.impact_diff.toFixed(2)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {issue.impact_score.toFixed(2)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

interface PagesTableProps {
  pages: PageDiff[];
}

const PagesTable: React.FC<PagesTableProps> = ({ pages }) => {
  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-sm font-bold text-gray-700 uppercase tracking-wider">
          Pages Diff (top)
        </h4>
        <div className="text-xs text-gray-500">Exit/Time changes</div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
            <tr>
              <th className="px-3 py-2 text-left">Page</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-right">Exit Δ (p.p.)</th>
              <th className="px-3 py-2 text-right">Time Δ (s)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {pages.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-3 py-4 text-center text-gray-400">
                  No page differences
                </td>
              </tr>
            ) : (
              pages.map((page, idx) => (
                <tr key={idx} className="hover:bg-gray-50">
                  <td className="px-3 py-2">
                    <div className="text-indigo-600 font-medium">
                      {page.readable}
                    </div>
                    <div className="text-xs text-gray-400 font-mono">
                      {page.v2?.url || page.v1?.url || ''}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-xs">
                    <span
                      className={`px-2 py-1 rounded-full ${getStatusBadgeClass(
                        page.status
                      )}`}
                    >
                      {page.status}
                    </span>
                  </td>
                  <td
                    className={`px-3 py-2 text-right ${
                      page.exit_diff > 0 ? 'text-red-600' : 'text-green-600'
                    }`}
                  >
                    {page.exit_diff > 0 ? '+' : ''}
                    {page.exit_diff.toFixed(1)}
                  </td>
                  <td
                    className={`px-3 py-2 text-right ${
                      page.time_diff > 0 ? 'text-green-600' : 'text-red-600'
                    }`}
                  >
                    {page.time_diff > 0 ? '+' : ''}
                    {page.time_diff.toFixed(1)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ==================== Main Component ====================

const ComparisonPage: React.FC = () => {
  const [versions, setVersions] = useState<Version[]>([]);
  const [selectedV1, setSelectedV1] = useState<number | null>(null);
  const [selectedV2, setSelectedV2] = useState<number | null>(null);
  const [comparison, setComparison] = useState<ComparisonData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchVersions()
      .then(setVersions)
      .catch((err) => setError(err.message));
  }, []);

  const handleCompare = async () => {
    if (!selectedV1 || !selectedV2) return;

    setLoading(true);
    setError(null);
    try {
      const data = await fetchComparison(selectedV1, selectedV2);
      setComparison(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Version Comparison</h1>

      <VersionSelector
        versions={versions}
        selectedV1={selectedV1}
        selectedV2={selectedV2}
        onV1Change={setSelectedV1}
        onV2Change={setSelectedV2}
        onCompare={handleCompare}
      />

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg mb-6">
          {error}
        </div>
      )}

      {loading && (
        <div className="text-center py-20 text-gray-400">Loading...</div>
      )}

      {comparison && !loading && (
        <>
          <AIAnalysis analysis={comparison.ai_analysis} />

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <MetricCard
              title="Bounce Rate Change"
              value={comparison.bounce_diff}
              unit="%"
              isPositive={comparison.bounce_diff < 0}
              hint="Lower is better"
            />
            <MetricCard
              title="Avg Duration Change"
              value={comparison.duration_diff}
              unit="s"
              isPositive={comparison.duration_diff > 0}
              hint="Context dependent"
            />
            <MetricCard
              title="Traffic Volume"
              value={comparison.visits_diff}
              unit=""
              isPositive={comparison.visits_diff > 0}
              hint="Sessions difference"
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
        </>
      )}
    </div>
  );
};

export default ComparisonPage;

