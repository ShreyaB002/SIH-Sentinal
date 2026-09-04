import { motion, AnimatePresence } from "framer-motion";
import { X, Users, Car, Map, AlertTriangle } from "lucide-react";

export default function InteractiveModals({ activeModal, onClose, events = [] }) {
  if (!activeModal) return null;

  const renderContent = () => {
    switch (activeModal) {
      case "watchlist":
        return (
          <div className="flex flex-col gap-4">
            <h3 className="text-sm font-bold text-white border-b border-white/10 pb-2 flex items-center gap-2">
              <Users size={16} /> WATCHLIST SCENARIOS
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-[#121824] p-3 rounded border border-white/10">
                <div className="text-secondary font-bold text-[11px] mb-1">SCENARIO: VIP MOVEMENT</div>
                <div className="text-[10px] text-text-muted">Target: Convey Alpha</div>
                <div className="text-[10px] text-green-healthy mt-1">STATUS: ACTIVE</div>
              </div>
              <div className="bg-[#121824] p-3 rounded border border-white/10">
                <div className="text-red-danger font-bold text-[11px] mb-1">SCENARIO: THREAT PERSON</div>
                <div className="text-[10px] text-text-muted">Target: Unknown ID-738</div>
                <div className="text-[10px] text-green-healthy mt-1">STATUS: ACTIVE</div>
              </div>
            </div>
          </div>
        );
      case "anpr":
        return (
          <div className="flex flex-col gap-4">
            <h3 className="text-sm font-bold text-white border-b border-white/10 pb-2 flex items-center gap-2">
              <Car size={16} className="text-red-danger" /> ANPR INGRESS LOG
            </h3>
            <table className="w-full text-left text-[10px] text-text-muted">
              <thead>
                <tr className="text-white border-b border-white/10">
                  <th className="pb-1">TIMESTAMP</th>
                  <th className="pb-1">PLATE NUMBER</th>
                  <th className="pb-1">CAMERA</th>
                  <th className="pb-1">STATUS</th>
                </tr>
              </thead>
              <tbody>
                <tr><td className="py-1">07:12:45</td><td className="font-mono text-secondary">MH 12 AB 1234</td><td>Sector 1</td><td className="text-green-healthy">CLEARED</td></tr>
                <tr><td className="py-1">07:05:10</td><td className="font-mono text-secondary">DL 01 ZZ 9999</td><td>Sector 2</td><td className="text-amber-warning">FLAGGED</td></tr>
                <tr><td className="py-1">06:45:00</td><td className="font-mono text-secondary">KA 05 XY 5678</td><td>Sector 5</td><td className="text-green-healthy">CLEARED</td></tr>
              </tbody>
            </table>
          </div>
        );
      case "zone":
        return (
          <div className="flex flex-col gap-4">
            <h3 className="text-sm font-bold text-white border-b border-white/10 pb-2 flex items-center gap-2">
              <Map size={16} /> ZONAL ADDITIONS
            </h3>
            <div className="flex flex-col gap-2">
              <div className="flex justify-between items-center bg-[#121824] p-2 rounded border border-white/10 text-[11px]">
                <span className="text-white">Zone Alpha (Perimeter)</span>
                <span className="text-text-muted">Added: 01-09-2026</span>
                <span className="text-green-healthy">ACTIVE</span>
              </div>
              <div className="flex justify-between items-center bg-[#121824] p-2 rounded border border-white/10 text-[11px]">
                <span className="text-white">Zone Bravo (Drop Gate)</span>
                <span className="text-text-muted">Added: 28-08-2026</span>
                <span className="text-green-healthy">ACTIVE</span>
              </div>
              <div className="flex justify-between items-center bg-[#121824] p-2 rounded border border-white/10 text-[11px]">
                <span className="text-white">Restricted Zone X</span>
                <span className="text-text-muted">Added: 15-08-2026</span>
                <span className="text-amber-warning">MAINTENANCE</span>
              </div>
            </div>
          </div>
        );
      case "incidents":
        return (
          <div className="flex flex-col gap-4 h-full max-h-[60vh]">
            <h3 className="text-sm font-bold text-white border-b border-white/10 pb-2 flex items-center gap-2">
              <AlertTriangle size={16} className="text-red-danger" /> INCIDENT CHRONOLOGY
            </h3>
            <div className="overflow-y-auto flex-1 pr-2 custom-scrollbar">
              {events.length === 0 ? (
                <div className="text-[11px] text-text-muted text-center mt-4">No recent incidents.</div>
              ) : (
                <div className="flex flex-col gap-2">
                  {events.map((ev, i) => (
                    <div key={i} className="flex justify-between items-center bg-red-danger/10 p-2 rounded border border-red-danger/30 text-[11px]">
                      <span className="text-white">{ev.label || ev.type} Detected</span>
                      <span className="text-text-muted">{ev.camera_id}</span>
                      <span className="font-mono text-red-danger">{new Date(ev.timestamp * 1000).toLocaleTimeString()}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.95, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.95, y: 20 }}
          className="relative w-full max-w-2xl bg-[#0a111a] border border-white/20 rounded-xl shadow-[0_0_40px_rgba(0,0,0,0.8)] overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header/Drag Handle Area */}
          <div className="h-1 bg-gradient-to-r from-secondary via-primary to-red-danger w-full" />
          
          <button 
            onClick={onClose}
            className="absolute top-4 right-4 text-text-muted hover:text-white transition-colors"
          >
            <X size={18} />
          </button>
          
          <div className="p-6">
            {renderContent()}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
