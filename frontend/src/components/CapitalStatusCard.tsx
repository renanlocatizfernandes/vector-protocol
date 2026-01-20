import React, { useEffect, useState } from 'react';
import { Wallet, Shield, TrendingDown, AlertTriangle, CheckCircle, RefreshCw, AlertCircle } from 'lucide-react';
import { getCapitalState, getMarginStatus, getDrawdownStatus, type CapitalState, type MarginStatus, type DrawdownStatus } from '../services/api';

export const CapitalStatusCard: React.FC = () => {
  const [capitalState, setCapitalState] = useState<CapitalState | null>(null);
  const [marginStatus, setMarginStatus] = useState<MarginStatus | null>(null);
  const [drawdown, setDrawdown] = useState<DrawdownStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [capitalRes, marginRes, drawdownRes] = await Promise.all([
        getCapitalState().catch(() => null),
        getMarginStatus().catch(() => null),
        getDrawdownStatus().catch(() => null)
      ]);
      // Handle nested data format: { status: "success", data: {...} }
      const capitalData = capitalRes?.data || capitalRes;
      const marginData = marginRes?.data || marginRes;
      const drawdownData = drawdownRes?.data || drawdownRes;

      if (capitalData) {
        setCapitalState({
          balance: capitalData.total_wallet_balance || capitalData.balance || 0,
          equity: capitalData.total_equity || capitalData.equity || 0,
          margin_used: capitalData.margin_used || 0,
          margin_used_pct: capitalData.margin_used_pct || 0,
          positions_count: capitalData.num_positions || capitalData.positions_count || 0,
          max_positions: capitalData.max_positions || 15,
          zone: capitalData.capital_status === 'healthy' ? 'GREEN_ZONE' :
                capitalData.capital_status === 'warning' ? 'YELLOW_ZONE' :
                capitalData.capital_status === 'danger' ? 'RED_ZONE' :
                capitalData.zone || 'UNKNOWN',
          can_open_new: capitalData.capital_status === 'healthy' || capitalData.can_open_new !== false,
          safety_buffer_pct: capitalData.margin_free_pct || capitalData.safety_buffer_pct || 0
        });
      }
      if (marginData) {
        setMarginStatus({
          total_wallet_balance: marginData.total_wallet_balance || 0,
          total_margin_used: marginData.margin_used || marginData.total_margin_used || 0,
          margin_used_pct: marginData.margin_used_pct || 0,
          available_balance: marginData.available_balance || 0,
          unrealized_pnl: marginData.unrealized_pnl || 0
        });
      }
      if (drawdownData) {
        setDrawdown({
          current_drawdown_pct: drawdownData.current_drawdown_pct || 0,
          max_drawdown_pct: drawdownData.max_drawdown_pct || 0,
          peak_balance: drawdownData.peak_balance || 0,
          current_balance: drawdownData.current_balance || 0,
          drawdown_level: drawdownData.drawdown_level || 'SAFE',
          recovery_needed_pct: drawdownData.recovery_needed_pct || 0
        });
      }
    } catch (err: any) {
      setError(err?.message || 'Erro ao carregar dados de capital');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const timer = setInterval(loadData, 30000); // Atualiza a cada 30s
    return () => clearInterval(timer);
  }, []);

  const getZoneColor = (zone: string | undefined) => {
    if (!zone) return { bg: 'bg-slate-100', text: 'text-slate-600', border: 'border-slate-200' };
    if (zone === 'GREEN_ZONE' || zone === 'GREEN') return { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-300' };
    if (zone === 'YELLOW_ZONE' || zone === 'YELLOW') return { bg: 'bg-yellow-100', text: 'text-yellow-700', border: 'border-yellow-300' };
    if (zone === 'RED_ZONE' || zone === 'RED') return { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-300' };
    return { bg: 'bg-slate-100', text: 'text-slate-600', border: 'border-slate-200' };
  };

  const getDrawdownColor = (level: string | undefined) => {
    if (!level) return 'text-slate-500';
    if (level === 'SAFE' || level === 'LOW') return 'text-green-600';
    if (level === 'WARNING' || level === 'MEDIUM') return 'text-yellow-600';
    if (level === 'DANGER' || level === 'HIGH' || level === 'CRITICAL') return 'text-red-600';
    return 'text-slate-600';
  };

  const zone = capitalState?.zone || marginStatus?.zone;
  const zoneColors = getZoneColor(zone);

  return (
    <div className="glass-card overflow-hidden">
      <div className="p-4 border-b border-slate-200/50 bg-gradient-to-r from-emerald-50/50 to-green-50/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-600 to-green-600 flex items-center justify-center shadow-lg shadow-emerald-500/30">
              <Wallet className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900">Capital & Leverage Manager</h3>
              <p className="text-xs text-slate-500 font-medium">Gestao Inteligente de Margem</p>
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

        {/* Capital Zone */}
        {zone && (
          <div className={`p-4 rounded-xl border-2 ${zoneColors.bg} ${zoneColors.border}`}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-bold text-slate-600 uppercase">Zona de Capital</span>
              <div className="flex items-center gap-2">
                {capitalState?.can_open_new ? (
                  <CheckCircle className="w-4 h-4 text-green-500" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-red-500" />
                )}
                <span className={`text-sm font-bold ${zoneColors.text}`}>
                  {zone.replace('_ZONE', '').replace('_', ' ')}
                </span>
              </div>
            </div>
            <p className="text-xs text-slate-600">
              {capitalState?.can_open_new
                ? 'Sistema pode abrir novas posicoes'
                : 'Novas entradas bloqueadas - gerencie o risco'
              }
            </p>
          </div>
        )}

        {/* Margin Stats */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 bg-slate-50 rounded-lg">
            <p className="text-xs text-slate-500 mb-1">Balance Total</p>
            <p className="text-lg font-bold text-slate-900">
              ${(marginStatus?.total_wallet_balance || capitalState?.balance || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}
            </p>
          </div>
          <div className="p-3 bg-slate-50 rounded-lg">
            <p className="text-xs text-slate-500 mb-1">Disponivel</p>
            <p className="text-lg font-bold text-green-600">
              ${(marginStatus?.available_balance || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}
            </p>
          </div>
        </div>

        {/* Margin Usage Bar */}
        {(capitalState?.margin_used_pct !== undefined || marginStatus?.margin_used_pct !== undefined) && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600 font-medium">Margem Utilizada</span>
              <span className={`font-bold ${
                (capitalState?.margin_used_pct || marginStatus?.margin_used_pct || 0) > 70 ? 'text-red-600' :
                (capitalState?.margin_used_pct || marginStatus?.margin_used_pct || 0) > 50 ? 'text-yellow-600' :
                'text-green-600'
              }`}>
                {(capitalState?.margin_used_pct || marginStatus?.margin_used_pct || 0).toFixed(1)}%
              </span>
            </div>
            <div className="h-3 bg-slate-200 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all ${
                  (capitalState?.margin_used_pct || marginStatus?.margin_used_pct || 0) > 70 ? 'bg-red-500' :
                  (capitalState?.margin_used_pct || marginStatus?.margin_used_pct || 0) > 50 ? 'bg-yellow-500' :
                  'bg-green-500'
                }`}
                style={{ width: `${Math.min(100, capitalState?.margin_used_pct || marginStatus?.margin_used_pct || 0)}%` }}
              ></div>
            </div>
          </div>
        )}

        {/* Positions Info */}
        {capitalState && (
          <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-medium text-blue-800">Posicoes Abertas</span>
            </div>
            <div className="text-right">
              <span className="text-lg font-bold text-blue-900">
                {capitalState.positions_count}/{capitalState.max_positions}
              </span>
            </div>
          </div>
        )}

        {/* Drawdown Status */}
        {drawdown && (
          <div className="p-4 bg-gradient-to-r from-slate-50 to-red-50 rounded-xl border border-slate-200">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-bold text-slate-600 uppercase">Drawdown</span>
              <span className={`text-sm font-bold px-2 py-1 rounded-lg ${
                drawdown.drawdown_level === 'SAFE' ? 'bg-green-100 text-green-700' :
                drawdown.drawdown_level === 'WARNING' ? 'bg-yellow-100 text-yellow-700' :
                'bg-red-100 text-red-700'
              }`}>
                {drawdown.drawdown_level}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-slate-500">Atual</p>
                <p className={`text-lg font-bold ${getDrawdownColor(drawdown.drawdown_level)}`}>
                  -{(drawdown.current_drawdown_pct || 0).toFixed(2)}%
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Maximo</p>
                <p className="text-lg font-bold text-red-600">
                  -{(drawdown.max_drawdown_pct || 0).toFixed(2)}%
                </p>
              </div>
            </div>
            {(drawdown.recovery_needed_pct || 0) > 0 && (
              <div className="mt-3 flex items-center gap-2 text-xs text-slate-600">
                <TrendingDown className="w-3 h-3" />
                <span>Precisa {(drawdown.recovery_needed_pct || 0).toFixed(1)}% para recuperar</span>
              </div>
            )}
          </div>
        )}

        {/* Safety Buffer */}
        {capitalState && capitalState.safety_buffer_pct !== undefined && (
          <div className="flex items-center justify-between p-3 bg-emerald-50 rounded-lg border border-emerald-200">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-emerald-600" />
              <span className="text-sm font-medium text-emerald-800">Safety Buffer</span>
            </div>
            <span className="text-lg font-bold text-emerald-900">
              {(capitalState.safety_buffer_pct || 0).toFixed(1)}%
            </span>
          </div>
        )}

        {loading && !capitalState && !marginStatus && (
          <div className="flex items-center justify-center p-8">
            <RefreshCw className="w-6 h-6 text-emerald-500 animate-spin" />
          </div>
        )}
      </div>
    </div>
  );
};

export default CapitalStatusCard;
