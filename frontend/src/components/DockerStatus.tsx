import React, { useEffect, useMemo, useState } from "react";
import { getComposeStatus } from "../services/api";

type Item = { name?: string; status?: string; ports?: string; raw?: string };

export default function DockerStatus() {
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<Item[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notAvailable, setNotAvailable] = useState<boolean>(false);

  // Classificação visual de status do container
  const statusKind = (s?: string) => {
    const str = String(s || "").toLowerCase();
    if (str.includes("up") || str.includes("healthy")) return "ok";
    if (str.includes("restarting") || str.includes("starting")) return "warn";
    if (str.includes("exited") || str.includes("unhealthy") || str.includes("dead")) return "err";
    return "info";
  };

  // Contadores por tipo (para resumo)
  const counters = useMemo(() => {
    const c = { ok: 0, warn: 0, err: 0, info: 0 };
    for (const it of items) {
      c[statusKind(it.status || it.raw)]++;
    }
    return c;
  }, [items]);

  const load = async () => {
    setError(null);
    try {
      const res = await getComposeStatus();
      setItems(res?.items || []);
      setNotAvailable(false);
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.message || "Falha ao consultar docker ps";
      const code = e?.response?.status;
      setNotAvailable(code === 501 || /Docker não disponível/i.test(String(detail)));
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    if (notAvailable) return; // não agendar polling quando o Docker não está disponível no host
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, [notAvailable]);

  return (
    <section className="card">
      <h3>Docker Compose - Status</h3>

      <div className="row" style={{ marginBottom: 8 }}>
        <button className="btn ghost" onClick={load} disabled={loading || notAvailable}>
          Atualizar
        </button>
        <span className="small">
          {notAvailable
            ? "Recurso indisponível neste ambiente (sem acesso ao Docker do host)"
            : "Atualiza automaticamente a cada 10s • Requer acesso ao Docker no host da API"}
        </span>
      </div>

      {loading ? (
        <div className="small">Carregando...</div>
      ) : notAvailable ? (
        <div className="badge err">
          Indisponível: Docker não disponível no ambiente da API. Este painel fica oculto quando a API não tem acesso ao Docker do host.
        </div>
      ) : error ? (
        <div className="badge err">
          Indisponível: {error}. Verifique o acesso ao Docker (host) ou utilize o supervisor.py para inspecionar via terminal.
        </div>
      ) : items.length === 0 ? (
        <div className="small">Nenhum container encontrado.</div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <div className="row small" style={{ marginBottom: 8 }}>
            <span className="badge ok">Up: {counters.ok}</span>
            <span className="badge warn">Restarting: {counters.warn}</span>
            <span className="badge err">Exited: {counters.err}</span>
            <span className="badge info">Outros: {counters.info}</span>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Status</th>
                <th>Portas</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it, idx) => (
                <tr key={idx}>
                  <td>{it.name || "—"}</td>
                  <td>
                    <span className={`badge ${statusKind(it.status || it.raw)}`}>
                      {it.status || it.raw || "—"}
                    </span>
                  </td>
                  <td>{it.ports || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
