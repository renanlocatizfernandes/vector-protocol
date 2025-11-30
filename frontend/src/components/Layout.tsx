import React from 'react';
import { Link, useLocation } from 'react-router-dom';

interface LayoutProps {
    children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
    const location = useLocation();

    const menuItems = [
        { path: '/', icon: '📊', label: 'Dashboard' },
        { path: '/metrics', icon: '📈', label: 'Métricas' },
        { path: '/config', icon: '⚙️', label: 'Configuração' },
        { path: '/logs', icon: '📝', label: 'Logs' },
    ];

    return (
        <div className="flex min-h-screen bg-primary text-primary font-sans">
            {/* Sidebar */}
            <aside className="w-64 bg-secondary border-r border-gray-700 flex flex-col fixed h-full">
                <div className="p-6 border-b border-gray-700">
                    <h1 className="text-xl font-bold text-blue-400 flex items-center gap-2">
                        <span className="text-2xl">🤖</span> Antigravity
                    </h1>
                    <p className="text-xs text-secondary mt-1">Crypto Bot v4.0</p>
                </div>

                <nav className="flex-1 p-4 flex flex-col gap-2">
                    {menuItems.map((item) => {
                        const isActive = location.pathname === item.path;
                        return (
                            <Link
                                key={item.path}
                                to={item.path}
                                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${isActive
                                        ? 'bg-blue-900/30 text-blue-400 border border-blue-900/50'
                                        : 'text-secondary hover:bg-tertiary hover:text-primary'
                                    }`}
                            >
                                <span className="text-lg">{item.icon}</span>
                                <span className="font-medium">{item.label}</span>
                            </Link>
                        );
                    })}
                </nav>

                <div className="p-4 border-t border-gray-700">
                    <div className="text-xs text-secondary text-center">
                        &copy; 2025 Antigravity Bot
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 ml-64 p-8 overflow-y-auto">
                {children}
            </main>
        </div>
    );
};
