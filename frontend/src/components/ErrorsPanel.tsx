import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getRecentErrors, getErrorRate, ErrorLog, ErrorRateResponse } from '@/services/api';

export const ErrorsPanel: React.FC = () => {
    const [errors, setErrors] = useState<ErrorLog[]>([]);
    const [errorRate, setErrorRate] = useState<ErrorRateResponse | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [errorsData, rateData] = await Promise.all([
                    getRecentErrors(20),
                    getErrorRate(undefined, 24)
                ]);
                setErrors(errorsData.errors);
                setErrorRate(rateData);
            } catch (err) {
                console.error('Failed to fetch error data:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
        const interval = setInterval(fetchData, 30000); // Refresh every 30s
        return () => clearInterval(interval);
    }, []);

    return (
        <Card className="glass-card border-white/10 bg-white/5">
            <CardHeader>
                <CardTitle className="text-lg font-semibold flex items-center gap-2 text-slate-900">
                    <AlertCircle className="h-5 w-5 text-danger" />
                    Recent Errors
                </CardTitle>
                <CardDescription className="text-slate-600">
                    Last 20 errors • {errorRate?.average_per_hour.toFixed(1) || '0'} errors/hour
                </CardDescription>
            </CardHeader>
            <CardContent>
                {loading ? (
                    <div className="text-center py-8 text-slate-600">Loading...</div>
                ) : (
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                        {errors.length > 0 ? (
                            errors.map((err, idx) => (
                                <div key={idx} className="border-l-2 border-red-500 pl-3 py-2 bg-white/5 rounded-r">
                                    <div className="flex justify-between text-sm">
                                        <span className="font-mono text-slate-900">{err.component}</span>
                                        <span className="text-xs text-slate-600">
                                            {new Date(err.timestamp * 1000).toLocaleTimeString()}
                                        </span>
                                    </div>
                                    <p className={cn(
                                        "text-sm mt-1",
                                        err.level === 'ERROR' ? 'text-red-600' : 'text-yellow-600'
                                    )}>
                                        {err.message}
                                    </p>
                                </div>
                            ))
                        ) : (
                            <div className="text-center py-8 text-slate-600">
                                <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                <p>No errors in the last 24h ✅</p>
                            </div>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
};
