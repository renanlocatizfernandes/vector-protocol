import React, { useEffect, useMemo, useState } from "react";
import { getComposeStatus } from "../services/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { RefreshCw, Server } from "lucide-react";
import { cn } from "@/lib/utils";

type Item = { name?: string; status?: string; ports?: string; raw?: string };

export default function DockerStatus() {
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<Item[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notAvailable, setNotAvailable] = useState<boolean>(false);

  const statusKind = (s?: string) => {
    const str = String(s || "").toLowerCase();
    if (str.includes("up") || str.includes("healthy")) return "ok";
    if (str.includes("restarting") || str.includes("starting")) return "warn";
    if (str.includes("exited") || str.includes("unhealthy") || str.includes("dead")) return "err";
    return "info";
  };

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
      setNotAvailable(code === 501 || /Docker nao disponivel/i.test(String(detail)));
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    if (notAvailable) return;
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, [notAvailable]);

  const statusClass = (kind: string) => {
    if (kind === "ok") return "bg-success/10 text-success border-success/20";
    if (kind === "warn") return "bg-warning/10 text-warning border-warning/20";
    if (kind === "err") return "bg-danger/10 text-danger border-danger/20";
    return "bg-white/5 text-muted-foreground border-white/10";
  };

  return (
    <Card className="glass-card border-white/10">
      <CardHeader className="border-b border-white/10 pb-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <CardTitle className="flex items-center gap-2 text-white">
            <Server className="w-5 h-5 text-primary" /> Docker Compose
          </CardTitle>
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={load} disabled={loading || notAvailable} className="border-white/10">
              <RefreshCw className={cn("mr-2 h-4 w-4", loading && "animate-spin")} /> Refresh
            </Button>
            <span className="text-xs text-muted-foreground">
              {notAvailable
                ? "Indisponivel neste ambiente"
                : "Atualiza automaticamente a cada 10s"}
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-6 space-y-4">
        {loading ? (
          <div className="text-sm text-muted-foreground">Carregando...</div>
        ) : notAvailable ? (
          <div className="text-sm text-muted-foreground">
            Docker nao disponivel no ambiente da API. Este painel requer acesso ao Docker do host.
          </div>
        ) : error ? (
          <div className="text-sm text-danger">
            Indisponivel: {error}
          </div>
        ) : items.length === 0 ? (
          <div className="text-sm text-muted-foreground">Nenhum container encontrado.</div>
        ) : (
          <>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline" className={statusClass("ok")}>Up: {counters.ok}</Badge>
              <Badge variant="outline" className={statusClass("warn")}>Restarting: {counters.warn}</Badge>
              <Badge variant="outline" className={statusClass("err")}>Exited: {counters.err}</Badge>
              <Badge variant="outline" className={statusClass("info")}>Outros: {counters.info}</Badge>
            </div>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nome</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Portas</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((it, idx) => {
                    const kind = statusKind(it.status || it.raw);
                    return (
                      <TableRow key={idx}>
                        <TableCell className="font-mono text-white">{it.name || "-"}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className={statusClass(kind)}>
                            {it.status || it.raw || "-"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">{it.ports || "-"}</TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
