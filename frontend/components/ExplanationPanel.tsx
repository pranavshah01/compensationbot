'use client';

interface HistoryItem {
  timestamp: string;
  context_snapshot: {
    job_level?: string;
    location?: string;
    job_title?: string;
    interview_feedback?: string;
    [key: string]: any;
  };
  recommendation: {
    base_salary?: number;
    total_compensation?: number;
    [key: string]: any;
  };
}

interface Recommendation {
  status: string;
  history?: HistoryItem[];
  recommendation?: {
    base_salary?: number;
    base_salary_percent_of_range?: number;
    base_salary_percentile?: number;
    bonus_percentage?: number;
    bonus_amount?: number;
    equity_amount?: number;
    total_compensation?: number;
    market_range?: {
      min: number;
      max: number;
      source: string;
    };
    internal_parity?: {
      min: number;
      max: number;
      count: number;
      source: string;
    };
    reasoning?: {
      market_data_analysis?: string;
      market_data_citation?: string;
      internal_parity_analysis?: string;
      internal_parity_citation?: string;
      percentile_justification?: string;
      job_family_impact?: string;
      proficiency_impact?: string;
      level_impact?: string;
      band_placement_reasoning?: string;
      equity_allocation_reasoning?: string;
      equity_justification?: string;
      bonus_percentage_reasoning?: string;
      bonus_justification?: string;
      data_sources_used?: string;
      considerations_and_tradeoffs?: string;
    } | string;
  };
}

interface ExplanationPanelProps {
  recommendation: Recommendation | null;
  onClose: () => void;
}

