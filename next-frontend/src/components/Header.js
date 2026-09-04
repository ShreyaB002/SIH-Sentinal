"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Grid, Layout, Maximize, Cpu, HardDrive, ShieldCheck, Activity } from "lucide-react";

export default function Header({
  wsStatus = "CONNECTING",
  layout = "2x3",
  setLayout = () => {}
}) {
  const [time, setTime] = useState("");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTime(
        now.toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
        })
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const wsOnline = wsStatus === "ONLINE";

  return (
    <header className="sticky top-0 z-40 bg-app-bg border-b border-border/50">
      <div className="flex h-14 items-center justify-between px-6">
        
        {/* Left: Branding & Status */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-3">
            <h1 className="text-sm font-semibold tracking-wider text-text-primary uppercase flex items-center gap-2">
              <ShieldCheck size={16} className="text-primary" />
              Sentinel OS
            </h1>
            <div className="h-4 w-px bg-border/50" />
            <div className="flex items-center gap-2">
              <span className={`h-1.5 w-1.5 rounded-full ${wsOnline ? "bg-green-healthy shadow-[0_0_8px_rgba(16,185,129,0.5)]" : "bg-amber-warning"} animate-pulse`} />
              <span className="text-[11px] font-medium tracking-wide text-text-muted uppercase">
                {wsOnline ? "Encrypted Link Active" : "Establishing..."}
              </span>
            </div>
          </div>
        </div>

        {/* Center: Layout Controls (Borderless Button Group) */}
        <div className="flex items-center gap-1 bg-nav-bg/50 rounded-lg p-1">
          <button 
            onClick={() => setLayout("2x3")}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-[11px] font-medium transition-colors ${layout === "2x3" ? "bg-nav-hover text-text-primary" : "text-text-muted hover:text-text-secondary"}`}
          >
            <Grid size={14} /> 2x3 Matrix
          </button>
          <button 
            onClick={() => setLayout("1+5")}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-[11px] font-medium transition-colors ${layout === "1+5" ? "bg-nav-hover text-text-primary" : "text-text-muted hover:text-text-secondary"}`}
          >
            <Layout size={14} /> 1+5 Focus
          </button>
          <button 
            onClick={() => setLayout("1x1")}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-[11px] font-medium transition-colors ${layout === "1x1" ? "bg-nav-hover text-text-primary" : "text-text-muted hover:text-text-secondary"}`}
          >
            <Maximize size={14} /> 1x1 Cinema
          </button>
        </div>

        {/* Right: Telemetry & Time */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-4 text-[10px] uppercase font-medium tracking-wider text-text-muted">
            <div className="flex items-center gap-1.5">
              <Cpu size={12} className="text-text-secondary" /> RTX 2050
            </div>
            <div className="flex items-center gap-1.5">
              <Activity size={12} className="text-secondary" /> YOLO26M
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-green-healthy" /> AUDIO ON
            </div>
          </div>

          <div className="h-4 w-px bg-border/50" />

          <p className="font-mono text-[13px] text-text-secondary tracking-wider">
            {time || "--:--:--"}
          </p>
        </div>
        
      </div>
    </header>
  );
}