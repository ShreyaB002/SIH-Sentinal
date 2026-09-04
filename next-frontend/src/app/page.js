"use client";

import { useEffect, useState, useCallback } from "react";
import { AnimatePresence } from "framer-motion";
import Header from "@/components/Header";
import CameraCard from "@/components/CameraCard";
import CameraInspector from "@/components/CameraInspector";
import EventLog from "@/components/EventLog";
import InteractiveModals from "@/components/InteractiveModals";
import useAlertsWebSocket from "@/hooks/useAlertsWebSocket";

export default function Home() {
  const [apiUrl, setApiUrl] = useState("http://127.0.0.1:8000");
  const [activeModal, setActiveModal] = useState(null);
  const [showAlert, setShowAlert] = useState(true);
  
  useEffect(() => {
    if (typeof window !== "undefined") {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setApiUrl(`http://${window.location.hostname}:8000`);
    }
  }, []);

  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  
  const [selectedCameraId, setSelectedCameraId] = useState(null);
  const [showIncidents, setShowIncidents] = useState(false);
  const [layout, setLayout] = useState("2x3");
  
  const { events, wsStatus, clearEvents } = useAlertsWebSocket();

  useEffect(() => {
    const fetchCameras = async () => {
      try {
        const response = await fetch(`${apiUrl}/api/cameras`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        setCameras(data);
        setError("");
      } catch (err) {
        console.error(err);
        setError("Could not connect to FastAPI backend. Check connection.");
      } finally {
        setLoading(false);
      }
    };

    fetchCameras();
    const interval = setInterval(fetchCameras, 5000);
    return () => clearInterval(interval);
  }, [apiUrl]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
      switch (e.key.toLowerCase()) {
        case "escape":
          setSelectedCameraId(null);
          setShowIncidents(false);
          break;
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const selectedCamera = cameras.find(c => c.id === selectedCameraId);

  // Layout handling
  let gridClasses = "grid gap-4"; // 16px gap = gap-4 in Tailwind
  if (layout === "2x3") gridClasses += " grid-cols-1 md:grid-cols-2 lg:grid-cols-3";
  else if (layout === "1+5") gridClasses += " grid-cols-3"; // Simplistic representation
  else if (layout === "1x1") gridClasses += " grid-cols-1";

  return (
    <main className="relative flex h-full flex-col bg-app-bg text-text-primary overflow-hidden">
      
      <Header
        wsStatus={wsStatus}
        layout={layout}
        setLayout={setLayout}
        onActionClick={setActiveModal}
      />

      <InteractiveModals 
        activeModal={activeModal} 
        onClose={() => setActiveModal(null)} 
        events={events} 
      />

      <div className="flex flex-1 overflow-hidden">
        {/* Main Content Area */}
        <div className="flex-1 flex flex-col p-6 overflow-y-auto dark-scroll">
          
          {loading ? (
            <div className="flex flex-1 items-center justify-center">
              <span className="text-sm font-medium tracking-wide text-text-muted">Initializing matrix...</span>
            </div>
          ) : (
            <section className="flex-1">
              <div className={gridClasses}>
                {cameras.map((camera, index) => {
                  // If 1x1 mode, only show the first one or selected one
                  if (layout === "1x1" && index !== 0 && !selectedCameraId) return null;
                  if (layout === "1x1" && selectedCameraId && camera.id !== selectedCameraId) return null;
                  
                  return (
                    <CameraCard
                      key={camera.id}
                      camera={camera}
                      apiUrl={apiUrl}
                      isSelected={selectedCameraId === camera.id}
                      onSelect={() => setSelectedCameraId(camera.id)}
                      layout={layout}
                      index={index}
                    />
                  );
                })}
              </div>
            </section>
          )}
        </div>

        {/* Right Sidebar Area */}
        <AnimatePresence mode="wait">
          {showIncidents ? (
            <EventLog 
              key="incidents"
              events={events} 
              onClear={clearEvents} 
              onClose={() => setShowIncidents(false)}
            />
          ) : selectedCamera ? (
            <CameraInspector 
              key="inspector"
              camera={selectedCamera} 
              apiUrl={apiUrl} 
              onClose={() => setSelectedCameraId(null)}
            />
          ) : null}
        </AnimatePresence>
      </div>

      {/* 3D Glass Console Footer & Alert Overlay */}
      <div className="absolute bottom-0 left-0 right-0 z-50 flex flex-col items-center pointer-events-none">
        
        {/* Floating Alert Bar */}
        <AnimatePresence>
          {showAlert && (
            <div className="mb-4 pointer-events-auto">
              <div className="flex items-center justify-between gap-4 bg-red-danger/20 border border-red-danger/50 rounded-md pl-4 pr-1 py-1 backdrop-blur-md shadow-[0_0_15px_rgba(239,68,68,0.3)]">
                <div className="flex items-center gap-2">
                  <span className="text-red-danger font-bold text-[14px]">!</span>
                  <span className="text-[12px] font-bold text-red-danger tracking-wide">
                    ALERT: Sector 4 ROAD SOUTH (Vehicle 3min)
                  </span>
                </div>
                <button 
                  onClick={() => setShowAlert(false)}
                  className="bg-red-danger/20 hover:bg-red-danger/40 border border-red-danger/40 text-[10px] font-bold text-white px-3 py-1.5 rounded transition-colors"
                >
                  ACKNOWLEDGE
                </button>
              </div>
            </div>
          )}
        </AnimatePresence>

        {/* 3D Glass Desk Surface */}
        <div 
          className="w-[80%] h-[40px] relative pointer-events-auto"
          style={{
            background: "linear-gradient(to bottom, rgba(30,41,59,0.9), rgba(15,23,42,0.95))",
            borderTop: "2px solid rgba(255,255,255,0.1)",
            boxShadow: "0 -5px 25px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.2)",
            borderTopLeftRadius: "120px",
            borderTopRightRadius: "120px",
            transform: "perspective(500px) rotateX(15deg)",
            transformOrigin: "bottom",
          }}
        >
          {/* Cyan edge reflection */}
          <div className="absolute top-0 left-[10%] right-[10%] h-[1px] bg-secondary shadow-[0_0_10px_#06B6D4]" />
        </div>
      </div>

      {/* Date & Time Overlay */}
      <div className="absolute bottom-6 right-8 z-50 flex flex-col items-end pointer-events-none">
        <span className="text-[28px] font-mono font-light text-text-primary/90 leading-tight">
          07:17:59
        </span>
        <span className="text-[14px] font-mono font-medium text-text-muted">
          01-09-2026
        </span>
      </div>

    </main>
  );
}