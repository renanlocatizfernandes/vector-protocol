import React, { useEffect, useMemo, useRef, useState } from "react";
import { getLogs } from "../services/api";

type Preset = {
  label: string;
  value: string;
};

const DEFAULT_PRESETS: Preset[] = [
  { label: "API (api_YYYYMMDD.log)", value: "api" },
  { label: "Trading Routes", value: "trading_routes" },
  { label: "Market Routes", value: "market_routes" },
  { label: "Autonomous Bot", value: "autonomous_bot" },
  { label: "Order Executor", value: "order_executor" },
  { label: "Position Monitor", value: "position_monitor" },
  { label: "Signal Generator", value: "signal_generator" }
];

export default function LogsViewer({
  presets = DEFAULT_PRESETS
}: {
  presets?: Preset[];
}) {
  const lastRefetch = useRef<number | null>(null);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);
  const inFlight = useRef<boolean>(false);
  const [component, setComponent] = useState<string>(presets[0]?.value || "api");
  const [tail, setTail] = useState<number>(300);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [intervalMs, setIntervalMs] = useState<number>(5000);

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lines, setLines] = useState<string[]>([]);
  const [file, setFile] = useState<string>("");

  const preRef = useRef<HTMLPreElement | null>(null);
  const [stickToBottom, setStickToBottom] = useState<boolean>(true);
  const [wrap, setWrap] = useState<boolean>(true);
  const [fontSize, setFontSize] = useState<number>(12);

  const fetchLogs = async (opts?: { silent?: boolean }) => {
    if (inFlight.current) return; // evita requisições concorrentes/overlap
    inFlight.current = true;
    if (!opts?.silent) setLoading(true);
    setError(null);
    try {
      const res = await getLogs(component, tail);
      setLines(res.lines || []);
      setFile(res.file || "");
      setLastUpdated(Date.now());
      // Se o usuário não rolou para cima, manter scroll no fim
      if (stickToBottom) {
        requestAnimationFrame(() => {
          preRef.current?.scrollTo({
            top: preRef.current.scrollHeight,
            behavior: "smooth"
          });
        });
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || "Falha ao carregar logs");
    } finally {
      if (!opts?.silent) setLoading(false);
      inFlight.current = false;
    }
  };

  // Auto refresh
  useEffect(() => {
    fetchLogs();
    if (!autoRefresh) return;
    const id = setInterval(() => {
      lastRefetch.current = Date.now();
      fetchLogs({ silent: true });
    }, Math.max(1000, intervalMs));
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [component, tail, autoRefresh, intervalMs]);

  const lineCount = useMemo(() => lines.length, [lines]);

  const handleScroll = () => {
    if (!preRef.current) return;
    const el = preRef.current;
    const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 10;
    setStickToBottom(atBottom);
  };

  // Utilitários de UX
  const copyLogs = () => {
    const text = lines.join("\n");
    if (!text) return;
    navigator.clipboard?.writeText(text).catch(() => {});
  };

  const downloadLogs = () => {
    const text = lines.join("\n");
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = (file || `logs-${component}.log`);
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="card">
      <h3>Logs em Tempo Quase Real</h3>

      <div className="row" style={{ gap: 10, alignItems: "center", marginBottom: 8 }}>
        <div style={{ minWidth: 220 }}>
          <label>Componente (prefixo do arquivo)</label>
          <div className="row" style={{ gap: 8 }}>
            <select value={component} onChange={(e) => setComponent(e.target.value)} style={{ flex: 1 }}>
              {presets.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
            <input
              placeholder="custom"
              value={component}
              onChange={(e) => setComponent(e.target.value)}
              style={{ width: 120 }}
              title="Prefixo customizado (ex.: api, trading_routes, etc.)"
            />
          </div>
        </div>

        <div>
          <label>Tail (linhas)</label>
          <input
            type="number"
            min={50}
            max={5000}
            value={tail}
            onChange={(e) => setTail(Number(e.target.value) || 300)}
            style={{ width: 120 }}
          />
        </div>

        <div>
          <label>Auto refresh</label>
          <div className="row" style={{ alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
            <span className="small">a cada</span>
            <input
              type="number"
              min={1000}
              step={500}
              value={intervalMs}
              onChange={(e) => setIntervalMs(Number(e.target.value) || 5000)}
              style={{ width: 100 }}
              disabled={!autoRefresh}
              title="Intervalo em ms"
            />
            <span className="small">ms</span>
          </div>
        </div>

        <div className="row" style={{ gap: 8 }}>
          <button className="btn" onClick={() => fetchLogs()} disabled={loading}>Atualizar</button>
          <button className="btn ghost" onClick={() => setStickToBottom(true)} title="Fixar no fim do log">Seguir fim</button>
          <button className="btn ghost" onClick={copyLogs} title="Copiar para a área de transferência">Copiar</button>
          <button className="btn ghost" onClick={downloadLogs} title="Baixar .log">Baixar</button>
          <button className="btn ghost" onClick={() => setWrap((w) => !w)} title="Alternar quebra de linha">{wrap ? "No-wrap" : "Wrap"}</button>
          <div className="row" style={{ gap: 4 }}>
            <button className="btn ghost" onClick={() => setFontSize((v) => Math.max(10, v - 1))} title="Fonte -">A-</button>
            <button className="btn ghost" onClick={() => setFontSize((v) => Math.min(18, v + 1))} title="Fonte +">A+</button>
          </div>
        </div>
      </div>

      <div className="small" style={{ marginBottom: 6 }}>
        Arquivo: {file || "—"} • Linhas: {lineCount} {loading ? "• carregando..." : ""}
        {lastUpdated ? ` • Atualizado às ${new Date(lastUpdated).toLocaleTimeString()}` : ""}
      </div>

      {error ? (
        <div className="badge err">{error}</div>
      ) : (
        <pre
          ref={preRef}
          onScroll={handleScroll}
          style={{
            background: "var(--panel-2)",
            border: "1px solid var(--border)",
            borderRadius: 10,
            padding: 12,
            height: 360,
            overflow: "auto",
            whiteSpace: wrap ? "pre-wrap" : "pre",
            fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
            fontSize: fontSize,
            lineHeight: 1.35
          }}
        >
{lines.join("\n")}
        </pre>
      )}
    </section>
  );
}
