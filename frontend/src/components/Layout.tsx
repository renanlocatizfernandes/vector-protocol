import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Activity, Settings, FileText, Terminal } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LayoutProps {
    children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
    const location = useLocation();

    const menuItems = [
        { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
        { path: '/metrics', icon: Activity, label: 'Métricas' },
        { path: '/config', icon: Settings, label: 'Configuração' },
        { path: '/logs', icon: Terminal, label: 'Logs' },
        { path: '/supervisor', icon: FileText, label: 'Supervisor' },
    ];

    return (
        <div className="flex min-h-screen bg-background font-sans antialiased">
            {/* Sidebar */}
            <aside className="fixed inset-y-0 left-0 z-50 w-64 border-r bg-card text-card-foreground shadow-xl transition-transform duration-300 ease-in-out">
                <div className="flex h-16 items-center border-b px-6">
                    <div className="flex items-center gap-2 font-bold text-xl text-primary">
                        <span className="text-2xl">🤖</span>
                        <span>Antigravity</span>
                    </div>
                </div>

                <div className="flex flex-col gap-1 p-4">
                    {menuItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = location.pathname === item.path;
                        return (
                            <Link
                                key={item.path}
                                to={item.path}
                                className={cn(
                                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
                                    isActive ? "bg-primary/10 text-primary" : "text-muted-foreground"
                                )}
                            >
                                <Icon className="h-4 w-4" />
                                {item.label}
                            </Link>
                        );
                    })}
                </div>

                <div className="mt-auto border-t p-4">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>v4.0.0</span>
                        <div className="flex items-center gap-1">
                            <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                            <span>Online</span>
                        </div>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 pl-64">
                <div className="container py-6 max-w-7xl mx-auto">
                    {children}
                </div>
            </main>
        </div>
    );
};
