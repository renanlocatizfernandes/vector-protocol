import * as React from "react"
import { cn } from "@/lib/utils"

const badgeVariants = (variant: string = "default") => {
    const base = "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"

    const variants: Record<string, string> = {
        default: "border-blue-200 bg-blue-100 text-blue-700",
        secondary: "border-gray-200 bg-gray-100 text-gray-700",
        destructive: "border-red-200 bg-red-100 text-red-700",
        outline: "border-gray-300 text-gray-700",
        success: "border-green-200 bg-green-100 text-green-700",
        warning: "border-yellow-200 bg-yellow-100 text-yellow-700",
    }

    return cn(base, variants[variant])
}

export interface BadgeProps
    extends React.HTMLAttributes<HTMLDivElement> {
    variant?: "default" | "secondary" | "destructive" | "outline" | "success" | "warning"
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
    return (
        <div className={cn(badgeVariants(variant), className)} {...props} />
    )
}

export { Badge, badgeVariants }
