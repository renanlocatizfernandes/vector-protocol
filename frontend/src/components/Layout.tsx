import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
    LayoutDashboard,
    Activity,
    Settings,
    FileText,
    Terminal,
    Menu,
    Bell,
    Wallet,
    BarChart3,
    LineChart
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface LayoutProps {
    children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
    const location = useLocation();
    const [collapsed, setCollapsed] = useState(false);
    const [balance, setBalance] = useState<number | null>(null);
    const [balanceChange, setBalanceChange] = useState<number>(0);
    const [balanceChangeLabel, setBalanceChangeLabel] = useState<string>('Daily (DB)');

    useEffect(() => {
        const fetchBalance = async () => {
            try {
                const res = await fetch('/api/trading/stats/daily');
                const data = await res.json();
                const exchangeBalance = data?.exchange?.total_wallet;
                const netPnl = data?.exchange?.net_pnl;
                const resolvedBalance = typeof exchangeBalance === 'number' ? exchangeBalance : data?.balance;
                if (typeof resolvedBalance === 'number') {
                    setBalance(resolvedBalance);
                }
                if (typeof netPnl === 'number' && resolvedBalance) {
                    const changePct = (netPnl / resolvedBalance) * 100;
                    setBalanceChange(changePct);
                    setBalanceChangeLabel('Net (R+U)');
                } else if (data && typeof data.total_pnl === 'number' && resolvedBalance) {
                    const changePct = (data.total_pnl / resolvedBalance) * 100;
                    setBalanceChange(changePct);
                    setBalanceChangeLabel('Daily (DB)');
                }
            } catch (e) {
                console.error('Error fetching balance:', e);
            }
        };
        fetchBalance();
        const interval = setInterval(fetchBalance, 30000); // Atualiza a cada 30s
        return () => clearInterval(interval);
    }, []);

    const menuItems = [
        { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
        { path: '/metrics', icon: BarChart3, label: 'Metrics' },
        { path: '/markets', icon: LineChart, label: 'Markets' },
        { path: '/positions', icon: Activity, label: 'Positions' },
        { path: '/config', icon: Settings, label: 'Configuration' },
        { path: '/logs', icon: Terminal, label: 'System Logs' },
        { path: '/supervisor', icon: FileText, label: 'Supervisor' },
    ];

    return (
        <div className="flex min-h-screen bg-dark-950 font-sans text-text-main overflow-hidden surface-grid">
            {/* Atmosphere */}
            <div className="fixed top-0 left-0 w-full h-full overflow-hidden -z-10 pointer-events-none">
                <div className="absolute -top-40 -left-40 h-96 w-96 rounded-full bg-primary/15 blur-[120px] animate-float" />
                <div className="absolute bottom-[-10%] right-[-5%] h-[28rem] w-[28rem] rounded-full bg-accent/15 blur-[160px] animate-float" style={{ animationDelay: '1s' }} />
                <div className="absolute top-1/3 right-1/4 h-56 w-56 rounded-full bg-white/5 blur-[120px]" />
            </div>

            {/* Enhanced Sidebar */}
            <aside
                className={cn(
                    "fixed inset-y-0 left-0 z-50 flex flex-col glass-panel transition-all duration-300",
                    "border-r border-white/5 bg-dark-900/70",
                    collapsed ? "w-20" : "w-64"
                )}
            >
                <div className="flex items-center justify-between h-20 px-6 border-b border-white/5 relative">
                    {/* Gradient accent line */}
                    <div className="absolute bottom-0 left-0 right-0 h-[1px] panel-divider" />

                    <div className={cn("flex items-center gap-3 transition-opacity duration-300", collapsed ? "opacity-0 hidden" : "opacity-100")}>
                        <div className="w-9 h-9 rounded-xl bg-primary/20 flex items-center justify-center border border-primary/30 shadow-[0_0_20px_rgba(42,212,198,0.35)]">
                            <Activity className="w-5 h-5 text-primary" />
                        </div>
                        <div className="flex flex-col leading-tight">
                            <span className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">Vector</span>
                            <span className="text-xs text-muted-foreground">Protocol Console</span>
                        </div>
                    </div>

                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setCollapsed(!collapsed)}
                        className="ml-auto text-text-muted hover:text-primary hover:bg-white/5 transition-all duration-300"
                    >
                        <Menu className="w-5 h-5" />
                    </Button>
                </div>

                <div className="flex-1 py-6 px-3 flex flex-col gap-2">
                    {menuItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = location.pathname === item.path;
                        return (
                            <Link
                                key={item.path}
                                to={item.path}
                                className={cn(
                                    "flex items-center gap-3 px-3 py-3 rounded-xl transition-all duration-300 group relative overflow-hidden",
                                    isActive
                                        ? "bg-white/10 text-primary border border-white/10 shadow-[0_12px_32px_rgba(0,0,0,0.35)]"
                                        : "text-text-muted hover:text-white hover:bg-white/5 hover:border hover:border-white/10"
                                )}
                            >
                                {isActive && (
                                    <>
                                        <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary shadow-[0_0_15px_rgba(42,212,198,0.5)]" />
                                        <div className="absolute inset-0 bg-gradient-to-r from-white/10 to-transparent opacity-50" />
                                    </>
                                )}
                                <Icon className={cn(
                                    "w-5 h-5 transition-all duration-300 group-hover:scale-110",
                                    isActive ? "text-primary drop-shadow-[0_0_8px_rgba(42,212,198,0.4)]" : "group-hover:text-primary"
                                )} />
                                <span className={cn(
                                    "font-medium transition-all duration-300",
                                    collapsed ? "opacity-0 w-0 overflow-hidden" : "opacity-100",
                                    isActive && "font-semibold"
                                )}>
                                    {item.label}
                                </span>
                            </Link>
                        );
                    })}
                </div>

                <div className="p-4 border-t border-white/5 relative">
                    {/* Gradient accent line */}
                    <div className="absolute top-0 left-0 right-0 h-[1px] panel-divider" />

                    <div className={cn(
                        "flex items-center gap-3 p-3 rounded-xl transition-all duration-300",
                        "bg-white/5 border border-white/10",
                        "hover:border-primary/30 hover:shadow-lg hover:shadow-primary/10",
                        collapsed ? "justify-center" : ""
                    )}>
                        <div className="relative">
                            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-xs font-bold ring-2 ring-dark-950 shadow-lg shadow-primary/20 text-primary">
                                VB
                            </div>
                            <div className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-success rounded-full ring-2 ring-dark-950 animate-pulse shadow-[0_0_8px_rgba(43,212,165,0.6)]" />
                        </div>
                        {!collapsed && (
                            <div className="flex flex-col">
                                <span className="text-sm font-semibold text-white">Vector Bot</span>
                                <span className="text-xs text-success flex items-center gap-1">
                                    <span className="w-1.5 h-1.5 bg-success rounded-full animate-pulse" />
                                    Active • Trading
                                </span>
                            </div>
                        )}
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main
                className={cn(
                    "flex-1 flex flex-col min-h-screen transition-all duration-300",
                    collapsed ? "pl-20" : "pl-64"
                )}
            >
                {/* Enhanced Topbar */}
                <header className="h-20 glass-panel border-b border-white/5 sticky top-0 z-40 px-8 flex items-center justify-between backdrop-blur-xl">
                    {/* Bottom gradient accent */}
                    <div className="absolute bottom-0 left-0 right-0 h-[1px] panel-divider" />

                    <div>
                        <h1 className="text-xl font-bold bg-gradient-to-r from-white via-primary/90 to-accent/90 bg-clip-text text-transparent">
                            {menuItems.find(i => i.path === location.pathname)?.label || 'Dashboard'}
                        </h1>
                        <p className="text-xs text-text-muted mt-0.5">
                            {new Date().toLocaleDateString('pt-BR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                        </p>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="hidden md:flex items-center gap-3 px-5 py-2.5 rounded-full bg-white/5 border border-white/10 shadow-lg hover:border-primary/30 transition-all duration-300 backdrop-blur-sm">
                            <Wallet className="w-4 h-4 text-primary drop-shadow-[0_0_6px_rgba(42,212,198,0.4)]" />
                            <span className="text-sm font-mono font-semibold text-white">
                                $ {balance !== null ? balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '...'}
                            </span>
                            <span className={cn(
                                "text-xs font-semibold px-2 py-1 rounded-full border transition-all duration-300",
                                balanceChange >= 0
                                    ? "text-success bg-success/10 border-success/20 shadow-[0_0_10px_rgba(43,212,165,0.2)]"
                                    : "text-danger bg-danger/10 border-danger/20 shadow-[0_0_10px_rgba(255,90,95,0.2)]"
                            )} title={balanceChangeLabel}>
                                {balanceChange >= 0 ? '+' : ''}{balanceChange.toFixed(2)}%
                            </span>
                        </div>

                        <Button variant="ghost" size="icon" className="relative group text-text-muted hover:text-primary hover:bg-white/5 transition-all duration-300 rounded-xl">
                            <Bell className="w-5 h-5 group-hover:rotate-12 transition-all duration-300" />
                            <span className="absolute top-2 right-2 w-2 h-2 bg-accent rounded-full animate-ping shadow-[0_0_8px_rgba(245,159,58,0.5)]" />
                            <span className="absolute top-2 right-2 w-2 h-2 bg-accent rounded-full shadow-[0_0_8px_rgba(245,159,58,0.5)]" />
                        </Button>
                    </div>
                </header>

                <div className="flex-1 p-8 overflow-y-auto">
                    {children}
                </div>
            </main>
        </div>
    );
};
