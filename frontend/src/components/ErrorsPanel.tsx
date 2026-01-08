import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ErrorLog {
    timestamp: string;
    component: string;
    level: string;
    message: string;
}

export const ErrorsPanel: React.FC = () => {
    const [errors, setErrors] = useState<ErrorLog[]>([]);
    const [errorRate, setErrorRate] = useState(0);

    useEffect(() => {
        // Mock data - will be replaced with real API calls in Phase 4
        const mockErrors: ErrorLog[] = [
            {
                timestamp: new Date(Date.now() - 1000 * 60 * 2).toISOString(),
                component: 'order_executor',
                level: 'ERROR',
                message: 'Insufficient margin for position'
            },
            {
                timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
                component: 'signal_generator',
                level: 'WARN',
                message: 'Low confidence signal rejected'
            },
            {
                timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
                component: 'binance_client',
                level: 'ERROR',
                message: 'Rate limit exceeded, retrying...'
            }
        ];

        setErrors(mockErrors);
        setErrorRate(2.5);
    }, []);

    return (
        <Card className="glass-card border-white/10 bg-white/5">
            <CardHeader>
                <CardTitle className="text-lg font-semibold flex items-center gap-2">
                    <AlertCircle className="h-5 w-5 text-danger" />
                    Recent Errors
                </CardTitle>
                <CardDescription>
                    Last 50 errors • {errorRate.toFixed(1)} errors/hour
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                    {errors.length > 0 ? (
                        errors.map((err, idx) => (
                            <div key={idx} className="border-l-2 border-red-500 pl-3 py-2 bg-white/5 rounded-r">
                                <div className="flex justify-between text-sm">
                                    <span className="font-mono text-yellow-400">{err.component}</span>
                                    <span className="text-xs text-muted-foreground">
                                        {new Date(err.timestamp).toLocaleTimeString()}
                                    </span>
                                </div>
                                <p className={cn(
                                    "text-sm mt-1",
                                    err.level === 'ERROR' ? 'text-red-400' : 'text-yellow-400'
                                )}>
                                    {err.message}
                                </p>
                            </div>
                        ))
                    ) : (
                        <div className="text-center py-8 text-muted-foreground">
                            <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                            <p>No errors in the last 24h</p>
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
};
