import { useEffect, useRef, useState } from "react";
import { getBotStatus, type BotStatus } from "../services/api";

export type BotIndicator = {
  running: boolean;
  data: BotStatus | null;
  loading: boolean;
  error: string | null;
};

export function useBotStatus(pollMs: number = 10000): BotIndicator {
  const [data, setData] = useState<BotStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const first = useRef(true);

  const load = async (silent?: boolean) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      const st = await getBotStatus();
      setData(st || null);
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || "Falha ao consultar status do bot");
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const id = setInterval(() => load(true), Math.max(1000, pollMs));
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pollMs]);

  return {
    running: !!data?.running,
    data,
    loading,
    error
  };
}
