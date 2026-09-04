"use client";

import { useEffect, useState } from "react";
import {
  Grid,
  Layout,
  Maximize,
  Cpu,
  Activity,
  Volume2,
  Users,
  Car,
  Map,
  AlertTriangle,
  Hexagon,
  Shield,
} from "lucide-react";

export default function Header({
  wsStatus = "CONNECTING",
  layout = "2x3",
  setLayout = () => {},
  onActionClick = () => {},
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
          hour12: true,
        }),
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="sticky top-0 z-40 bg-[#060a12] border-b border-border/20 flex flex-col justify-center">
      {/* Container for the 3D-like panels */}
      <div className="mx-auto w-full px-2 py-2 max-w-full">
        {/* TOP TIER: DataStream Command Hub */}
        <div className="w-full flex flex-col items-center mb-1">
          {/* Top Center Title (Moved out of absolute positioning) */}
          <div className="flex flex-col items-center z-10 mb-2 mt-1">
            <div className="flex items-center gap-2 text-secondary text-xs font-mono tracking-widest bg-[#0a111a]/80 px-8 py-1 border border-secondary/50 rounded-full shadow-[0_0_15px_rgba(6,182,212,0.3)]">
              <Activity size={14} className="animate-pulse" />
              <span>DATASTREAM COMMAND HUB</span>
              <Activity size={14} className="animate-pulse" />
            </div>
            <div className="w-px h-2 bg-secondary/30" />
            <div className="w-32 h-px bg-secondary/30" />
          </div>

          <div className="flex justify-between items-start w-full relative">
            {/* Left: Main Logo + Status */}
            <div className="flex gap-6">
              <div className="flex items-center gap-4 bg-gradient-to-r from-nav-bg/60 to-transparent p-2 rounded-lg">
                <div className="relative flex items-center justify-center h-20 w-20 border border-border/30 rounded-full bg-[#0a111a]">
                  <Shield size={36} className="text-text-primary" />
                  <Hexagon size={20} className="absolute text-secondary" />
                </div>
                <div className="flex flex-col">
                  <span className="text-3xl font-bold tracking-[0.2em] text-text-primary uppercase leading-tight">
                    IBVAP
                  </span>
                  <span className="text-xs text-text-muted font-mono tracking-wider mt-1">
                    TACTICAL SURVEILLANCE NODE
                  </span>
                </div>
              </div>

              {/* System Status (New widget to fill empty space) */}
              <div className="border border-border/30 bg-[#0a111a]/80 p-3 rounded flex flex-col w-48 justify-center">
                <div className="text-green-healthy font-bold text-xs mb-1 flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-green-healthy shadow-[0_0_8px_#10b981] animate-pulse" /> SYSTEM ONLINE
                </div>
                <div className="flex justify-between text-[11px] font-mono text-text-muted mt-2">
                  <span>NETWORK</span>
                  <span className="text-text-primary font-semibold">ENCRYPTED</span>
                </div>
                <div className="flex justify-between text-[11px] font-mono text-text-muted mt-1">
                  <span>UPTIME</span>
                  <span className="text-text-primary font-semibold">99.9%</span>
                </div>
              </div>
            </div>

            {/* Right: Telemetry Dashboards */}
            <div className="flex gap-2">
              {/* Event Chronology */}
              <div className="border border-border/30 bg-[#0a111a]/80 p-3 rounded flex flex-col w-56 text-xs font-mono text-text-muted justify-between">
                <div className="text-text-primary text-xs font-bold mb-2 border-b border-border/30 pb-1">
                  EVENT CHRONOLOGY
                </div>
                <div className="flex justify-between">
                  <span>07:17:59</span>{" "}
                  <span className="text-green-healthy font-semibold">gate_open</span>
                </div>
                <div className="flex justify-between">
                  <span>07:17:58</span>{" "}
                  <span className="text-secondary font-semibold">vehicle_detect</span>
                </div>
                <div className="flex justify-between">
                  <span>07:17:57</span>{" "}
                  <span className="text-text-muted">system_heartbeat</span>
                </div>
              </div>

              {/* Sensor Hub */}
              <div className="border border-border/30 bg-[#0a111a]/80 p-3 rounded flex flex-col w-44">
                <div className="text-amber-warning font-bold text-xs mb-2 flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-warning" />{" "}
                  Sensor Hub
                </div>
                <div className="flex items-end justify-between h-full">
                  <div className="flex flex-col">
                    <span className="text-[10px] text-text-muted">
                      Temperature
                    </span>
                    <span className="text-base font-mono text-text-primary mt-0.5">
                      16°C
                    </span>
                  </div>
                  {/* Mock Sparkline */}
                  <div className="flex items-end gap-[1px] h-8">
                    {[20, 40, 30, 70, 50, 90, 60].map((v, i) => (
                      <div
                        key={i}
                        className="w-1.5 bg-amber-warning/70"
                        style={{ height: `${v}%` }}
                      />
                    ))}
                  </div>
                </div>
              </div>

              {/* Compute Engine */}
              <div className="border border-border/30 bg-[#0a111a]/80 p-3 rounded flex flex-col w-44">
                <div className="text-secondary font-bold text-xs mb-2 flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-secondary" />{" "}
                  Compute Engine
                </div>
                <div className="flex items-end justify-between h-full">
                  <div className="flex flex-col">
                    <span className="text-[10px] text-text-muted">Load</span>
                    <span className="text-base font-mono text-text-primary mt-0.5">
                      82%
                    </span>
                  </div>
                  {/* Mock Sparkline */}
                  <div className="flex items-end gap-[1px] h-8">
                    {[60, 70, 80, 85, 90, 95, 82].map((v, i) => (
                      <div
                        key={i}
                        className="w-1.5 bg-secondary/70"
                        style={{ height: `${v}%` }}
                      />
                    ))}
                  </div>
                </div>
              </div>

              {/* AI Core */}
              <div className="border border-border/30 bg-[#0a111a]/80 p-3 rounded flex flex-col w-44">
                <div className="text-primary font-bold text-xs mb-2 flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-primary" /> AI
                  Core
                </div>
                <div className="flex items-end justify-between h-full">
                  <div className="flex flex-col">
                    <span className="text-[10px] text-text-muted">
                      Throughput
                    </span>
                    <span className="text-base font-mono text-text-primary mt-0.5">
                      1080 <span className="text-[10px]">FPS</span>
                    </span>
                  </div>
                  {/* Mock Sparkline */}
                  <div className="flex items-end gap-[1px] h-8">
                    {[80, 85, 82, 88, 90, 85, 90].map((v, i) => (
                      <div
                        key={i}
                        className="w-1.5 bg-primary/70"
                        style={{ height: `${v}%` }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* BOTTOM TIER: Navigation & Tools */}
        <div className="flex items-center justify-between bg-nav-bg/40 border border-border/20 rounded-md p-1 mt-1">
          {/* Layouts */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 pl-3">
              <button
                onClick={() => setLayout("2x3")}
                className={`flex flex-col items-center justify-center w-20 h-10 rounded text-[10px] font-bold tracking-widest transition-colors ${layout === "2x3" ? "bg-primary text-white" : "text-text-secondary hover:text-text-primary"}`}
              >
                <span>2x3</span>
                <span>MATRIX</span>
              </button>
              <button
                onClick={() => setLayout("1+5")}
                className={`flex flex-col items-center justify-center w-20 h-10 rounded text-[10px] font-bold tracking-widest transition-colors ${layout === "1+5" ? "bg-primary text-white" : "text-text-secondary hover:text-text-primary"}`}
              >
                <span>1+5</span>
                <span>FOCUS</span>
              </button>
              <button
                onClick={() => setLayout("1x1")}
                className={`flex flex-col items-center justify-center w-20 h-10 rounded text-[10px] font-bold tracking-widest transition-colors ${layout === "1x1" ? "bg-primary text-white" : "text-text-secondary hover:text-text-primary"}`}
              >
                <span>1x1</span>
                <span>CINEMA</span>
              </button>
            </div>
          </div>

          {/* Action Toolbar */}
          <div className="flex items-center gap-3 pr-2">
            {/* Hardware Specs */}
            <div className="flex items-center gap-2 px-4 h-10 border border-border/30 rounded bg-[#0a111a]/50 text-xs font-mono text-secondary">
              <Cpu size={14} /> RTX 2050: 124 MB / 4096 MB
            </div>
            <div className="flex items-center gap-2 px-4 h-10 border border-border/30 rounded bg-[#0a111a]/50 text-xs font-mono text-green-healthy">
              <Activity size={14} /> YOLO26M (CUDA)
            </div>

            {/* Action Buttons */}
            <button className="flex items-center gap-2 px-4 h-10 border border-border/30 rounded text-[11px] font-bold tracking-wider text-green-healthy hover:bg-white/5 transition-colors">
              <Volume2 size={14} /> AUDIO ON
            </button>
            <button
              onClick={() => onActionClick("watchlist")}
              className="flex items-center gap-2 px-4 h-10 border border-border/30 rounded text-[11px] font-bold tracking-wider text-text-primary hover:bg-white/5 transition-colors"
            >
              <Users size={14} /> WATCHLIST
            </button>
            <button
              onClick={() => onActionClick("anpr")}
              className="flex flex-col items-center justify-center px-4 h-10 border border-border/30 rounded text-[11px] font-bold tracking-wider text-text-primary hover:bg-white/5 transition-colors"
            >
              <div className="flex items-center gap-1">
                <Car size={12} className="text-red-danger" /> ANPR
              </div>
              <span>LOG</span>
            </button>
            <button
              onClick={() => onActionClick("zone")}
              className="flex flex-col items-center justify-center px-4 h-10 border border-border/30 rounded text-[11px] font-bold tracking-wider text-text-primary hover:bg-white/5 transition-colors"
            >
              <div className="flex items-center gap-1">
                <Map size={12} /> ZONE
              </div>
              <span>EDITOR</span>
            </button>

            <button
              onClick={() => onActionClick("incidents")}
              className="relative flex flex-col items-center justify-center px-4 h-10 border border-red-danger/50 rounded text-[11px] font-bold tracking-wider text-red-danger bg-red-danger/5 hover:bg-red-danger/10 transition-colors"
            >
              <div className="flex items-center gap-1">
                <AlertTriangle size={12} />
              </div>
              <span>INCIDENTS</span>
              <span className="absolute -top-1.5 -right-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-danger px-1 text-[10px] font-bold text-white shadow-[0_0_8px_rgba(239,68,68,0.6)]">
                0
              </span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
