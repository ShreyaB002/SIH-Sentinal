"use client";

import { AlertTriangle, Camera, Activity, ShieldAlert, Cpu } from "lucide-react";
import { motion } from "framer-motion";

export default function MetricCard({ title, value, status, icon: Icon, type = "neutral" }) {
  const getColors = () => {
    switch(type) {
      case "danger": return "text-red-danger bg-red-danger/10 border-red-danger/20";
      case "warning": return "text-amber-warning bg-amber-warning/10 border-amber-warning/20";
      case "success": return "text-green-healthy bg-green-healthy/10 border-green-healthy/20";
      default: return "text-blue-primary bg-blue-primary/10 border-blue-primary/20";
    }
  };

  return (
    <motion.div 
      whileHover={{ y: -2 }}
      className="flex flex-col justify-between rounded-[10px] border border-border bg-card-bg p-4 shadow-[0_5px_16px_rgba(58,80,88,0.12)] transition-all duration-[200ms] hover:shadow-[0_8px_24px_rgba(58,80,88,0.18)] hover:border-border-accent"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <div className={`flex h-8 w-8 items-center justify-center rounded-lg border ${getColors()}`}>
            <Icon size={16} />
          </div>
          <span className="text-xs font-semibold text-text-secondary">{title}</span>
        </div>
      </div>
      
      <div className="mt-4 flex items-end justify-between">
        <span className="text-2xl font-bold tracking-tight text-text-primary">{value}</span>
        {status && (
          <span className="text-xs font-medium text-text-muted mb-1">{status}</span>
        )}
      </div>
    </motion.div>
  );
}
