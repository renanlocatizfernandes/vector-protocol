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
    LineChart,
    ChevronRight,
    Sparkles,
    Zap
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
    const [balanceChange, setBalanceChange] = useState<number | null>(null);
    const [balanceChangeLabel, setBalanceChangeLabel] = useState<string>('Net (R+U)');

    useEffect(() => {
        const fetchBalance = async () => {
            try {
                const res = await fetch('/api/trading/stats/daily');
                const data = await res.json();
                const exchangeBalance = data?.exchange?.total_wallet;
                const netPnl = data?.exchange?.net_pnl;
                const resolvedBalance = typeof exchangeBalance === 'number' ? exchangeBalance : null;
                if (resolvedBalance !== null) {
                    setBalance(resolvedBalance);
                } else {
                    setBalance(null);
                }
                if (typeof netPnl === 'number' && typeof resolvedBalance === 'number' && resolvedBalance) {
                    const changePct = (netPnl / resolvedBalance) * 100;
                    setBalanceChange(changePct);
                    setBalanceChangeLabel('Net (R+U)');
                } else {
                    setBalanceChange(null);
                    setBalanceChangeLabel('Net (R+U)');
                }
            } catch (e) {
                console.error('Error fetching balance:', e);
            }
        };
        fetchBalance();
        const interval = setInterval(fetchBalance, 30000);
        return () => clearInterval(interval);
    }, []);

    const menuItems = [
        { path: '/', icon: LayoutDashboard, label: 'Dashboard', color: 'blue' },
        { path: '/metrics', icon: BarChart3, label: 'Metrics', color: 'purple' },
        { path: '/markets', icon: LineChart, label: 'Markets', color: 'green' },
        { path: '/positions', icon: Activity, label: 'Positions', color: 'orange' },
        { path: '/config', icon: Settings, label: 'Configuration', color: 'slate' },
        { path: '/logs', icon: Terminal, label: 'System Logs', color: 'rose' },
        { path: '/supervisor', icon: FileText, label: 'Supervisor', color: 'indigo' },
    ];

    return (
        <div className="flex min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50 font-sans text-slate-900 overflow-hidden pattern-grid">
            {/*  Premium Animated Background */}
            <div className="fixed inset-0 -z-10 pointer-events-none overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-slate-50/50 via-white/50 to-blue-50/50" />
                <div className="absolute inset-0 animated-bg-subtle" />
                {/* Decorative Orbs */}
                <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-blue-500/5 rounded-full blur-3xl animate-float" />
                <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-purple-500/5 rounded-full blur-3xl animate-float" style={{ animationDelay: '1s' }} />
                <div className="absolute top-1/2 left-1/2 w-[400px] h-[400px] bg-green-500/5 rounded-full blur-3xl animate-float" style={{ animationDelay: '2s' }} />
            </div>

            {/*  Modern Glassmorphism Sidebar */}
            <aside
                className={cn(
                    "fixed inset-y-0 left-0 z-50 flex flex-col glass-strong border-r border-slate-200/50 shadow-xl shadow-slate-200/50 transition-all duration-500",
                    collapsed ? "w-20" : "w-72"
                )}
            >
                {/* Brand Section */}
                <div className="relative h-20 px-6 flex items-center justify-between border-b border-slate-200/50 bg-gradient-to-r from-white/80 to-blue-50/80 backdrop-blur-xl">
                    <div className={cn("flex items-center gap-3 transition-all duration-500", collapsed ? "opacity-0 w-0 overflow-hidden" : "opacity-100")}>
                        <div className="relative">
                            <div className="w-10 h-10 rounded-xl premium-gradient flex items-center justify-center shadow-lg shadow-blue-500/30 animate-float">
                                <Sparkles className="w-5 h-5 text-white" />
                            </div>
                            <div className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 rounded-full border-2 border-white pulse-dot" />
                        </div>
                        <div className="flex flex-col leading-tight">
                            <span className="text-lg font-bold text-blue-600">
                                INVEST TIP
                            </span>
                            <span className="text-xs text-slate-500 font-semibold tracking-wide">
                                Dicas Inteligentes
                            </span>
                        </div>
                    </div>

                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setCollapsed(!collapsed)}
                        className="ml-auto text-slate-600 hover:text-slate-900 hover:bg-slate-100/80 transition-all duration-300 hover:scale-110"
                    >
                        <Menu className="w-5 h-5" />
                    </Button>
                </div>

                {/* Menu Items */}
                <div className="flex-1 py-6 px-4 flex flex-col gap-2 overflow-y-auto scrollbar-hide">
                    {menuItems.map((item, index) => {
                        const Icon = item.icon;
                        const isActive = location.pathname === item.path;
                        const colorMap: Record<string, string> = {
                            blue: 'from-blue-600 to-indigo-600',
                            purple: 'from-purple-600 to-violet-600',
                            green: 'from-green-600 to-emerald-600',
                            orange: 'from-orange-600 to-amber-600',
                            slate: 'from-slate-600 to-gray-600',
                            rose: 'from-rose-600 to-red-600',
                            indigo: 'from-indigo-600 to-blue-600'
                        };

                        return (
                            <Link
                                key={item.path}
                                to={item.path}
                                style={{ animationDelay: `${index * 0.05}s` }}
                                className={cn(
                                    "group relative flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 animate-slide-up overflow-hidden",
                                    isActive
                                        ? "bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30 shadow-lg shadow-blue-500/10"
                                        : "text-slate-600 hover:bg-slate-100/80 hover:text-slate-900 hover:shadow-md"
                                )}
                            >
                                {/* Active Indicator */}
                                {isActive && (
                                    <div className={cn(
                                        "absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 rounded-r-full premium-gradient-blue shadow-lg shadow-blue-500/50"
                                    )} />
                                )}

                                {/* Glow Effect */}
                                {isActive && (
                                    <div className="absolute inset-0 bg-gradient-to-r from-blue-500/5 to-purple-500/5 animate-pulse" />
                                )}

                                <Icon className={cn(
                                    "w-5 h-5 transition-all duration-300 relative z-10",
                                    isActive ? `bg-gradient-to-r ${colorMap[item.color]} bg-clip-text text-transparent scale-110` : "text-slate-500 group-hover:text-slate-700 group-hover:scale-110"
                                )} />

                                <span className={cn(
                                    "font-semibold transition-all duration-300 relative z-10",
                                    collapsed ? "opacity-0 w-0 overflow-hidden" : "opacity-100",
                                    isActive && `bg-gradient-to-r ${colorMap[item.color]} bg-clip-text text-transparent`
                                )}>
                                    {item.label}
                                </span>

                                {/* Hover Arrow */}
                                {!collapsed && !isActive && (
                                    <ChevronRight className={cn(
                                        "w-4 h-4 ml-auto opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300 text-slate-400"
                                    )} />
                                )}
                            </Link>
                        );
                    })}
                </div>

                {/* User Profile Section */}
                <div className="p-4 border-t border-slate-200/50 bg-gradient-to-r from-slate-50/80 to-white/80 backdrop-blur-xl">
                    <div className={cn(
                        "flex items-center gap-3 p-3 rounded-xl transition-all duration-300 hover:shadow-lg cursor-pointer group",
                        "bg-white border border-slate-200/50 shadow-sm",
                        "hover:border-blue-300/50 hover:shadow-blue-500/10",
                        collapsed ? "justify-center" : ""
                    )}>
                        <div className="relative">
                            <div className="w-10 h-10 rounded-xl premium-gradient flex items-center justify-center text-xs font-bold text-white shadow-lg shadow-purple-500/30 group-hover:scale-110 transition-transform duration-300">
                                ITB
                            </div>
                            <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-500 rounded-full ring-2 ring-white pulse-glow" />
                        </div>
                        {!collapsed && (
                            <div className="flex flex-col flex-1">
                                <span className="text-sm font-bold text-slate-900">Invest Tip Bot</span>
                                <span className="text-xs text-green-600 font-semibold flex items-center gap-1.5">
                                    <span className="w-1.5 h-1.5 bg-green-500 rounded-full pulse-dot" />
                                    <Zap className="w-3 h-3" />
                                    Ativo - Operando
                                </span>
                            </div>
                        )}
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main
                className={cn(
                    "flex-1 flex flex-col min-h-screen transition-all duration-500",
                    collapsed ? "pl-20" : "pl-72"
                )}
            >
                {/*  Premium Glassmorphism Header */}
                <header className="h-20 bg-gradient-to-r from-white/90 to-slate-50/90 backdrop-blur-xl border-b border-slate-200/50 sticky top-0 z-40 px-8 flex items-center justify-between shadow-lg shadow-slate-200/30">
                    <div>
                        <div className="flex items-center gap-3">
                            <div className="w-1 h-10 bg-gradient-to-b from-blue-600 to-purple-600 rounded-full shadow-lg shadow-blue-500/30" />
                            <div>
                                <h1 className="text-2xl font-bold text-blue-600">
                                    {menuItems.find(i => i.path === location.pathname)?.label || 'Dashboard'}
                                </h1>
                                <p className="text-sm text-slate-500 mt-0.5 font-medium">
                                    {new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })}
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        {/* Balance Card */}
                        <div className="hidden md:flex items-center gap-4 px-5 py-3 rounded-xl bg-gradient-to-r from-blue-50/80 to-purple-50/80 border border-blue-200/50 shadow-lg shadow-blue-500/10 transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/20 hover:scale-105 group">
                            <div className="relative">
                                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/30 group-hover:scale-110 transition-transform duration-300">
                                    <Wallet className="w-5 h-5 text-white" />
                                </div>
                                <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full ring-2 ring-white pulse-dot" />
                            </div>
                            <div className="flex flex-col">
                                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Saldo Total</span>
                                <span className="text-lg font-bold text-slate-900 font-mono">
                                    $ {balance !== null ? balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '...'}
                                </span>
                            </div>
                            <div className={cn(
                                "px-3 py-1.5 rounded-lg text-xs font-bold border transition-all duration-300",
                                balanceChange === null
                                    ? "bg-slate-100 text-slate-500 border-slate-200"
                                    : balanceChange >= 0
                                        ? "bg-gradient-to-r from-green-100 to-emerald-100 text-green-700 border-green-300 shadow-sm shadow-green-500/20"
                                        : "bg-gradient-to-r from-red-100 to-rose-100 text-red-700 border-red-300 shadow-sm shadow-red-500/20"
                            )} title={balanceChangeLabel}>
                                {balanceChange === null
                                    ? "--"
                                    : `${balanceChange >= 0 ? "+" : "-"}${Math.abs(balanceChange).toFixed(2)}%`}
                            </div>
                        </div>

                        {/* Notifications */}
                        <Button variant="ghost" size="icon" className="relative group text-slate-600 hover:text-slate-900 hover:bg-slate-100/80 rounded-xl transition-all duration-300 hover:scale-110">
                            <Bell className="w-5 h-5 group-hover:animate-shimmer" />
                            <span className="absolute top-2 right-2 w-2.5 h-2.5 bg-gradient-to-r from-amber-500 to-orange-500 rounded-full shadow-lg shadow-amber-500/30 pulse-dot" />
                        </Button>
                    </div>
                </header>

                {/* Content Area */}
                <div className="flex-1 p-8 overflow-y-auto scrollbar-hide">
                    <div className="animate-fade-in">
                        {children}
                    </div>
                </div>
            </main>
        </div>
    );
};
