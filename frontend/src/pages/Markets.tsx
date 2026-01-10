import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  getMarketTickers,
  getConfig,
  getFearGreed,
  type MarketTicker,
  type FearGreedResponse,
} from "../services/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Star, RefreshCw, TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

type TabKey = "favorites" | "crypto" | "gainers" | "losers" | "change";

const TABS: { key: TabKey; label: string }[] = [
  { key: "favorites", label: "Favorites" },
  { key: "crypto", label: "Crypto" },
  { key: "gainers", label: "Gainers" },
  { key: "losers", label: "Losers" },
  { key: "change", label: "Change" },
];

const FAVORITES_KEY = "market_favorites";

function formatVolume(value: number) {
  if (!value || Number.isNaN(value)) return "-";
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(2)}K`;
  return `$${value.toFixed(2)}`;
}

function formatPrice(value: number) {
  if (!value || Number.isNaN(value)) return "-";
  if (value >= 1000) return `$${value.toFixed(2)}`;
  if (value >= 1) return `$${value.toFixed(4)}`;
  return `$${value.toFixed(6)}`;
}

function gradeFromChange(change: number) {
  if (change >= 10) return { label: "A+", tone: "success" };
  if (change >= 5) return { label: "A", tone: "success" };
  if (change >= 0) return { label: "B", tone: "neutral" };
  if (change >= -5) return { label: "C", tone: "warning" };
  return { label: "D", tone: "danger" };
}

export default function Markets() {
  const [tickers, setTickers] = useState<MarketTicker[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<TabKey>("favorites");
  const [search, setSearch] = useState("");
  const [favorites, setFavorites] = useState<string[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string>("");
  const [fearGreed, setFearGreed] = useState<FearGreedResponse | null>(null);

  const loadFavorites = useCallback(async () => {
    try {
      const stored = localStorage.getItem(FAVORITES_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          setFavorites(parsed);
          return;
        }
      }
      const config = await getConfig();
      const wl = (config.symbol_whitelist || []).map((s) => String(s).toUpperCase());
      if (wl.length) {
        setFavorites(wl);
        localStorage.setItem(FAVORITES_KEY, JSON.stringify(wl));
      }
    } catch {
      // ignore
    }
  }, []);

  const loadTickers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getMarketTickers(400, "USDT");
      setTickers(res.tickers || []);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (e: any) {
      setError(e?.message || "Failed to load market data");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadFearGreed = useCallback(async () => {
    try {
      const res = await getFearGreed(30);
      setFearGreed(res);
    } catch {
      setFearGreed(null);
    }
  }, []);

  useEffect(() => {
    loadFavorites();
    loadTickers();
    loadFearGreed();
    const id = setInterval(loadTickers, 30000);
    return () => clearInterval(id);
  }, [loadFavorites, loadTickers, loadFearGreed]);

  const toggleFavorite = (symbol: string) => {
    setFavorites((prev) => {
      const next = prev.includes(symbol)
        ? prev.filter((s) => s !== symbol)
        : [...prev, symbol];
      localStorage.setItem(FAVORITES_KEY, JSON.stringify(next));
      return next;
    });
  };

  const filtered = useMemo(() => {
    let rows = [...tickers];
    if (tab === "favorites") {
      rows = rows.filter((t) => favorites.includes(t.symbol));
    } else if (tab === "gainers") {
      rows.sort((a, b) => b.price_change_percent - a.price_change_percent);
    } else if (tab === "losers") {
      rows.sort((a, b) => a.price_change_percent - b.price_change_percent);
    } else if (tab === "change") {
      rows.sort((a, b) => Math.abs(b.price_change_percent) - Math.abs(a.price_change_percent));
    } else {
      rows.sort((a, b) => b.quote_volume - a.quote_volume);
    }

    const query = search.trim().toUpperCase();
    if (query) {
      rows = rows.filter((t) => t.symbol.includes(query));
    }

    return rows.slice(0, 200);
  }, [tickers, tab, favorites, search]);

  const breadth = useMemo(() => {
    const total = tickers.length || 1;
    const up = tickers.filter((t) => t.price_change_percent > 0).length;
    const down = tickers.filter((t) => t.price_change_percent < 0).length;
    return {
      up,
      down,
      upPct: (up / total) * 100,
      downPct: (down / total) * 100,
      total,
    };
  }, [tickers]);

  const changeBuckets = useMemo(() => {
    const buckets = [
      { label: ">10%", min: 10, max: Infinity },
      { label: "7-10%", min: 7, max: 10 },
      { label: "5-7%", min: 5, max: 7 },
      { label: "3-5%", min: 3, max: 5 },
      { label: "0-3%", min: 0, max: 3 },
      { label: "0--3%", min: -3, max: 0 },
      { label: "-3--5%", min: -5, max: -3 },
      { label: "-5--7%", min: -7, max: -5 },
      { label: "-7--10%", min: -10, max: -7 },
      { label: "<-10%", min: -Infinity, max: -10 },
    ].map((b) => ({ ...b, count: 0 }));

    for (const t of tickers) {
      const v = t.price_change_percent;
      const bucket = buckets.find((b) => v >= b.min && v < b.max);
      if (bucket) {
        bucket.count += 1;
      }
    }
    return buckets;
  }, [tickers]);

  const fngSeries = useMemo(() => {
    const data = fearGreed?.data || [];
    return data.map((point) => ({
      date: new Date(point.timestamp * 1000).toLocaleDateString([], {
        month: "short",
        day: "2-digit",
      }),
      value: point.value,
    }));
  }, [fearGreed]);

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-3">
            <div className="w-1 h-8 bg-gradient-to-b from-blue-600 to-green-600 rounded-full" />
            <h1 className="text-3xl font-bold text-gray-900">Visão Geral do Mercado</h1>
          </div>
          <p className="text-gray-600 ml-4">
            Principais moedores, líderes de volume e favoritos (futuros USDT).
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground">Updated {lastUpdated || "..."}</span>
          <Button onClick={loadTickers} disabled={loading} variant="outline" size="sm" className="gap-2">
            <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
            {loading ? "Loading..." : "Refresh"}
          </Button>
        </div>
      </div>

      <Card className="elevated-card border-gray-200 bg-gray-50">
        <CardHeader className="border-b border-gray-200">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div className="flex flex-wrap gap-2">
              {TABS.map((t) => (
                <Button
                  key={t.key}
                  variant={tab === t.key ? "default" : "outline"}
                  size="sm"
                  onClick={() => setTab(t.key)}
                  className={cn(
                    "h-8 px-4 text-xs",
                    tab === t.key ? "bg-primary text-dark-950" : "border-gray-200 hover:bg-gray-50"
                  )}
                >
                  {t.label}
                </Button>
              ))}
            </div>
            <div className="w-full lg:w-64">
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search symbol"
                className="h-9 text-sm bg-white border-gray-200"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="grid grid-cols-1 lg:grid-cols-3 gap-4 border-b border-white/5">
          <div className="lg:col-span-1 flex flex-col gap-4 p-4">
            <div className="rounded-xl border border-gray-200 bg-white p-4">
              <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                Market Breadth
              </div>
              <div className="mt-3 flex items-center justify-between">
                <div>
                  <div className="text-2xl font-semibold text-green-600">
                    {breadth.up}
                  </div>
                  <div className="text-xs text-muted-foreground">Up</div>
                </div>
                <div>
                  <div className="text-2xl font-semibold text-red-600">
                    {breadth.down}
                  </div>
                  <div className="text-xs text-muted-foreground">Down</div>
                </div>
              </div>
              <div className="mt-4 h-2 w-full rounded-full bg-gray-100 overflow-hidden">
                <div
                  className="h-full bg-success"
                  style={{ width: `${breadth.upPct}%` }}
                />
              </div>
              <div className="mt-2 text-xs text-muted-foreground">
                {breadth.upPct.toFixed(1)}% up / {breadth.downPct.toFixed(1)}% down
              </div>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-4">
              <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                Change Distribution
              </div>
              <div className="mt-3 space-y-2">
                {changeBuckets.map((bucket) => {
                  const pct = breadth.total ? (bucket.count / breadth.total) * 100 : 0;
                  const isPositive = bucket.min >= 0;
                  return (
                    <div key={bucket.label} className="flex items-center gap-2 text-xs">
                      <span className="w-14 text-muted-foreground">{bucket.label}</span>
                      <div className="flex-1 h-2 rounded-full bg-gray-100 overflow-hidden">
                        <div
                          className={cn("h-full", isPositive ? "bg-success/70" : "bg-danger/70")}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="w-10 text-right text-muted-foreground">{bucket.count}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
          <div className="lg:col-span-2 p-4">
            <div className="h-full rounded-xl border border-gray-200 bg-white p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    Fear & Greed Index
                  </div>
                  <div className="mt-2 text-3xl font-semibold text-gray-900">
                    {fearGreed?.latest?.value ?? "--"}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {fearGreed?.latest?.classification || "No data"}
                  </div>
                </div>
                <div className="text-xs text-muted-foreground">
                  Last 30 days
                </div>
              </div>
              <div className="mt-4 h-[220px]">
                {fngSeries.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={fngSeries}>
                      <XAxis dataKey="date" stroke="#9aa3b2" fontSize={11} tickLine={false} axisLine={false} />
                      <YAxis stroke="#9aa3b2" fontSize={11} tickLine={false} axisLine={false} domain={[0, 100]} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#111827",
                          borderColor: "#1f2937",
                          color: "#ffffff",
                          borderRadius: "8px",
                          boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
                        }}
                        formatter={(value: number) => [`${value}`, "Index"]}
                        labelStyle={{ color: "#9aa3b2" }}
                      />
                      <Line type="monotone" dataKey="value" stroke="#2ad4c6" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
                    No fear & greed data available.
                  </div>
                )}
              </div>
            </div>
          </div>
        </CardContent>
        <CardContent className="p-0">
          {error ? (
            <div className="p-6 text-sm text-red-600">{error}</div>
          ) : (
            <div className="max-h-[600px] overflow-auto">
              <Table>
                <TableHeader className="bg-gray-50">
                  <TableRow className="border-gray-200">
                    <TableHead className="text-xs uppercase tracking-wider text-muted-foreground">Symbol</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider text-muted-foreground">Grade</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider text-muted-foreground text-right">Price</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider text-muted-foreground text-right">24h %</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider text-muted-foreground text-right">24h Vol</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider text-muted-foreground text-right">Fav</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.length === 0 && !loading ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-muted-foreground py-12">
                        No symbols found for this view.
                      </TableCell>
                    </TableRow>
                  ) : (
                    filtered.map((t) => {
                      const grade = gradeFromChange(t.price_change_percent);
                      const positive = t.price_change_percent >= 0;
                      return (
                        <TableRow key={t.symbol} className="border-gray-200 hover:bg-gray-50 transition-colors">
                          <TableCell className="font-mono font-semibold text-gray-900">{t.symbol}</TableCell>
                          <TableCell>
                            <Badge
                              variant="outline"
                              className={cn(
                                "border-0 text-xs",
                                grade.tone === "success" && "bg-success/15 text-green-600",
                                grade.tone === "warning" && "bg-accent/15 text-accent",
                                grade.tone === "danger" && "bg-danger/15 text-red-600",
                                grade.tone === "neutral" && "bg-gray-100 text-muted-foreground"
                              )}
                            >
                              {grade.label}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right font-mono">{formatPrice(t.last_price)}</TableCell>
                          <TableCell className="text-right">
                            <span
                              className={cn(
                                "inline-flex items-center gap-1 font-mono text-sm",
                                positive ? "text-green-600" : "text-red-600"
                              )}
                            >
                              {positive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                              {positive ? "+" : ""}
                              {t.price_change_percent.toFixed(2)}%
                            </span>
                          </TableCell>
                          <TableCell className="text-right text-muted-foreground font-mono">
                            {formatVolume(t.quote_volume)}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => toggleFavorite(t.symbol)}
                              className={cn(
                                "h-8 w-8",
                                favorites.includes(t.symbol) ? "text-primary" : "text-muted-foreground"
                              )}
                            >
                              <Star className="w-4 h-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
