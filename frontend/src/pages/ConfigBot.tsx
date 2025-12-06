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
import { Settings, Save, Send, AlertTriangle, CheckCircle, Sliders, Activity, Shield, Terminal } from "lucide-react";
import { cn } from "@/lib/utils";

function Field({
  label,
  children
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{label}</label>
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
        setMsg({ kind: "err", text: "Failed to load configuration" });
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
      setMsg({ kind: "ok", text: res?.message || "Config Updated" });
      const b = await getBotStatus().catch(() => null);
      if (b) setBot(b);
    } catch (e: any) {
      setMsg({ kind: "err", text: e?.message || "Error Saving" });
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
      setMsg({ kind: "err", text: e?.message || "Error sending test" });
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-10 w-1/3 bg-dark-800 animate-pulse rounded-md"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="h-64 bg-dark-800 animate-pulse rounded-xl"></div>
          <div className="h-64 bg-dark-800 animate-pulse rounded-xl"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* HERO */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Bot Configuration</h1>
          <p className="text-muted-foreground">Adjust runtime variables and monitor system parameters.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className={cn(
            "px-3 py-1.5 rounded-full border text-xs font-bold flex items-center gap-2",
            bot?.running
              ? "bg-green-500/10 text-green-500 border-green-500/20"
              : "bg-red-500/10 text-red-500 border-red-500/20"
          )}>
            <div className={cn("h-2 w-2 rounded-full", bot?.running ? "bg-green-500 animate-pulse" : "bg-red-500")} />
            {bot?.running ? "ENGINE ONLINE" : "ENGINE OFFLINE"}
          </div>
          <Button variant="outline" size="sm" onClick={onTestTelegram} disabled={busy} className="border-dark-700 hover:bg-dark-800">
            <Send className="mr-2 h-4 w-4" /> Test Telegram
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Runtime Config */}
        <Card className="border-primary/20 bg-dark-900/40 backdrop-blur-xl shadow-[0_0_30px_rgba(0,240,255,0.05)]">
          <CardHeader className="border-b border-dark-700/50 pb-4">
            <CardTitle className="flex items-center gap-2 text-primary">
              <Sliders className="h-5 w-5" /> Runtime Configuration
            </CardTitle>
            <CardDescription>Dynamic adjustments. No restart required.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 pt-6">
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline" className="bg-dark-800 text-muted-foreground border-dark-700">Dry Run: {String(bot?.dry_run ?? "—")}</Badge>
              <Badge variant="outline" className="bg-dark-800 text-muted-foreground border-dark-700">Current Score: {String(bot?.min_score ?? "—")}</Badge>
              <Badge variant="outline" className="bg-dark-800 text-muted-foreground border-dark-700">Positions: {String(bot?.max_positions ?? "—")}</Badge>
              <Badge variant="outline" className="bg-dark-800 text-muted-foreground border-dark-700">Scan: {bot?.scan_interval ? Math.round((bot?.scan_interval as number) / 60) + "m" : "—"}</Badge>
            </div>

            <div className="grid grid-cols-1 gap-5">
              <Field label="Scan Interval (minutes)">
                <div className="relative">
                  <Input
                    type="number"
                    min={1}
                    className="pl-9 bg-dark-800 border-dark-700 focus:border-primary/50"
                    value={scanIntervalMin}
                    onChange={(e) => setScanIntervalMin(e.target.value === "" ? "" : Number(e.target.value))}
                  />
                  <Activity className="w-4 h-4 text-muted-foreground absolute left-3 top-2.5" />
                </div>
              </Field>
              <Field label="Minimum Score Threshold">
                <div className="relative">
                  <Input
                    type="number"
                    min={0}
                    max={100}
                    className="pl-9 bg-dark-800 border-dark-700 focus:border-primary/50"
                    value={minScore}
                    onChange={(e) => setMinScore(e.target.value === "" ? "" : Number(e.target.value))}
                  />
                  <Shield className="w-4 h-4 text-muted-foreground absolute left-3 top-2.5" />
                </div>
              </Field>
              <Field label="Max Concurrent Positions">
                <Input
                  type="number"
                  min={1}
                  className="bg-dark-800 border-dark-700 focus:border-primary/50"
                  value={maxPositions}
                  onChange={(e) => setMaxPositions(e.target.value === "" ? "" : Number(e.target.value))}
                />
              </Field>
            </div>

            <div className="pt-2 flex items-center justify-between border-t border-dark-700/50 mt-4">
              <Button onClick={onSave} disabled={busy} className="px-6">
                {busy ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" /> : <Save className="mr-2 h-4 w-4" />}
                Apply Changes
              </Button>

              {msg && (
                <div className={cn(
                  "flex items-center gap-2 text-sm font-medium animate-in slide-in-from-right-4",
                  msg.kind === "ok" ? "text-green-500" : "text-red-500"
                )}>
                  {msg.kind === "ok" ? <CheckCircle className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
                  {msg.text}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Static Config */}
        <Card className="border-dark-700/50 bg-dark-900/20">
          <CardHeader className="border-b border-dark-700/50 pb-4">
            <CardTitle className="flex items-center gap-2 text-white">
              <Terminal className="h-5 w-5 text-muted-foreground" /> Environment Settings
            </CardTitle>
            <CardDescription>Loaded from .env / startup vars.</CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col p-4 bg-dark-800/50 border border-dark-700/30 rounded-xl">
                <span className="text-xs text-muted-foreground uppercase mb-1">Max Positions</span>
                <span className="font-mono font-bold text-lg text-white">{cfg?.max_positions ?? "—"}</span>
              </div>
              <div className="flex flex-col p-4 bg-dark-800/50 border border-dark-700/30 rounded-xl">
                <span className="text-xs text-muted-foreground uppercase mb-1">Risk Per Trade</span>
                <span className="font-mono font-bold text-lg text-white">{cfg?.risk_per_trade ?? "—"}</span>
              </div>
              <div className="flex flex-col p-4 bg-dark-800/50 border border-dark-700/30 rounded-xl">
                <span className="text-xs text-muted-foreground uppercase mb-1">Max Portfolio Risk</span>
                <span className="font-mono font-bold text-lg text-white">{cfg?.max_portfolio_risk ?? "—"}</span>
              </div>
              <div className="flex flex-col p-4 bg-dark-800/50 border border-dark-700/30 rounded-xl">
                <span className="text-xs text-muted-foreground uppercase mb-1">Default Leverage</span>
                <span className="font-mono font-bold text-lg text-white">{cfg?.default_leverage ?? "—"}</span>
              </div>
              <div className="flex flex-col p-4 bg-dark-800/50 border border-dark-700/30 rounded-xl col-span-2 relative overflow-hidden">
                <span className="text-xs text-muted-foreground uppercase mb-1 z-10 relative">Execution Mode</span>
                <span className={cn("font-mono font-bold text-xl z-10 relative", cfg?.testnet ? "text-yellow-500" : "text-green-500")}>
                  {cfg?.testnet ? "TESTNET MODE" : "PRODUCTION MODE"}
                </span>
                {cfg?.testnet && (
                  <div className="absolute top-0 right-0 p-4 opacity-10">
                    <AlertTriangle className="w-16 h-16" />
                  </div>
                )}
              </div>
            </div>

            <div className="mt-6 p-4 rounded-xl bg-dark-950/50 border border-dark-800 text-xs text-muted-foreground space-y-2">
              <p className="font-semibold text-white">Note:</p>
              <div className="flex gap-2">
                <span className="text-primary">•</span>
                <span>Runtime changes are applied immediately to the next loop iteration.</span>
              </div>
              <div className="flex gap-2">
                <span className="text-warning">•</span>
                <span>Keep <strong>TESTNET</strong> active until strategy is fully validated.</span>
              </div>
            </div>

          </CardContent>
        </Card>
      </div>
    </div>
  );
}
