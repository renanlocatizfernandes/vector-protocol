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
        <div className="flex min-h-screen bg-gray-50 font-sans text-gray-900 overflow-hidden">
            {/* Financial Platform Background */}
            <div className="fixed inset-0 -z-10 pointer-events-none">
                <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-white to-green-50 opacity-60" />
                <div className="absolute inset-0" style={{
                    backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(30, 136, 229, 0.08) 1px, transparent 0)',
                    backgroundSize: '40px 40px'
                }} />
            </div>

            {/* Professional Sidebar */}
            <aside
                className={cn(
                    "fixed inset-y-0 left-0 z-50 flex flex-col bg-white border-r border-gray-200 shadow-sm transition-all duration-300",
                    collapsed ? "w-20" : "w-64"
                )}
            >
                <div className="flex items-center justify-between h-16 px-6 border-b border-gray-200 bg-white">
                    <div className={cn("flex items-center gap-3 transition-opacity duration-300", collapsed ? "opacity-0 hidden" : "opacity-100")}>
                        <div className="flex flex-col leading-tight">
                            <span className="text-lg font-bold bg-gradient-to-r from-blue-600 to-green-600 bg-clip-text text-transparent">
                                INVEST TIP BOT
                            </span>
                            <span className="text-xs text-gray-500 font-medium">
                                Dicas Inteligentes
                            </span>
                        </div>
                    </div>

                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setCollapsed(!collapsed)}
                        className="ml-auto text-gray-600 hover:text-gray-900 hover:bg-gray-100"
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
                                    "flex items-center gap-3 px-3 py-2.5 mx-2 rounded-lg transition-all duration-200 group relative",
                                    isActive
                                        ? "bg-blue-50 text-blue-600 font-semibold border-l-4 border-blue-600 pl-4"
                                        : "text-gray-700 hover:bg-gray-50 hover:text-gray-900"
                                )}
                            >
                                <Icon className={cn(
                                    "w-5 h-5 transition-all duration-200",
                                    isActive ? "text-blue-600" : "text-gray-500 group-hover:text-gray-700"
                                )} />
                                <span className={cn(
                                    "font-medium transition-all duration-200",
                                    collapsed ? "opacity-0 w-0 overflow-hidden" : "opacity-100",
                                    isActive && "font-semibold"
                                )}>
                                    {item.label}
                                </span>
                            </Link>
                        );
                    })}
                </div>

                <div className="p-4 border-t border-gray-200">
                    <div className={cn(
                        "flex items-center gap-3 p-3 rounded-lg transition-all duration-200",
                        "bg-gray-50 border border-gray-200",
                        "hover:border-gray-300 hover:shadow-sm",
                        collapsed ? "justify-center" : ""
                    )}>
                        <div className="relative">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-green-500 flex items-center justify-center text-xs font-bold text-white shadow-md">
                                ITB
                            </div>
                            <div className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-green-500 rounded-full ring-2 ring-white" />
                        </div>
                        {!collapsed && (
                            <div className="flex flex-col">
                                <span className="text-sm font-semibold text-gray-900">Invest Tip Bot</span>
                                <span className="text-xs text-green-600 flex items-center gap-1">
                                    <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                                    Ativo • Operando
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
                {/* Professional Header */}
                <header className="h-16 bg-white border-b border-gray-200 sticky top-0 z-40 px-8 flex items-center justify-between shadow-sm">
                    <div>
                        <h1 className="text-xl font-bold text-gray-900">
                            {menuItems.find(i => i.path === location.pathname)?.label || 'Dashboard'}
                        </h1>
                        <p className="text-xs text-gray-500 mt-0.5">
                            {new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })}
                        </p>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="hidden md:flex items-center gap-3 px-4 py-2 rounded-lg bg-gray-50 border border-gray-200 shadow-sm">
                            <Wallet className="w-4 h-4 text-blue-600" />
                            <div className="flex flex-col">
                                <span className="text-xs text-gray-500">Saldo Total</span>
                                <span className="text-sm font-bold text-gray-900 font-mono">
                                    $ {balance !== null ? balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '...'}
                                </span>
                            </div>
                            <span className={cn(
                                "text-xs font-semibold px-2 py-1 rounded-md border",
                                balanceChange >= 0
                                    ? "text-green-700 bg-green-100 border-green-200"
                                    : "text-red-700 bg-red-100 border-red-200"
                            )} title={balanceChangeLabel}>
                                {balanceChange >= 0 ? '+' : ''}{balanceChange.toFixed(2)}%
                            </span>
                        </div>

                        <Button variant="ghost" size="icon" className="relative group text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg">
                            <Bell className="w-5 h-5" />
                            <span className="absolute top-2 right-2 w-2 h-2 bg-yellow-500 rounded-full" />
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
