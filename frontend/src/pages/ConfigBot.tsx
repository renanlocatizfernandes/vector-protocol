import React, { useEffect, useState } from "react";
import {
  getConfig,
  getBotStatus,
  updateBotConfig,
  testTelegram,
  type ConfigResponse,
  type BotStatus
} from "../services/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Settings, Save, Send, AlertTriangle, CheckCircle } from "lucide-react";
import { cn } from "@/lib/utils";

function Field({
  label,
  children
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium">{label}</label>
      {children}
    </div>
  );
}

export default function ConfigBot() {
  const [loading, setLoading] = useState(true);
  const [cfg, setCfg] = useState<ConfigResponse | null>(null);
  const [bot, setBot] = useState<BotStatus | null>(null);

  const [scanIntervalMin, setScanIntervalMin] = useState<number | "">("");
  const [minScore, setMinScore] = useState<number | "">("");
  const [maxPositions, setMaxPositions] = useState<number | "">("");

  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [c, b] = await Promise.all([
          getConfig().catch(() => null),
          getBotStatus().catch(() => null),
        ]);
        if (c) setCfg(c);
        if (b) {
          setBot(b);
          setScanIntervalMin(b?.scan_interval ? Math.round((b.scan_interval as number) / 60) : "");
          setMinScore(typeof b?.min_score === "number" ? (b.min_score as number) : "");
          setMaxPositions(typeof b?.max_positions === "number" ? (b.max_positions as number) : "");
        }
      } catch {
        setMsg({ kind: "err", text: "Falha ao carregar configuração" });
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const onSave = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const params: Record<string, number> = {};
      if (scanIntervalMin !== "" && !Number.isNaN(Number(scanIntervalMin))) params.scan_interval_minutes = Number(scanIntervalMin);
      if (minScore !== "" && !Number.isNaN(Number(minScore))) params.min_score = Number(minScore);
      if (maxPositions !== "" && !Number.isNaN(Number(maxPositions))) params.max_positions = Number(maxPositions);

      const res = await updateBotConfig(params);
      setMsg({ kind: "ok", text: res?.message || "Config atualizada" });
      const b = await getBotStatus().catch(() => null);
      if (b) setBot(b);
    } catch (e: any) {
      setMsg({ kind: "err", text: e?.message || "Erro ao salvar" });
    } finally {
      setBusy(false);
    }
  };

  const onTestTelegram = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const res = await testTelegram();
      setMsg({ kind: "ok", text: res?.message || "Telegram OK" });
    } catch (e: any) {
      setMsg({ kind: "err", text: e?.message || "Erro ao enviar teste" });
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return <div className="animate-pulse h-64 bg-muted rounded-lg"></div>;
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* HERO */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-primary">Configuração do Bot</h1>
          <p className="text-muted-foreground">Ajuste as principais variáveis de execução em runtime.</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={bot?.running ? "success" : "destructive"} className="flex gap-1 items-center px-3 py-1">
            <div className={cn("h-2 w-2 rounded-full", bot?.running ? "bg-green-500 animate-pulse" : "bg-red-500")} />
            {bot?.running ? "Rodando" : "Parado"}
          </Badge>
          <Button variant="outline" size="sm" onClick={onTestTelegram} disabled={busy}>
            <Send className="mr-2 h-4 w-4" /> Testar Telegram
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Painel de Configurações do backend */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" /> Configurações Globais
            </CardTitle>
            <CardDescription>Valores carregados do backend (env/settings).</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col p-3 bg-muted/50 rounded-lg">
                <span className="text-xs text-muted-foreground">Max Positions</span>
                <span className="font-mono font-bold">{cfg?.max_positions ?? "—"}</span>
              </div>
              <div className="flex flex-col p-3 bg-muted/50 rounded-lg">
                <span className="text-xs text-muted-foreground">Risk Per Trade</span>
                <span className="font-mono font-bold">{cfg?.risk_per_trade ?? "—"}</span>
              </div>
              <div className="flex flex-col p-3 bg-muted/50 rounded-lg">
                <span className="text-xs text-muted-foreground">Max Portfolio Risk</span>
                <span className="font-mono font-bold">{cfg?.max_portfolio_risk ?? "—"}</span>
              </div>
              <div className="flex flex-col p-3 bg-muted/50 rounded-lg">
                <span className="text-xs text-muted-foreground">Default Leverage</span>
                <span className="font-mono font-bold">{cfg?.default_leverage ?? "—"}</span>
              </div>
              <div className="flex flex-col p-3 bg-muted/50 rounded-lg col-span-2">
                <span className="text-xs text-muted-foreground">Mode</span>
                <span className={cn("font-mono font-bold", cfg?.testnet ? "text-yellow-500" : "text-green-500")}>
                  {cfg?.testnet ? "TESTNET" : "PRODUCTION"}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Form runtime refinado */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" /> Runtime Config
            </CardTitle>
            <CardDescription>Ajustes dinâmicos do loop do bot.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2 mb-4">
              <Badge variant="outline">dry_run: {String(bot?.dry_run ?? "—")}</Badge>
              <Badge variant="outline">min_score: {String(bot?.min_score ?? "—")}</Badge>
              <Badge variant="outline">max_positions: {String(bot?.max_positions ?? "—")}</Badge>
              <Badge variant="outline">scan: {bot?.scan_interval ? Math.round((bot?.scan_interval as number) / 60) + "m" : "—"}</Badge>
            </div>

            <div className="grid grid-cols-1 gap-4">
              <Field label="Scan interval (min)">
                <Input
                  type="number"
                  min={1}
                  value={scanIntervalMin}
                  onChange={(e) => setScanIntervalMin(e.target.value === "" ? "" : Number(e.target.value))}
                />
              </Field>
              <Field label="Min score">
                <Input
                  type="number"
                  min={0}
                  max={100}
                  value={minScore}
                  onChange={(e) => setMinScore(e.target.value === "" ? "" : Number(e.target.value))}
                />
              </Field>
              <Field label="Max positions">
                <Input
                  type="number"
                  min={1}
                  value={maxPositions}
                  onChange={(e) => setMaxPositions(e.target.value === "" ? "" : Number(e.target.value))}
                />
              </Field>
            </div>

            <div className="pt-4 flex items-center justify-between">
              <Button onClick={onSave} disabled={busy}>
                <Save className="mr-2 h-4 w-4" /> Salvar Alterações
              </Button>

              {msg && (
                <div className={cn(
                  "flex items-center gap-2 text-sm font-medium",
                  msg.kind === "ok" ? "text-green-500" : "text-red-500"
                )}>
                  {msg.kind === "ok" ? <CheckCircle className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
                  {msg.text}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Notas */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Notas Importantes</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1">
            <li>As configurações de runtime são aplicadas imediatamente sem reiniciar o serviço.</li>
            <li>Mantenha <strong>TESTNET=True</strong> até validar a estratégia; depois troque para produção com cautela.</li>
            <li>Use a página <strong>Supervisor</strong> para monitorar a saúde dos containers e logs do sistema.</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
