import React, { useEffect, useMemo, useRef, useState } from "react";
import { getLogs } from "../services/api";
import { wsService } from "../services/websocket";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Terminal, Download, Copy, RefreshCw, ArrowDown, Type, AlignLeft } from "lucide-react";
import { cn } from "@/lib/utils";

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
  const [tail, setTail] = useState<string>("300");
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [intervalMs, setIntervalMs] = useState<string>("5000");

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lines, setLines] = useState<string[]>([]);
  const [file, setFile] = useState<string>("");

  const preRef = useRef<HTMLPreElement | null>(null);
  const [stickToBottom, setStickToBottom] = useState<boolean>(true);
  const [wrap, setWrap] = useState<boolean>(true);
  const [fontSize, setFontSize] = useState<number>(12);

  const fetchLogs = async (opts?: { silent?: boolean }) => {
    if (inFlight.current) return;
    inFlight.current = true;
    if (!opts?.silent) setLoading(true);
    setError(null);
    try {
      const res = await getLogs(component, Number(tail));
      setLines(res.lines || []);
      setFile(res.file || "");
      setLastUpdated(Date.now());
      if (stickToBottom) {
        requestAnimationFrame(() => {
          if (preRef.current) {
            preRef.current.scrollTop = preRef.current.scrollHeight;
          }
        });
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || "Failed to load logs");
    } finally {
      if (!opts?.silent) setLoading(false);
      inFlight.current = false;
    }
  };

  useEffect(() => {
    fetchLogs();
    if (!autoRefresh) return;
    const id = setInterval(() => {
      lastRefetch.current = Date.now();
      fetchLogs({ silent: true });
    }, Math.max(1000, Number(intervalMs)));
    return () => clearInterval(id);
  }, [component, tail, autoRefresh, intervalMs]);

  // WebSocket Integration
  useEffect(() => {
    wsService.connect();

    const handleLog = (data: any) => {
      // Data is the JSON log object from Python
      // Check if it matches the current component
      // Mapping logic: component "api" -> logger "api", "trading_routes" -> logger "trading_routes" etc.
      // Often strictly equal or contains.

      if (!data || !data.logger) return;

      // Simple filter: if component is "api", show logs from "api" or "uvicorn"?
      // If component is "autonomous_bot", show logs from "autonomous_bot"

      // Let's match loosely for now, or strict if names align.
      // presets values: api, trading_routes, market_routes, autonomous_bot...
      // loggers: api, trading, market, autonomous_bot...

      // Heuristic:
      const loggerName = String(data.logger);
      const target = component.replace("_routes", "").replace("_monitor", "").replace("_generator", "");

      // If presets value is exactly the logger name (e.g. autonomous_bot), match exact
      // If preset has suffixes, try to match prefix.

      let match = false;
      if (component === "api" && (loggerName === "api" || loggerName.startsWith("uvicorn"))) match = true;
      else if (loggerName === component) match = true;
      else if (loggerName.includes(target)) match = true;

      if (match) {
        // Append line. Current lines are JSON strings of log objects.
        // We received 'data' which IS the log object.
        // We need to convert it to string to append to 'lines'.
        setLines(prev => {
          // Optional: limit growth
          const newLines = [...prev, JSON.stringify(data)];
          if (newLines.length > 2000) return newLines.slice(-1000); // Keep last 1000
          return newLines;
        });

        // Update valid updated timestamp
        setLastUpdated(Date.now());

        // Auto-scroll handled by another effect or do it here?
        // Another effect dependency on lines usually.
      }
    };

    wsService.on("log", handleLog);

    return () => {
      wsService.off("log", handleLog);
      // Don't disconnect here if shared? Or yes?
      // Service handles reference counting? No.
      // Just leave it connected or have a global disconnect strategy.
      // For now, keep connected as other components might use it.
    };
  }, [component]);

  // Auto-scroll effect when lines change
  useEffect(() => {
    if (stickToBottom && preRef.current) {
      requestAnimationFrame(() => {
        if (preRef.current) {
          preRef.current.scrollTop = preRef.current.scrollHeight;
        }
      });
    }
  }, [lines, stickToBottom]);

  const lineCount = useMemo(() => lines.length, [lines]);

  const handleScroll = () => {
    if (!preRef.current) return;
    const el = preRef.current;

    // Check if scrolled to bottom with a tolerance of 10px
    const atBottom = Math.abs(el.scrollHeight - el.clientHeight - el.scrollTop) < 20;
    setStickToBottom(atBottom);
  };

  const copyLogs = () => {
    const text = lines.join("\n");
    if (!text) return;
    navigator.clipboard?.writeText(text).catch(() => { });
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
    <Card className="flex flex-col h-[calc(100vh-140px)] glass-card border-white/10 bg-white/5 shadow-[0_24px_60px_rgba(0,0,0,0.45)]">
      <CardHeader className="py-4 border-b border-white/10">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
          <CardTitle className="flex items-center gap-2 text-primary text-lg">
            <Terminal className="w-5 h-5" /> Live System Logs
          </CardTitle>

          <div className="flex flex-wrap items-center gap-3">
            <Select value={component} onValueChange={setComponent}>
              <SelectTrigger className="w-[200px] h-8 text-xs bg-white/5 border-white/10">
                <SelectValue placeholder="Select component" />
              </SelectTrigger>
              <SelectContent>
                {presets.map(p => (
                  <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <div className="flex items-center gap-2">
              <Input
                type="number"
                className="w-20 h-8 text-xs bg-white/5 border-white/10"
                placeholder="Tail"
                value={tail}
                onChange={(e) => setTail(e.target.value)}
              />
              <span className="text-xs text-muted-foreground hidden lg:inline">lines</span>
            </div>

            <div className="h-6 w-px bg-white/10 mx-1 hidden lg:block" />

            <div className="flex items-center gap-2">
              <label className="flex items-center gap-2 text-xs font-medium cursor-pointer text-muted-foreground hover:text-white">
                <Checkbox
                  checked={autoRefresh}
                  onCheckedChange={(c) => setAutoRefresh(!!c)}
                  className="border-white/10 data-[state=checked]:bg-primary data-[state=checked]:border-primary"
                />
                Auto
              </label>
              {autoRefresh && (
                <Input
                  type="number"
                  className="w-16 h-8 text-xs bg-white/5 border-white/10"
                  value={intervalMs}
                  onChange={e => setIntervalMs(e.target.value)}
                  disabled={!autoRefresh}
                />
              )}
              <span className="text-xs text-muted-foreground w-4">ms</span>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between mt-4">
          <div className="text-xs text-muted-foreground font-mono flex items-center gap-2">
            <span className="text-primary">{file || "Loading..."}</span>
            <span>•</span>
            <span>{lineCount} lines</span>
            <span>•</span>
            <span>{lastUpdated ? `Updated ${new Date(lastUpdated).toLocaleTimeString()}` : "Waiting..."}</span>
            {loading && <RefreshCw className="w-3 h-3 animate-spin text-primary" />}
          </div>

          <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => fetchLogs()} title="Refresh">
              <RefreshCw className={cn("w-3 h-3", loading && "animate-spin")} />
            </Button>
            <div className="mx-1 h-4 w-px bg-white/10" />
            <Button variant="ghost" size="icon" className={cn("h-7 w-7", stickToBottom && "text-primary bg-primary/10")} onClick={() => setStickToBottom(!stickToBottom)} title="Sticky Bottom">
              <ArrowDown className="w-3 h-3" />
            </Button>
            <Button variant="ghost" size="icon" className={cn("h-7 w-7", wrap && "text-primary bg-primary/10")} onClick={() => setWrap(!wrap)} title="Toggle Wrap">
              <AlignLeft className="w-3 h-3" />
            </Button>
            <div className="mx-1 h-4 w-px bg-white/10" />
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setFontSize(s => Math.max(10, s - 1))} title="Smaller Font">
              <Type className="w-3 h-3 scale-75" />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setFontSize(s => Math.min(20, s + 1))} title="Larger Font">
              <Type className="w-4 h-4" />
            </Button>
            <div className="mx-1 h-4 w-px bg-white/10" />
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={copyLogs} title="Copy">
              <Copy className="w-3 h-3" />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={downloadLogs} title="Download">
              <Download className="w-3 h-3" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="h-full overflow-hidden p-0 relative">
        {error && (
          <div className="absolute top-0 left-0 right-0 bg-danger/10 text-danger text-xs p-2 text-center border-b border-danger/20 z-10 transition-all">
            {error}
          </div>
        )}
        <pre
          ref={preRef}
          onScroll={handleScroll}
          className={cn(
            "h-full w-full overflow-auto p-4 font-mono scrollbar-hide text-white/90 bg-dark-950",
            wrap ? "whitespace-pre-wrap" : "whitespace-pre"
          )}
          style={{
            fontSize: `${fontSize}px`,
            lineHeight: '1.5',
          }}
        >
          {lines.join('\n')}
        </pre>
        {!stickToBottom && (
          <Button
            variant="default"
            size="sm"
            className="absolute bottom-4 right-8 shadow-lg animate-in fade-in"
            onClick={() => {
              setStickToBottom(true);
              if (preRef.current) preRef.current.scrollTop = preRef.current.scrollHeight;
            }}
          >
            <ArrowDown className="mr-2 w-3 h-3" /> Jump to Bottom
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
