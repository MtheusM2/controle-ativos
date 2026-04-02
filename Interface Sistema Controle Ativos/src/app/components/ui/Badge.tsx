import * as React from "react"
import { cn } from "../../utils/cn"

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "success" | "warning" | "destructive" | "outline"
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center rounded-sm border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        {
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80": variant === "default",
          "border-transparent bg-emerald-500/20 text-emerald-400 border-emerald-500/30": variant === "success",
          "border-transparent bg-amber-500/20 text-amber-400 border-amber-500/30": variant === "warning",
          "border-transparent bg-wine-glow/20 text-wine-glow border-wine-glow/30": variant === "destructive",
          "text-foreground border-border": variant === "outline",
        },
        className
      )}
      {...props}
    />
  )
}
