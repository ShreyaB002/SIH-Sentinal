"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X, ShieldAlert, AlertTriangle, Eye } from "lucide-react";

const MAX_LOG_ENTRIES = 200;

function formatTime(iso) {
  try {
    const date = new Date(iso);
    const pad = (number) => String(number).padStart(2, "0");
    return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
  } catch {
    return "--:--:--";
  }
}

function EventCard({ event }) {
  const isIntrusion = event?.event_type === "INTRUSION";
  const confidence = event?.confidence !== undefined && event?.confidence !== null
    ? `${(event.confidence * 100).toFixed(0)}%`
    : "";
  const zone = event?.zone || "";

  // Severity based on type for demo
  const severity = isIntrusion ? "critical" : "medium";

  const getSeverityStyles = () => {
    if (severity === "critical") return "border-l-red-danger border-border/50 bg-app-bg";
    if (severity === "high") return "border-l-amber-warning border-border/50 bg-app-bg";
    return "border-l-blue-primary border-border/50 bg-app-bg";
  };

  const Icon = severity === "critical" ? ShieldAlert : AlertTriangle;
  const iconColor = severity === "critical" ? "text-red-danger" : "text-amber-warning";

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 20, scale: 0.98 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 20, scale: 0.98 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className={`relative mb-3 flex flex-col rounded-r-[10px] border-y border-r border-l-4 p-3 shadow-[0_4px_12px_rgba(24,55,85,0.08)] transition-all duration-[200ms] hover:shadow-[0_8px_20px_rgba(24,55,85,0.15)] hover:-translate-y-[2px] ${getSeverityStyles()}`}
    >
      {/* Top row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <Icon size={14} className={iconColor} />
          <span className={`text-xs font-bold uppercase tracking-wider ${iconColor}`}>
            {isIntrusion ? "Intrusion" : "Detection"}
          </span>
          <span className="rounded bg-black/5 px-1.5 py-0.5 text-[9px] font-medium text-text-muted uppercase tracking-wider">
            AI Detection
          </span>
        </div>
        <span className="font-mono text-[10px] text-text-muted">
          {formatTime(event?.timestamp)}
        </span>
      </div>

      {/* Details */}
      <div className="mt-2 text-[13px] font-semibold text-text-primary">
        {event?.label || "Unknown Object"}
        {confidence && <span className="ml-1.5 text-[11px] font-medium text-text-secondary opacity-70">({confidence} CONF)</span>}
      </div>

      {/* Meta */}
      <div className="mt-2.5 flex items-center justify-between">
        <div className="flex flex-col gap-0.5 text-[11px] text-text-secondary font-medium">
          <span>{event?.camera_name || event?.camera_id}</span>
          {zone && <span className="text-text-muted flex items-center gap-1"><MapPin size={10}/> {zone}</span>}
        </div>
        
        <div className="flex gap-1">
          <button className="rounded border border-border bg-card-bg px-2 py-1 text-[9px] font-medium text-text-secondary hover:bg-black/5 transition-colors">
            Ack
          </button>
          <button className="flex items-center justify-center rounded border border-border bg-card-bg px-2 py-1 text-text-secondary hover:bg-black/5 transition-colors" title="View Feed">
            <Eye size={12} />
          </button>
        </div>
      </div>
    </motion.div>
  );
}

// Dummy MapPin since it's not imported at top
function MapPin(props) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width={props.size} height={props.size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/>
      <circle cx="12" cy="10" r="3"/>
    </svg>
  );
}

export default function EventLog({ events = [], onClear, onClose }) {
  const visibleEvents = events.slice(0, MAX_LOG_ENTRIES);

  return (
    <motion.aside 
      initial={{ x: 320, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 320, opacity: 0 }}
      transition={{ type: "spring", bounce: 0, duration: 0.3 }}
      className="flex h-full w-80 flex-col border-l border-border bg-card-bg shadow-lg z-30"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border bg-app-bg px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
            Incident Log
            <span className="rounded bg-red-danger/10 px-1.5 py-0.5 text-[10px] font-bold text-red-danger">
              {events.length}
            </span>
          </h2>
        </div>

        <div className="flex items-center gap-2">
          {events.length > 0 && (
            <button
              onClick={onClear}
              className="rounded-md px-2 py-1 text-[10px] font-medium text-text-secondary hover:bg-black/5 transition-colors uppercase tracking-wider"
            >
              Clear
            </button>
          )}
          <div className="h-4 w-px bg-border" />
          <button 
            onClick={onClose}
            className="flex h-7 w-7 items-center justify-center rounded-md text-text-muted hover:bg-black/5 hover:text-text-primary transition-colors"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Events List */}
      <div className="flex-1 overflow-y-auto p-3 dark-scroll">
        {visibleEvents.length === 0 ? (
          <div className="flex min-h-[300px] flex-col items-center justify-center text-center">
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-app-bg border border-border">
              <ShieldAlert size={20} className="text-text-muted opacity-50" />
            </div>
            <p className="text-xs font-semibold text-text-secondary">No Active Incidents</p>
            <p className="mt-1 text-[10px] text-text-muted max-w-[200px]">
              AI detection events will appear here when threats are identified.
            </p>
          </div>
        ) : (
          <motion.div layout>
            <AnimatePresence initial={false}>
              {visibleEvents.map((event, index) => (
                <EventCard key={event?.id ?? `${event?.timestamp}-${index}`} event={event} />
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </div>
    </motion.aside>
  );
}