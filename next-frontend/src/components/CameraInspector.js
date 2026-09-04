"use client";

import { motion } from "framer-motion";
import { X, Maximize, Edit3, Settings, Activity, Map, Camera, Video } from "lucide-react";

export default function CameraInspector({ camera, apiUrl, onClose, onFullscreen }) {
  if (!camera) return null;

  const online = camera.status === "ONLINE";

  return (
    <motion.aside 
      initial={{ x: 300, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 300, opacity: 0 }}
      transition={{ type: "spring", bounce: 0, duration: 0.3 }}
      className="flex h-full w-80 flex-col border-l border-border bg-card-secondary shadow-lg z-30"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3 bg-header-bg">
        <div>
          <h2 className="text-sm font-semibold text-text-primary">Camera Inspector</h2>
          <p className="text-[10px] text-text-muted mt-0.5">{camera.id}</p>
        </div>
        <button 
          onClick={onClose}
          className="flex h-7 w-7 items-center justify-center rounded-md text-text-muted hover:bg-black/5 hover:text-text-primary transition-colors"
        >
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        
        {/* Preview */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-text-secondary uppercase tracking-wider">Live Preview</span>
            <span className={`text-[10px] font-bold tracking-wider ${online ? "text-green-healthy" : "text-red-danger"}`}>
              {camera.status}
            </span>
          </div>
          <div className="relative aspect-video overflow-hidden rounded-lg border border-border bg-video-canvas shadow-inner">
            {online ? (
              <img
                src={`${apiUrl}/api/stream/${camera.id}`}
                alt={`${camera.name} inspector feed`}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-text-muted">
                <Video size={24} className="opacity-30" />
              </div>
            )}
            {online && (
              <div className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-green-healthy shadow-[0_0_8px_rgba(31,169,113,0.8)]" />
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="grid grid-cols-2 gap-2">
          <button 
            onClick={onFullscreen}
            className="flex items-center justify-center gap-2 rounded-lg border border-border bg-card-bg py-2 text-xs font-medium text-text-primary shadow-sm hover:bg-black/5 hover:border-border-accent transition-colors"
          >
            <Maximize size={14} className="text-text-secondary" /> Fullscreen
          </button>
          <button className="flex items-center justify-center gap-2 rounded-lg border border-border bg-card-bg py-2 text-xs font-medium text-text-primary shadow-sm hover:bg-black/5 hover:border-border-accent transition-colors">
            <Edit3 size={14} className="text-text-secondary" /> Edit Zones
          </button>
        </div>

        {/* Info */}
        <div className="space-y-3 rounded-lg border border-border bg-card-bg p-3 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-text-secondary">
              <Camera size={14} />
              <span className="text-xs font-medium">Name</span>
            </div>
            <span className="text-xs text-text-primary">{camera.name}</span>
          </div>
          
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-text-secondary">
              <Map size={14} />
              <span className="text-xs font-medium">Location</span>
            </div>
            <span className="text-xs text-text-primary">Western Sector</span>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-text-secondary">
              <Activity size={14} />
              <span className="text-xs font-medium">Stream</span>
            </div>
            <span className="text-xs text-text-primary">RTSP / H.264</span>
          </div>
        </div>

      </div>
    </motion.aside>
  );
}
