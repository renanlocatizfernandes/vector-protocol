import React, { useEffect, useState } from 'react';
import { Brain, Activity, AlertCircle, CheckCircle, XCircle, RefreshCw } from 'lucide-react';
import { getMLStatus, getMLRegimes, type MLStatus } from '../services/api';

interface RegimeData {
  regime_id: number;
  regime_name: string;
  config?: Record<string, any>;
  metrics?: { total_trades: number; win_rate: number; avg_pnl_pct: number };
}

export const AIEStatusCard: React.FC = () => {
  const [mlStatus, setMlStatus] = useState<MLStatus | null>(null);
  const [regimes, setRegimes] = useState<RegimeData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [statusRes, regimesRes] = await Promise.all([
        getMLStatus().catch(() => null),
        getMLRegimes().catch(() => null)
      ]);

      if (statusRes?.data) {
        setMlStatus({
          initialized: statusRes.data.is_initialized,
          regime_detector_trained: statusRes.data.models_trained?.regime_detector || false,
          anomaly_detector_trained: statusRes.data.models_trained?.anomaly_detector || false,
          indicator_optimizer_trained: statusRes.data.models_trained?.indicator_optimizer || false,
          current_regime: statusRes.data.current_regime,
          filter_rules_loaded: statusRes.data.active_filter_rules || 0
        });
      }

      // Convert regimes object to array
      if (regimesRes?.data) {
        const regimesArray: RegimeData[] = Object.entries(regimesRes.data).map(([name, data]: [string, any]) => ({
          regime_id: data.regime_id,
          regime_name: name,
          config: data.config,
          metrics: data.metrics
        }));
        setRegimes(regimesArray);
      }
    } catch (err: any) {
      setError(err?.message || 'Erro ao carregar status do ML');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const timer = setInterval(loadData, 60000); // Atualiza a cada 1 minuto
    return () => clearInterval(timer);
  }, []);

  const getRegimeColor = (regime: string | undefined) => {
    if (!regime) return 'bg-slate-500';
    if (regime.includes('trending_low_vol')) return 'bg-green-500';
    if (regime.includes('trending_high_vol')) return 'bg-yellow-500';
    if (regime.includes('ranging_low_vol')) return 'bg-blue-500';
    if (regime.includes('ranging_high_vol')) return 'bg-orange-500';
    if (regime.includes('explosive')) return 'bg-red-500';
    return 'bg-purple-500';
  };

  const getRegimeEmoji = (regime: string | undefined) => {
    if (!regime) return '?';
    if (regime.includes('trending_low_vol')) return 'trending_low_vol';
    if (regime.includes('trending_high_vol')) return 'trending_high_vol';
    if (regime.includes('ranging_low_vol')) return 'ranging_low_vol';
    if (regime.includes('ranging_high_vol')) return 'ranging_high_vol';
    if (regime.includes('explosive')) return 'explosive';
    return regime;
  };

  if (loading && !mlStatus) {
    return (
      <div className="glass-card p-6 animate-pulse">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-slate-200 rounded-xl"></div>
          <div className="h-6 bg-slate-200 rounded w-48"></div>
        </div>
        <div className="space-y-3">
          <div className="h-4 bg-slate-200 rounded w-full"></div>
          <div className="h-4 bg-slate-200 rounded w-3/4"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card overflow-hidden">
      <div className="p-4 border-b border-slate-200/50 bg-gradient-to-r from-purple-50/50 to-indigo-50/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-purple-500/30">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900">Adaptive Intelligence Engine</h3>
              <p className="text-xs text-slate-500 font-medium">ML & Otimizacao Automatica</p>
            </div>
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="p-2 rounded-lg hover:bg-slate-100 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 text-slate-600 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
            <AlertCircle className="w-4 h-4 text-red-500" />
            <span className="text-sm text-red-700">{error}</span>
          </div>
        )}

        {/* Status do Sistema */}
        <div className="grid grid-cols-2 gap-3">
          <div className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg">
            {mlStatus?.initialized ? (
              <CheckCircle className="w-4 h-4 text-green-500" />
            ) : (
              <XCircle className="w-4 h-4 text-red-500" />
            )}
            <span className="text-sm font-medium text-slate-700">AIE Inicializado</span>
          </div>
          <div className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg">
            {mlStatus?.regime_detector_trained ? (
              <CheckCircle className="w-4 h-4 text-green-500" />
            ) : (
              <XCircle className="w-4 h-4 text-red-500" />
            )}
            <span className="text-sm font-medium text-slate-700">Regime Detector</span>
          </div>
          <div className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg">
            {mlStatus?.anomaly_detector_trained ? (
              <CheckCircle className="w-4 h-4 text-green-500" />
            ) : (
              <XCircle className="w-4 h-4 text-red-500" />
            )}
            <span className="text-sm font-medium text-slate-700">Anomaly Detector</span>
          </div>
          <div className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg">
            {mlStatus?.indicator_optimizer_trained ? (
              <CheckCircle className="w-4 h-4 text-green-500" />
            ) : (
              <XCircle className="w-4 h-4 text-red-500" />
            )}
            <span className="text-sm font-medium text-slate-700">Indicator Optimizer</span>
          </div>
        </div>

        {/* Regime Atual */}
        <div className="p-4 bg-gradient-to-r from-slate-50 to-purple-50 rounded-xl border border-slate-200">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-bold text-slate-600 uppercase">Regime de Mercado Atual</span>
            <Activity className="w-4 h-4 text-purple-600" />
          </div>
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${getRegimeColor(typeof mlStatus?.current_regime === 'object' ? mlStatus?.current_regime?.name : mlStatus?.current_regime)} animate-pulse`}></div>
            <span className="text-lg font-bold text-slate-900">
              {typeof mlStatus?.current_regime === 'object' ? mlStatus?.current_regime?.name : mlStatus?.current_regime || 'Nao detectado'}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-2">
            {regimes.length} regimes configurados
          </p>
        </div>

        {/* Filter Rules */}
        {mlStatus?.filter_rules_loaded !== undefined && mlStatus.filter_rules_loaded > 0 && (
          <div className="flex items-center justify-between p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-amber-600" />
              <span className="text-sm font-medium text-amber-800">Filter Rules Ativas</span>
            </div>
            <span className="text-lg font-bold text-amber-900">{mlStatus.filter_rules_loaded}</span>
          </div>
        )}

        {/* Regimes Overview */}
        {regimes.length > 0 && (
          <div className="space-y-2">
            <span className="text-xs font-bold text-slate-500 uppercase">Performance por Regime</span>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {regimes.slice(0, 5).map((regime) => (
                <div
                  key={regime.regime_id}
                  className={`flex items-center justify-between p-2 rounded-lg ${
                    regime.regime_name === (typeof mlStatus?.current_regime === 'object' ? mlStatus?.current_regime?.name : mlStatus?.current_regime)
                      ? 'bg-purple-100 border border-purple-300'
                      : 'bg-slate-50'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${getRegimeColor(regime.regime_name)}`}></div>
                    <span className="text-sm font-medium text-slate-700">{regime.regime_name}</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs">
                    {regime.metrics?.win_rate !== undefined && (
                      <span className={`font-bold ${regime.metrics.win_rate >= 0.5 ? 'text-green-600' : 'text-red-600'}`}>
                        {(regime.metrics.win_rate * 100).toFixed(0)}% WR
                      </span>
                    )}
                    {regime.metrics?.total_trades !== undefined && (
                      <span className="text-slate-500">{regime.metrics.total_trades} trades</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AIEStatusCard;