export default function ExplanationPanel({ recommendation, onClose }: ExplanationPanelProps) {
  if (!recommendation || recommendation.status !== 'approved' || !recommendation.recommendation) {
    return null;
  }

  const rec = recommendation.recommendation;
  // Handle reasoning being either an object or a string
  const reasoning = typeof rec.reasoning === 'object' ? (rec.reasoning || {}) : {};
  const reasoningText = typeof rec.reasoning === 'string' ? rec.reasoning : null;
  const history = recommendation.history || [];
  
  // Get percentile - check both field names
  const percentile = rec.base_salary_percentile || rec.base_salary_percent_of_range || 0;

  const formatDate = (isoString: string) => {
    try {
      return new Date(isoString).toLocaleString('en-US', {
        month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'
      });
    } catch (e) {
      return isoString;
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-white/95 backdrop-blur-sm shadow-xl z-50 flex flex-col border-l border-gray-200">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary-600 to-indigo-600 text-white px-6 py-5 flex items-center justify-between shadow-medium">
        <h2 className="text-xl font-bold">Detailed Explanation</h2>
        <button
          onClick={onClose}
          className="text-white hover:text-gray-200 transition-colors p-1.5 rounded-lg hover:bg-white/20"
          aria-label="Close"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6 smooth-scroll">

        {/* RECOMMENDATION HISTORY */}
        {history.length > 0 && (
          <div className="space-y-3">
            <h3 className="font-bold text-gray-900 text-lg flex items-center gap-2">
              <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0" /></svg>
              History ({history.length})
            </h3>
            <div className="space-y-3 max-h-60 overflow-y-auto pr-1">
              {history.map((item, idx) => (
                <div key={idx} className="bg-gray-50 rounded-lg p-3 border border-gray-200 text-sm hover:border-primary-300 transition-colors">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{formatDate(item.timestamp)}</span>
                  </div>

                  {/* Context Snapshot */}
                  <div className="grid grid-cols-2 gap-x-2 gap-y-1 mb-2 text-xs text-gray-600 border-b border-gray-200 pb-2">
                    {item.context_snapshot.job_title && <div className="col-span-2 font-medium text-gray-800">{item.context_snapshot.job_title}</div>}
                    {item.context_snapshot.location && <div>Loc: {item.context_snapshot.location}</div>}
                    {item.context_snapshot.job_level && <div>Lvl: {item.context_snapshot.job_level}</div>}
                    {item.context_snapshot.interview_feedback && <div className="col-span-2">Rating: {item.context_snapshot.interview_feedback}</div>}
                  </div>

                  {/* Outcome */}
                  <div className="flex justify-between items-end">
                    <div className="text-gray-600 text-xs">Base: ${item.recommendation.base_salary?.toLocaleString() ?? 0}</div>
                    <div className="font-bold text-primary-700">Total: ${item.recommendation.total_compensation?.toLocaleString() ?? 0}</div>
                  </div>
                </div>
              ))}
            </div>
            <hr className="border-gray-200" />
          </div>
        )}

        {/* Summary */}
        <div className="bg-gradient-to-br from-primary-50 to-indigo-50 rounded-xl p-5 border border-primary-200 shadow-soft">
          <h3 className="font-bold text-primary-900 mb-4 text-lg">Compensation Summary</h3>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between items-center py-2">
              <span className="text-gray-700 font-medium">Base Salary:</span>
              <span className="font-bold text-gray-900">${rec.base_salary?.toLocaleString() || 0}</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-gray-700 font-medium">Percentile:</span>
              <span className="font-bold text-gray-900">{Math.round(percentile)}th</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-gray-700 font-medium">Bonus:</span>
              <span className="font-bold text-gray-900">{rec.bonus_percentage || 0}% (${rec.bonus_amount?.toLocaleString() || Math.round((rec.base_salary || 0) * (rec.bonus_percentage || 0) / 100).toLocaleString()})</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-gray-700 font-medium">Equity:</span>
              <span className="font-bold text-gray-900">${rec.equity_amount?.toLocaleString() || 0}</span>
            </div>
            <div className="flex justify-between items-center pt-3 mt-3 border-t border-primary-300">
              <span className="text-gray-900 font-bold">Total Compensation:</span>
              <span className="font-bold text-2xl text-primary-900">${rec.total_compensation?.toLocaleString() || 0}</span>
            </div>
          </div>
        </div>

        {/* Data Source Citations */}
        <div className="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-xl p-5 border border-blue-200 shadow-soft">
          <h3 className="font-bold text-blue-900 mb-4 text-lg flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
            Data Sources & Citations
          </h3>
          <div className="space-y-4 text-sm">
            {/* Market Data Citation */}
            {rec.market_range && (
              <div className="bg-white rounded-lg p-3 border border-blue-100">
                <div className="font-semibold text-blue-800 mb-1">📊 {rec.market_range.source}</div>
                <div className="text-gray-700">
                  Market range: <span className="font-medium">${rec.market_range.min?.toLocaleString()} - ${rec.market_range.max?.toLocaleString()}</span>
                </div>
                <div className="text-gray-600 text-xs mt-1">
                  Recommended base ${rec.base_salary?.toLocaleString()} is at {Math.round(percentile)}th percentile
                </div>
              </div>
            )}
            
            {/* Internal Parity Citation */}
            {rec.internal_parity && (
              <div className="bg-white rounded-lg p-3 border border-blue-100">
                <div className="font-semibold text-blue-800 mb-1">👥 {rec.internal_parity.source}</div>
                <div className="text-gray-700">
                  {rec.internal_parity.count} comparable employees: <span className="font-medium">${rec.internal_parity.min?.toLocaleString()} - ${rec.internal_parity.max?.toLocaleString()}</span>
                </div>
              </div>
            )}
            
            {/* Reasoning citations from LLM */}
            {reasoning.market_data_citation && (
              <div className="text-gray-700 italic">{reasoning.market_data_citation}</div>
            )}
            {reasoning.internal_parity_citation && (
              <div className="text-gray-700 italic">{reasoning.internal_parity_citation}</div>
            )}
          </div>
        </div>

        {/* Detailed Analysis */}
        <div className="space-y-5">
          <h3 className="font-bold text-gray-900 text-lg">Detailed Analysis</h3>

          {/* If reasoning is just a string, show it */}
          {reasoningText && (
            <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
              <h4 className="font-bold text-gray-900 mb-2.5 text-base">Reasoning</h4>
              <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{reasoningText}</p>
            </div>
          )}

          {reasoning.percentile_justification && (
            <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
              <h4 className="font-bold text-gray-900 mb-2.5 text-base">Percentile Justification</h4>
              <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{reasoning.percentile_justification}</p>
            </div>
          )}

          {reasoning.market_data_analysis && (
            <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
              <h4 className="font-bold text-gray-900 mb-2.5 text-base">Market Data Analysis</h4>
              <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{reasoning.market_data_analysis}</p>
            </div>
          )}

          {reasoning.internal_parity_analysis && (
            <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
              <h4 className="font-bold text-gray-900 mb-2.5 text-base">Internal Parity Analysis</h4>
              <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{reasoning.internal_parity_analysis}</p>
            </div>
          )}

          {reasoning.job_family_impact && (
            <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
              <h4 className="font-bold text-gray-900 mb-2.5 text-base">Job Family Impact</h4>
              <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{reasoning.job_family_impact}</p>
            </div>
          )}

          {reasoning.proficiency_impact && (
            <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
              <h4 className="font-bold text-gray-900 mb-2.5 text-base">Proficiency Impact</h4>
              <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{reasoning.proficiency_impact}</p>
            </div>
          )}

          {reasoning.level_impact && (
            <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
              <h4 className="font-bold text-gray-900 mb-2.5 text-base">Level Impact</h4>
              <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{reasoning.level_impact}</p>
            </div>
          )}

          {reasoning.band_placement_reasoning && (
            <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
              <h4 className="font-bold text-gray-900 mb-2.5 text-base">Band Placement Reasoning</h4>
              <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{reasoning.band_placement_reasoning}</p>
            </div>
          )}

          {reasoning.equity_allocation_reasoning && (
            <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
              <h4 className="font-bold text-gray-900 mb-2.5 text-base">Equity Allocation Reasoning</h4>
              <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{reasoning.equity_allocation_reasoning}</p>
            </div>
          )}

          {reasoning.bonus_percentage_reasoning && (
            <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
              <h4 className="font-bold text-gray-900 mb-2.5 text-base">Bonus Percentage Reasoning</h4>
              <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{reasoning.bonus_percentage_reasoning}</p>
            </div>
          )}

          {reasoning.considerations_and_tradeoffs && (
            <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
              <h4 className="font-bold text-gray-900 mb-2.5 text-base">Considerations and Trade-offs</h4>
              <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{reasoning.considerations_and_tradeoffs}</p>
            </div>
          )}

          {/* Data Sources and Citations */}
          {reasoning.data_sources_used && (
            <div className="bg-gradient-to-br from-gray-50 to-slate-50 rounded-xl p-5 border border-gray-200 shadow-soft">
              <h4 className="font-bold text-gray-900 mb-3 text-base">Data Sources and Citations</h4>
              <div className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{reasoning.data_sources_used}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


