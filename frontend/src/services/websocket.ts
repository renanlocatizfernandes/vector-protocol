import { http } from "./api";

type EventHandler = (data: any) => void;

class WebSocketService {
    private ws: WebSocket | null = null;
    private url: string;
    private reconnectInterval: number = 2000;
    private maxReconnectInterval: number = 30000;
    private handlers: Map<string, EventHandler[]> = new Map();
    private isConnecting: boolean = false;
    private shouldReconnect: boolean = true;

    constructor() {
        // Derive WS URL from API base URL
        const baseUrl = http.defaults.baseURL || "";
        // If baseURL is empty (same origin), use window.location
        // If baseURL is full URL, replace http/https with ws/wss

        let wsUrl = "";
        if (!baseUrl) {
            const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
            wsUrl = `${protocol}//${window.location.host}/ws`;
        } else {
            if (baseUrl.startsWith("http")) {
                wsUrl = baseUrl.replace(/^http/, "ws") + "/ws";
            } else if (baseUrl.startsWith("/")) {
                const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
                wsUrl = `${protocol}//${window.location.host}${baseUrl}/ws`;
            } else {
                // Fallback
                wsUrl = `ws://localhost:8000/ws`;
            }
        }

        const apiKey = (import.meta.env as any).VITE_API_KEY;
        if (apiKey) {
            const sep = wsUrl.includes("?") ? "&" : "?";
            wsUrl = `${wsUrl}${sep}api_key=${encodeURIComponent(String(apiKey))}`;
        }

        this.url = wsUrl;
    }

    public connect() {
        if (this.ws || this.isConnecting) return;
        this.isConnecting = true;
        this.shouldReconnect = true;

        try {
            console.log(`Connecting to WebSocket at ${this.url}...`);
            this.ws = new WebSocket(this.url);

            this.ws.onopen = () => {
                console.log("✅ WebSocket Connected");
                this.isConnecting = false;
                this.reconnectInterval = 2000; // Reset backoff
            };

            this.ws.onmessage = (event) => {
                try {
                    // Expecting {"type": "...", "data": ...}
                    const payload = JSON.parse(event.data);
                    const { type, data } = payload;

                    if (type) {
                        this.emit(type, data);
                    }
                } catch (err) {
                    console.error("Error parsing WS message:", err);
                }
            };

            this.ws.onclose = () => {
                this.ws = null;
                this.isConnecting = false;
                if (this.shouldReconnect) {
                    console.log(`WebSocket closed. Reconnecting in ${this.reconnectInterval}ms...`);
                    setTimeout(() => this.connect(), this.reconnectInterval);
                    this.reconnectInterval = Math.min(this.reconnectInterval * 1.5, this.maxReconnectInterval);
                }
            };

            this.ws.onerror = (err) => {
                console.error("WebSocket error:", err);
                if (this.ws) {
                    this.ws.close();
                }
            };

        } catch (e) {
            console.error("WebSocket connection failed:", e);
            this.isConnecting = false;
        }
    }

    public disconnect() {
        this.shouldReconnect = false;
        if (this.ws) {
            this.ws.close();
        }
    }

    public on(type: string, handler: EventHandler) {
        if (!this.handlers.has(type)) {
            this.handlers.set(type, []);
        }
        this.handlers.get(type)?.push(handler);
    }

    public off(type: string, handler: EventHandler) {
        if (!this.handlers.has(type)) return;
        const list = this.handlers.get(type) || [];
        this.handlers.set(type, list.filter(h => h !== handler));
    }

    private emit(type: string, data: any) {
        const list = this.handlers.get(type);
        if (list) {
            list.forEach(h => h(data));
        }
    }
}

export const wsService = new WebSocketService();
