"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Zap, Maximize, Focus, Camera as CameraIcon, ShieldOff, Wifi, Battery, Activity, Monitor, Server, Globe, Code, AlertCircle, Layers } from "lucide-react";

export default function CameraCard({ camera, apiUrl, isSelected, onSelect }) {
  const [isFullscreen, setIsFullscreen] = useState(false);

  const online = camera.status === "ONLINE";
  const connecting = camera.status === "CONNECTING";
  const camNumber = camera.id.replace("cam_", "").replace(/^0+/, "");
  const isWatchtower6 = camera.name.includes("Watchtower 6");

  // Close fullscreen with Escape
  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === "Escape") setIsFullscreen(false);
    }
    if (isFullscreen) {
      document.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [isFullscreen]);

  return (
    <>
      <div
        onClick={onSelect}
        className={`
          flex flex-col overflow-hidden rounded border border-border/30 bg-[#0a111a]
          shadow-[0_4px_24px_rgba(0,0,0,0.4)] transition-all duration-300 relative
          ${isSelected ? "ring-1 ring-secondary" : ""}
        `}
      >
        {/* Card Header */}
        <div className="flex items-center justify-between px-3 py-1.5 border-b border-border/30 bg-[#0a111a]">
          <div className="flex items-center gap-2">
            <span className={`h-1.5 w-1.5 rounded-full ${online ? "bg-green-healthy shadow-[0_0_8px_rgba(16,185,129,0.5)]" : "bg-red-danger"}`} />
            <h2 className="text-[11px] font-bold tracking-wide text-text-primary uppercase">
              {camera.name.includes("—") ? camera.name : `Sector ${camNumber} — ${camera.name}`}
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[9px] font-medium text-text-muted">
              BOP Alpha
            </span>
            <span className="text-[9px] font-bold text-secondary tracking-widest">
              30 FPS
            </span>
          </div>
        </div>

        {/* Video Area */}
        <div className="relative w-full aspect-video bg-[#05080f] overflow-hidden group">
          {online || connecting ? (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`${apiUrl}/api/stream/${camera.id}`}
                alt={`${camera.name} feed`}
                className="h-full w-full object-cover"
              />
              
              {/* OVERLAYS FOR ONLINE STATE */}
              
              {/* Top Left: Grid Index */}
              <div className="absolute top-2 left-2 bg-black/60 border border-white/10 px-2 py-0.5 rounded text-[9px] font-mono text-white">
                Grid Index 2A
              </div>

              {/* Top Right: Sensor Health box */}
              <div className="absolute top-2 right-2 bg-black/70 border border-white/10 p-1.5 rounded flex flex-col gap-0.5 text-[8px] font-mono text-white min-w-[120px] backdrop-blur-sm">
                <div className="flex justify-between items-center border-b border-white/10 pb-0.5 mb-0.5">
                  <span className="text-text-muted">SENSOR HEALTH:</span>
                  <span className="text-green-healthy font-bold">98%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-text-muted">BANDWIDTH:</span>
                  <span>15 Mbps</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-text-muted">BITRATE:</span>
                  <span>4K/60</span>
                </div>
              </div>

              {/* Bottom Right: Latency Graph */}
              <div className="absolute bottom-6 right-2 bg-black/70 border border-white/10 p-1.5 rounded flex flex-col w-[120px] backdrop-blur-sm">
                <div className="text-[8px] font-mono text-text-muted mb-1 flex items-center justify-between">
                  <span>LATENCY (RTT)</span>
                  <span className="text-secondary font-bold">8.12 ms</span>
                </div>
                <div className="flex items-end gap-[1px] h-8 border-b border-l border-white/20 pl-1 pb-1">
                  {[20, 25, 30, 20, 15, 35, 40, 20, 25, 30, 25, 20].map((v, i) => (
                    <div key={i} className="flex-1 bg-secondary/80 hover:bg-secondary transition-colors" style={{ height: `${v}%` }} />
                  ))}
                </div>
              </div>

              {/* Bottom Left: Wifi & Power */}
              <div className="absolute bottom-6 left-2 flex flex-col gap-1">
                <div className="flex items-center gap-1.5 bg-black/60 px-1.5 py-0.5 rounded border border-white/10 text-[8px] font-mono text-secondary backdrop-blur-sm">
                  <Wifi size={10} /> <span>WIFI RSSI<br/>238%</span>
                </div>
                <div className="flex items-center gap-1.5 bg-black/60 px-1.5 py-0.5 rounded border border-white/10 text-[8px] font-mono text-green-healthy backdrop-blur-sm">
                  <Battery size={10} /> <span>POWER STATUS</span>
                </div>
              </div>

              {/* Site Overview Mock (only for Sector 6) */}
              {isWatchtower6 && (
                <div className="absolute bottom-6 right-36 bg-black/80 border border-white/20 p-2 rounded-lg shadow-2xl backdrop-blur-md transform scale-110">
                  <div className="text-[7px] font-bold text-white mb-1 tracking-widest">SITE OVERVIEW</div>
                  <div className="relative w-24 h-16 border border-white/10 rounded overflow-hidden">
                    {/* Isometric mock drawing */}
                    <div className="absolute inset-0 bg-[#0a111a] flex items-center justify-center transform rotate-x-[60deg] rotate-z-45">
                       <div className="w-16 h-16 border border-white/20 grid grid-cols-2 grid-rows-2">
                         <div className="border border-white/10 relative"><div className="absolute inset-2 bg-green-healthy/50 rounded-full blur-[2px]" /></div>
                         <div className="border border-white/10 relative"><div className="absolute inset-3 bg-secondary/50 rounded-full blur-[2px]" /></div>
                         <div className="border border-white/10 relative"><div className="absolute inset-1 bg-amber-warning/50 rounded-full blur-[2px]" /></div>
                         <div className="border border-white/10 relative"><div className="absolute inset-2 bg-red-danger/50 rounded-full blur-[2px]" /></div>
                       </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            // SIGNAL LOST STATE
            <div className="flex flex-col h-full w-full items-center justify-center bg-[#05080f] relative overflow-hidden">
              {/* Scanline overlay */}
              <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:100%_4px] pointer-events-none" />
              
              <h3 className="text-red-danger text-[18px] font-bold tracking-[0.3em] mb-8 drop-shadow-[0_0_8px_rgba(239,68,68,0.5)]">
                SIGNAL LOST
              </h3>

              {/* Connection Diagram */}
              <div className="flex items-center gap-4 mb-8">
                <div className="flex flex-col items-center gap-2 text-text-muted">
                  <Monitor size={20} />
                </div>
                <div className="h-[2px] w-8 bg-text-muted/30" />
                <div className="flex flex-col items-center gap-2 text-red-danger p-2 border border-red-danger/50 rounded-md bg-red-danger/10 relative shadow-[0_0_15px_rgba(239,68,68,0.2)]">
                  <Code size={20} />
                  {/* Error line */}
                  <div className="absolute -top-3 -right-3 text-red-danger">
                    <AlertCircle size={14} fill="black" />
                  </div>
                </div>
                <div className="h-[2px] w-8 bg-text-muted/30" />
                <div className="flex flex-col items-center gap-2 text-text-muted">
                  <Server size={20} />
                </div>
                <div className="h-[2px] w-8 bg-text-muted/30" />
                <div className="flex flex-col items-center gap-2 text-text-muted">
                  <Globe size={20} />
                </div>
              </div>

              <button className="px-6 py-1.5 bg-[#1a2333] border border-white/10 text-[10px] text-text-primary tracking-widest font-bold rounded hover:bg-[#233147] transition-colors">
                DIAGNOSE
              </button>
            </div>
          )}

          {/* Hover Actions */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            whileHover={{ opacity: 1, y: 0 }}
            className="absolute bottom-2 left-1/2 flex -translate-x-1/2 items-center gap-2 rounded border border-white/10 bg-black/80 px-2 py-1 backdrop-blur-md opacity-0 transition-opacity duration-300 group-hover:opacity-100 z-10"
            onClick={(e) => e.stopPropagation()}
          >
            <button 
              onClick={() => setIsFullscreen(true)}
              className="rounded p-1 text-white/70 hover:bg-white/20 hover:text-white transition-colors"
              title="Fullscreen"
            >
              <Maximize size={12} />
            </button>
            <button 
              onClick={onSelect}
              className="rounded p-1 text-white/70 hover:bg-white/20 hover:text-white transition-colors"
              title="Focus feed"
            >
              <Focus size={12} />
            </button>
            <button 
              className="rounded p-1 text-white/70 hover:bg-white/20 hover:text-white transition-colors"
              title="Snapshot"
            >
              <CameraIcon size={12} />
            </button>
          </motion.div>
        </div>

        {/* Card Footer */}
        <div className="flex items-center justify-between px-3 py-1 border-t border-border/30 bg-[#0a111a] relative">
          <div className="flex items-center gap-1">
            <Zap size={10} className="text-amber-warning fill-amber-warning" />
            <span className="text-[9px] font-medium text-text-muted">
              8ms latency
            </span>
          </div>
          <span className={`text-[9px] font-bold tracking-widest ${online ? 'text-green-healthy' : 'text-text-muted'}`}>
            {camera.status}
          </span>
          {/* subtle glow if online */}
          {online && <div className="absolute right-0 top-0 bottom-0 w-16 bg-gradient-to-l from-green-healthy/10 to-transparent pointer-events-none" />}
        </div>
      </div>

      {/* Fullscreen Modal (unchanged behavior, updated colors) */}
      <AnimatePresence>
        {isFullscreen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-[100] flex items-center justify-center bg-app-bg/95 p-6 backdrop-blur-md"
            onClick={() => setIsFullscreen(false)}
          >
            <div 
              className="relative flex h-full w-full flex-col overflow-hidden rounded-xl border border-border/30 bg-[#05080f] shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="absolute top-4 right-4 z-10">
                <button
                  onClick={() => setIsFullscreen(false)}
                  className="flex h-8 w-8 items-center justify-center rounded bg-black/50 text-white/70 backdrop-blur-md hover:bg-white/10 hover:text-white transition-colors border border-white/10"
                >
                  ✕
                </button>
              </div>
              
              <div className="relative flex flex-1 items-center justify-center overflow-hidden">
                {online || connecting ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={`${apiUrl}/api/stream/${camera.id}`}
                    alt={`${camera.name} live feed`}
                    className="max-h-full max-w-full object-contain"
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center h-full w-full">
                    <ShieldOff size={64} className="mb-4 text-text-muted opacity-40 stroke-[1]" />
                    <p className="text-sm font-semibold tracking-widest text-text-muted uppercase">Camera Offline</p>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}