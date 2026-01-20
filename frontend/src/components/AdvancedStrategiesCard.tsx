import React, { useEffect, useState } from 'react';
import { Crosshair, TrendingUp, Layers, ArrowDownCircle, Shield, Activity, RefreshCw, AlertCircle, CheckCircle, XCircle } from 'lucide-react';
import { getStrategiesConfig, getActiveTrailingStops, getStrategiesPerformance, type StrategiesConfig, type ActiveTrailingStop, type PerformanceSummary } from '../services/api';

export const AdvancedStrategiesCard: React.FC = () => {
  const [config, setConfig] = useState<StrategiesConfig | null>(null);
  const [trailingStops, setTrailingStops] = useState<ActiveTrailingStop[]>([]);
  const [performance, setPerformance] = useState<PerformanceSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [configRes, trailingRes, perfRes] = await Promise.all([
        getStrategiesConfig().catch(() => null),
        getActiveTrailingStops().catch(() => ({ active_trails: [] })),
        getStrategiesPerformance().catch(() => null)
      ]);
      // Handle config response format
      if (configRes?.config) {
        setConfig({
          default_execution_mode: configRes.config.execution_mode || 'static',
          default_trailing_mode: configRes.config.trailing_stop_mode || 'smart',
          sniper_enabled: configRes.config.is_active || false,
          pyramid_enabled: true,
          dca_enabled: true,
          breakeven_enabled: true,
          trailing_stop_pct: configRes.config.base_callback_pct
        });
      } else if (configRes) {
        setConfig(configRes);
      }
      // Handle trailing stops response - use active_trails instead of active_stops
      setTrailingStops(trailingRes?.active_trails || trailingRes?.active_stops || []);
      // Handle performance response
      if (perfRes?.data) {
        setPerformance(perfRes.data);
      } else if (perfRes) {
        setPerformance(perfRes);
      }
    } catch (err: any) {
      setError(err?.message || 'Erro ao carregar estrategias');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const timer = setInterval(loadData, 30000); // Atualiza a cada 30s
    return () => clearInterval(timer);
  }, []);

  const StrategyBadge: React.FC<{ enabled: boolean; name: string; icon: React.ReactNode }> = ({ enabled, name, icon }) => (
    <div className={`flex items-center gap-2 p-3 rounded-lg ${
      enabled ? 'bg-green-50 border border-green-200' : 'bg-slate-50 border border-slate-200'
    }`}>
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
        enabled ? 'bg-green-100' : 'bg-slate-100'
      }`}>
        {icon}
      </div>
      <div className="flex-1">
        <p className={`text-sm font-bold ${enabled ? 'text-green-700' : 'text-slate-500'}`}>
          {name}
        </p>
      </div>
      {enabled ? (
        <CheckCircle className="w-4 h-4 text-green-500" />
      ) : (
        <XCircle className="w-4 h-4 text-slate-400" />
      )}
    </div>
  );

  return (
    <div className="glass-card overflow-hidden">
      <div className="p-4 border-b border-slate-200/50 bg-gradient-to-r from-orange-50/50 to-amber-50/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-600 to-amber-600 flex items-center justify-center shadow-lg shadow-orange-500/30">
              <Crosshair className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900">Advanced Strategies</h3>
              <p className="text-xs text-slate-500 font-medium">Sniper, Pyramid, DCA & Smart TS</p>
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

        {/* Strategy Toggles */}
        {config && (
          <div className="grid grid-cols-2 gap-3">
            <StrategyBadge
              enabled={config.sniper_enabled}
              name="Sniper Mode"
              icon={<Crosshair className={`w-4 h-4 ${config.sniper_enabled ? 'text-green-600' : 'text-slate-400'}`} />}
            />
            <StrategyBadge
              enabled={config.pyramid_enabled}
              name="Pyramiding"
              icon={<Layers className={`w-4 h-4 ${config.pyramid_enabled ? 'text-green-600' : 'text-slate-400'}`} />}
            />
            <StrategyBadge
              enabled={config.dca_enabled}
              name="DCA Recovery"
              icon={<ArrowDownCircle className={`w-4 h-4 ${config.dca_enabled ? 'text-green-600' : 'text-slate-400'}`} />}
            />
            <StrategyBadge
              enabled={config.breakeven_enabled}
              name="Breakeven"
              icon={<Shield className={`w-4 h-4 ${config.breakeven_enabled ? 'text-green-600' : 'text-slate-400'}`} />}
            />
          </div>
        )}

        {/* Execution Mode */}
        {config && (
          <div className="p-4 bg-gradient-to-r from-slate-50 to-orange-50 rounded-xl border border-slate-200">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-bold text-slate-600 uppercase">Modos de Execucao</span>
              <Activity className="w-4 h-4 text-orange-600" />
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-xs text-slate-500">Execution</p>
                <p className="font-bold text-slate-900">{config.default_execution_mode || 'DEFAULT'}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Trailing</p>
                <p className="font-bold text-slate-900">{config.default_trailing_mode || 'ATR'}</p>
              </div>
            </div>
          </div>
        )}

        {/* Active Trailing Stops */}
        {trailingStops.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-bold text-slate-600 uppercase">Trailing Stops Ativos</span>
              <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded-lg font-bold">
                {trailingStops.length}
              </span>
            </div>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {trailingStops.map((ts, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200">
                  <div>
                    <span className="font-bold text-green-800">{ts.symbol || 'N/A'}</span>
                    <span className="text-xs text-green-600 ml-2">({ts.mode || 'N/A'})</span>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-green-700">
                      Peak: {(ts.peak_price || 0).toFixed(4)}
                    </p>
                    <p className="text-xs text-green-600">
                      Callback: {(ts.callback_pct || 0).toFixed(2)}%
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Performance Summary */}
        {performance && (
          <div className="p-4 bg-gradient-to-r from-slate-50 to-purple-50 rounded-xl border border-slate-200">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-bold text-slate-600 uppercase">Performance</span>
              <TrendingUp className="w-4 h-4 text-purple-600" />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <p className="text-xs text-slate-500">Trades</p>
                <p className="text-lg font-bold text-slate-900">{performance.total_trades || 0}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Win Rate</p>
                <p className={`text-lg font-bold ${(performance.win_rate || 0) >= 50 ? 'text-green-600' : 'text-red-600'}`}>
                  {(performance.win_rate || 0).toFixed(1)}%
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">P&L Total</p>
                <p className={`text-lg font-bold ${(performance.total_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {(performance.total_pnl || 0) >= 0 ? '+' : ''}{(performance.total_pnl || 0).toFixed(2)}
                </p>
              </div>
            </div>
            {performance.best_strategy && (
              <div className="mt-3 flex items-center gap-2 text-xs text-purple-600">
                <TrendingUp className="w-3 h-3" />
                <span>Melhor: {performance.best_strategy}</span>
              </div>
            )}
          </div>
        )}

        {/* Strategy Parameters */}
        {config && (config.pyramid_max_entries || config.dca_max_entries || config.trailing_stop_pct) && (
          <div className="grid grid-cols-3 gap-2 text-xs">
            {config.pyramid_max_entries && (
              <div className="p-2 bg-slate-50 rounded-lg text-center">
                <p className="text-slate-500">Pyramid Max</p>
                <p className="font-bold text-slate-900">{config.pyramid_max_entries}</p>
              </div>
            )}
            {config.dca_max_entries && (
              <div className="p-2 bg-slate-50 rounded-lg text-center">
                <p className="text-slate-500">DCA Max</p>
                <p className="font-bold text-slate-900">{config.dca_max_entries}</p>
              </div>
            )}
            {config.trailing_stop_pct && (
              <div className="p-2 bg-slate-50 rounded-lg text-center">
                <p className="text-slate-500">Trail %</p>
                <p className="font-bold text-slate-900">{config.trailing_stop_pct}%</p>
              </div>
            )}
          </div>
        )}

        {loading && !config && (
          <div className="flex items-center justify-center p-8">
            <RefreshCw className="w-6 h-6 text-orange-500 animate-spin" />
          </div>
        )}
      </div>
    </div>
  );
};

export default AdvancedStrategiesCard;
