"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Maximize, Focus, Camera as CameraIcon, ShieldOff } from "lucide-react";

export default function CameraCard({ camera, apiUrl, isSelected, onSelect }) {
  const [isFullscreen, setIsFullscreen] = useState(false);

  const online = camera.status === "ONLINE";
  const connecting = camera.status === "CONNECTING";

  // Close fullscreen with Escape
  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === "Escape") {
        setIsFullscreen(false);
      }
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
      <motion.button
        type="button"
        onClick={onSelect}
        className={`
          group relative w-full aspect-video overflow-hidden rounded-lg bg-card-bg text-left focus:outline-none
          shadow-[0_4px_24px_rgba(0,0,0,0.2)] hover:shadow-[0_8px_32px_rgba(0,0,0,0.3)] transition-all duration-300
          border border-border/20 ${isSelected ? "ring-1 ring-border-selected" : ""}
        `}
      >
        {/* Main Video Area */}
        <div className="absolute inset-0 bg-video-canvas">
          {online || connecting ? (
            <img
              src={`${apiUrl}/api/stream/${camera.id}`}
              alt={`${camera.name} feed`}
              className="h-full w-full object-cover transition-transform duration-500 ease-out group-hover:scale-105"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-slate-800 via-slate-900 to-slate-950">
              <div className="absolute inset-0 opacity-10 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI4IiBoZWlnaHQ9IjgiPgo8cmVjdCB3aWR0aD0iOCIgaGVpZ2h0PSI4IiBmaWxsPSIjZmZmIiBmaWxsLW9wYWNpdHk9IjAuMDUiLz4KPHBhdGggZD0iTTAgMEw4IDhaTTAgOEw4IDBaIiBzdHJva2U9IiMwMDAiIHN0cm9rZS1vcGFjaXR5PSIwLjEiLz4KPC9zdmc+')] mix-blend-overlay"></div>
              <div className="relative text-center flex flex-col items-center">
                <ShieldOff size={42} className="mb-4 text-text-muted opacity-40 stroke-[1.5]" />
                <p className="text-[13px] font-semibold tracking-wide text-text-muted uppercase">Camera Feed Offline</p>
                <p className="mt-1 text-[11px] text-text-muted/60 font-medium">Link terminated</p>
              </div>
            </div>
          )}
        </div>

        {/* Overlay Content */}
        <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-transparent to-black/30 pointer-events-none" />

        {/* Top Header Information */}
        <div className="absolute top-0 left-0 right-0 flex justify-between items-start p-4 pointer-events-none">
          <div className="flex flex-col gap-1">
            <h2 className="text-[13px] font-semibold tracking-wide text-white drop-shadow-md">
              {camera.name}
            </h2>
            <div className="flex items-center gap-1.5">
              <span className={`h-1.5 w-1.5 rounded-full ${online ? "bg-green-healthy shadow-[0_0_8px_rgba(16,185,129,0.5)]" : connecting ? "bg-amber-warning" : "bg-text-muted"} ${online ? "animate-pulse" : ""}`} />
              <span className="text-[10px] font-medium text-white/70 uppercase tracking-widest drop-shadow-sm">
                {camera.status}
              </span>
            </div>
          </div>
          <div className="flex flex-col items-end gap-1">
            <span className="font-mono text-[11px] font-medium text-white/60 drop-shadow-sm">
              30 FPS
            </span>
          </div>
        </div>

        {/* Bottom Actions Bar (Hover) */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          whileHover={{ opacity: 1, y: 0 }}
          className="absolute bottom-4 left-1/2 flex -translate-x-1/2 items-center gap-2 rounded-lg border border-white/10 bg-black/60 px-2 py-1.5 backdrop-blur-md opacity-0 transition-opacity duration-300 group-hover:opacity-100"
          onClick={(e) => e.stopPropagation()}
        >
          <button 
            onClick={() => setIsFullscreen(true)}
            className="rounded p-1.5 text-white/70 hover:bg-white/20 hover:text-white transition-colors"
            title="Fullscreen"
          >
            <Maximize size={14} />
          </button>
          <button 
            onClick={onSelect}
            className="rounded p-1.5 text-white/70 hover:bg-white/20 hover:text-white transition-colors"
            title="Focus feed"
          >
            <Focus size={14} />
          </button>
          <button 
            className="rounded p-1.5 text-white/70 hover:bg-white/20 hover:text-white transition-colors"
            title="Snapshot"
          >
            <CameraIcon size={14} />
          </button>
        </motion.div>
      </motion.button>

      {/* Fullscreen Modal */}
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
              className="relative flex h-full w-full flex-col overflow-hidden rounded-xl border border-border bg-video-canvas shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="absolute top-4 right-4 z-10">
                <button
                  onClick={() => setIsFullscreen(false)}
                  className="flex h-8 w-8 items-center justify-center rounded-lg bg-black/50 text-white/70 backdrop-blur-md hover:bg-white/10 hover:text-white transition-colors border border-white/10"
                >
                  ✕
                </button>
              </div>
              
              <div className="relative flex flex-1 items-center justify-center bg-black overflow-hidden">
                {online || connecting ? (
                  <img
                    src={`${apiUrl}/api/stream/${camera.id}`}
                    alt={`${camera.name} live feed`}
                    className="max-h-full max-w-full object-contain"
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center h-full w-full bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-slate-800 via-slate-900 to-slate-950">
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