"use client";

import { useEffect, useState } from "react";

import Header from "@/components/Header";
import CameraCard from "@/components/CameraCard";
import EventLog from "@/components/EventLog";
import useAlertsWebSocket from "@/hooks/useAlertsWebSocket";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000";

export default function Home() {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const {
    events,
    wsStatus,
    clearEvents,
  } = useAlertsWebSocket();

  async function fetchCameras() {
    try {
      const response = await fetch(
        `${API_URL}/api/cameras`
      );

      if (!response.ok) {
        throw new Error(
          `HTTP ${response.status}`
        );
      }

      const data = await response.json();

      setCameras(data);
      setError("");
    } catch (err) {
      console.error(err);
      setError("Could not connect to FastAPI");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchCameras();

    const interval = setInterval(
      fetchCameras,
      5000
    );

    return () => clearInterval(interval);
  }, []);

  return (
    <main className="min-h-screen bg-black p-6 text-white">

      <Header
        cameras={cameras}
        wsStatus={wsStatus}
      />

      {error && (
        <div className="mb-6 rounded-lg border border-red-900 bg-red-950/40 p-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex min-h-[400px] items-center justify-center">
          <p className="text-zinc-500">
            Loading cameras...
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">

          {/* Cameras */}
          <section>
            <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
              {cameras.map((camera) => (
                <CameraCard
                  key={camera.id}
                  camera={camera}
                  apiUrl={API_URL}
                />
              ))}
            </div>
          </section>

          
          <EventLog
            events={events}
            onClear={clearEvents}
          />

        </div>
      )}

    </main>
  );
}