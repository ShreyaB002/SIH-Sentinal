"use client";

import { useEffect, useState, useCallback } from "react";
import { AnimatePresence } from "framer-motion";
import Header from "@/components/Header";
import CameraCard from "@/components/CameraCard";
import CameraInspector from "@/components/CameraInspector";
import EventLog from "@/components/EventLog";
import useAlertsWebSocket from "@/hooks/useAlertsWebSocket";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function Home() {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  
  const [selectedCameraId, setSelectedCameraId] = useState(null);
  const [showIncidents, setShowIncidents] = useState(false);
  const [layout, setLayout] = useState("2x3");
  
  const { events, wsStatus, clearEvents } = useAlertsWebSocket();

  const fetchCameras = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/cameras`);
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
  }, []);

  useEffect(() => {
    fetchCameras();
    const interval = setInterval(fetchCameras, 5000);
    return () => clearInterval(interval);
  }, [fetchCameras]);

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
                      apiUrl={API_URL}
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
              apiUrl={API_URL} 
              onClose={() => setSelectedCameraId(null)}
            />
          ) : null}
        </AnimatePresence>
      </div>

      {/* Single-line footer */}
      <footer className="h-8 border-t border-border/50 flex items-center justify-center text-[10px] uppercase tracking-widest text-text-muted opacity-80">
        Sentinel Platform v2.4.1 • End-to-End Encryption Enabled • Authorized Personnel Only
      </footer>

    </main>
  );
}