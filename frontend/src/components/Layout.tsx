import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
    LayoutDashboard,
    Activity,
    Settings,
    FileText,
    Terminal,
    Menu,
    LogOut,
    Bell,
    Wallet
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface LayoutProps {
    children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
    const location = useLocation();
    const [collapsed, setCollapsed] = useState(false);

    const menuItems = [
        { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
        { path: '/positions', icon: Activity, label: 'Positions' },
        { path: '/config', icon: Settings, label: 'Configuration' },
        { path: '/logs', icon: Terminal, label: 'System Logs' },
        { path: '/supervisor', icon: FileText, label: 'Supervisor' },
    ];

    return (
        <div className="flex min-h-screen bg-dark-950 font-sans text-text-main overflow-hidden">
            {/* Background Gradients */}
            <div className="fixed top-0 left-0 w-full h-full overflow-hidden -z-10 pointer-events-none">
                <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-primary-dim blur-[120px] rounded-full opacity-20" />
                <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-accent-dim blur-[120px] rounded-full opacity-20" />
            </div>

            {/* Sidebar */}
            <aside
                className={cn(
                    "fixed inset-y-0 left-0 z-50 flex flex-col glass-panel transition-all duration-300 border-r border-dark-700/50",
                    collapsed ? "w-20" : "w-64"
                )}
            >
                <div className="flex items-center justify-between h-20 px-6 border-b border-dark-700/50">
                    <div className={cn("flex items-center gap-3 transition-opacity duration-300", collapsed ? "opacity-0 hidden" : "opacity-100")}>
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center shadow-lg shadow-primary/20">
                            <Activity className="w-5 h-5 text-white" />
                        </div>
                        <span className="font-bold text-lg tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-400">
                            ANTIGRAVITY
                        </span>
                    </div>

                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setCollapsed(!collapsed)}
                        className="ml-auto text-text-muted hover:text-white hover:bg-dark-800"
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
                                        ? "bg-primary/10 text-primary shadow-inner"
                                        : "text-text-muted hover:text-white hover:bg-dark-800/50"
                                )}
                            >
                                {isActive && (
                                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary shadow-[0_0_10px_#00f0ff]" />
                                )}
                                <Icon className={cn("w-5 h-5 transition-transform group-hover:scale-110", isActive && "text-primary drop-shadow-[0_0_5px_rgba(0,240,255,0.5)]")} />
                                <span className={cn("font-medium transition-all duration-300", collapsed ? "opacity-0 w-0 overflow-hidden" : "opacity-100")}>
                                    {item.label}
                                </span>
                            </Link>
                        );
                    })}
                </div>

                <div className="p-4 border-t border-dark-700/50">
                    <div className={cn("flex items-center gap-3 p-3 rounded-xl bg-dark-900/50 border border-dark-800", collapsed ? "justify-center" : "")}>
                        <div className="relative">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-accent to-blue-600 flex items-center justify-center text-xs font-bold ring-2 ring-dark-950">
                                RB
                            </div>
                            <div className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-success rounded-full ring-2 ring-dark-950 animate-pulse" />
                        </div>
                        {!collapsed && (
                            <div className="flex flex-col">
                                <span className="text-sm font-semibold text-white">Renan Bot</span>
                                <span className="text-xs text-success">Active • Trading</span>
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
                {/* Topbar */}
                <header className="h-20 glass-panel border-b border-dark-700/50 sticky top-0 z-40 px-8 flex items-center justify-between">
                    <div>
                        <h1 className="text-xl font-bold text-white">
                            {menuItems.find(i => i.path === location.pathname)?.label || 'Dashboard'}
                        </h1>
                        <p className="text-xs text-text-muted">
                            {new Date().toLocaleDateString('pt-BR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                        </p>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="hidden md:flex items-center gap-2 px-4 py-2 rounded-full bg-dark-800/50 border border-dark-700/50">
                            <Wallet className="w-4 h-4 text-primary" />
                            <span className="text-sm font-mono text-white">$ 12,450.00</span>
                            <span className="text-xs text-success bg-success/10 px-1.5 py-0.5 rounded">+2.4%</span>
                        </div>

                        <Button variant="ghost" size="icon" className="relative group text-text-muted hover:text-white hover:bg-dark-800/50">
                            <Bell className="w-5 h-5 group-hover:rotate-12 transition-transform" />
                            <span className="absolute top-2 right-2 w-2 h-2 bg-accent rounded-full animate-ping" />
                            <span className="absolute top-2 right-2 w-2 h-2 bg-accent rounded-full" />
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
