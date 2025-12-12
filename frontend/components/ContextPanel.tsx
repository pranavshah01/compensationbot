'use client';

import { useState } from 'react';
import { contextAPI } from '@/lib/api';
import { useAuthStore } from '@/lib/store';

interface ContextPanelProps {
  candidateId: string;
  onCandidateIdChange: (id: string) => void;
}

export default function ContextPanel({ candidateId, onCandidateIdChange }: ContextPanelProps) {
  const [context, setContext] = useState<any>(null);
  const [auditLog, setAuditLog] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { user } = useAuthStore();

  const handleGetStatus = async () => {
    if (!candidateId) {
      setError('Please enter a candidate ID');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const data = await contextAPI.getContext(candidateId);
      setContext(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch context');
      setContext(null);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    if (!candidateId) {
      setError('Please enter a candidate ID');
      return;
    }

    if (!confirm('Are you sure you want to reset the context for this candidate?')) {
      return;
    }

    setLoading(true);
    setError('');
    try {
      await contextAPI.resetContext(candidateId);
      alert('Context reset successfully');
      setContext(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to reset context');
    } finally {
      setLoading(false);
    }
  };

  const handleGetAudit = async () => {
    if (!candidateId) {
      setError('Please enter a candidate ID');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const data = await contextAPI.getAudit(candidateId);
      setAuditLog(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch audit log');
      setAuditLog([]);
    } finally {
      setLoading(false);
    }
  };

  const isCompTeam = user?.user_type === 'Comp Team';

  return (
    <div className="bg-white/95 backdrop-blur-sm border-l border-gray-200 p-6 w-96 overflow-y-auto shadow-soft">
      <h2 className="text-xl font-bold mb-6 text-gray-900">Context Management</h2>

      <div className="space-y-5">
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2.5">
            Candidate ID
          </label>
          <input
            type="text"
            value={candidateId}
            onChange={(e) => onCandidateIdChange(e.target.value)}
            placeholder="Enter candidate ID"
            className="w-full px-4 py-3 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all font-mono"
          />
        </div>

        <div className="flex gap-3">
          <button
            onClick={handleGetStatus}
            disabled={loading}
            className="flex-1 px-4 py-2.5 bg-primary-600 text-white text-sm font-semibold rounded-xl hover:bg-primary-700 disabled:opacity-50 transition-all shadow-sm hover:shadow"
          >
            Status
          </button>
          {isCompTeam && (
            <button
              onClick={handleReset}
              disabled={loading}
              className="flex-1 px-4 py-2.5 bg-red-600 text-white text-sm font-semibold rounded-xl hover:bg-red-700 disabled:opacity-50 transition-all shadow-sm hover:shadow"
            >
              Reset
            </button>
          )}
        </div>

        <button
          onClick={handleGetAudit}
          disabled={loading}
          className="w-full px-4 py-2.5 bg-gray-700 text-white text-sm font-semibold rounded-xl hover:bg-gray-800 disabled:opacity-50 transition-all shadow-sm hover:shadow"
        >
          Audit Log
        </button>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm animate-slide-up">
            {error}
          </div>
        )}

        {context && (
          <div className="mt-5 p-4 bg-gray-50 rounded-xl border border-gray-200">
            <h3 className="font-semibold text-sm mb-3 text-gray-900">Context</h3>
            <pre className="text-xs overflow-auto font-mono bg-white p-3 rounded-lg border border-gray-200 text-gray-800">
              {JSON.stringify(context.context, null, 2)}
            </pre>
            <p className="text-xs text-gray-600 mt-3 font-medium">
              Last updated: {new Date(context.last_updated).toLocaleString()}
            </p>
          </div>
        )}

        {auditLog.length > 0 && (
          <div className="mt-5">
            <h3 className="font-semibold text-sm mb-3 text-gray-900">Audit Log</h3>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {auditLog.map((log, idx) => (
                <div key={idx} className="text-xs p-3 bg-gray-50 rounded-xl border border-gray-200 hover:bg-gray-100 transition-colors">
                  <p className="font-semibold text-gray-900 mb-1">{log.field}</p>
                  <p className="text-gray-600 mb-1">{log.updated_by}</p>
                  <p className="text-gray-500">{new Date(log.timestamp).toLocaleString()}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}



