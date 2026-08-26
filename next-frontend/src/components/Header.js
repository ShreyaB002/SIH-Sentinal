"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

export default function Header({
  cameras = [],
  wsStatus = "CONNECTING",
}) {
  const [time, setTime] = useState("");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();

      setTime(
        now.toLocaleTimeString("en-IN", {
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

  const onlineCameras = cameras.filter(
    (camera) => camera.status === "ONLINE"
  ).length;

  const totalCameras = cameras.length;

  const wsOnline = wsStatus === "ONLINE";
  const wsConnecting = wsStatus === "CONNECTING";

  return (
    <motion.header
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="mb-7"
    >
      <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">

        {/* Brand */}
        <div className="flex items-center gap-4">

          {/* Logo */}
          <motion.div
            whileHover={{ scale: 1.05 }}
            className="relative flex h-12 w-12 items-center justify-center rounded-xl border border-zinc-800 bg-zinc-950"
          >
            <motion.div
              animate={{
                opacity: [0.4, 1, 0.4],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
              }}
              className={`h-3 w-3 rounded-full ${
                wsOnline
                  ? "bg-emerald-400"
                  : wsConnecting
                    ? "bg-amber-400"
                    : "bg-red-400"
              }`}
            />

            {wsOnline && (
              <motion.div
                animate={{
                  scale: [1, 1.5, 1],
                  opacity: [0.4, 0, 0.4],
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                }}
                className="absolute h-6 w-6 rounded-full border border-emerald-500/30"
              />
            )}
          </motion.div>

          {/* Title */}
          <div>
            <div className="flex items-center gap-3">

              <h1 className="text-2xl font-semibold tracking-tight text-white">
                IBVAP
              </h1>

              {/* LIVE indicator */}
              <div className="flex items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/5 px-2.5 py-1">
                <motion.span
                  animate={{
                    opacity: [1, 0.3, 1],
                  }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                  }}
                  className="h-1.5 w-1.5 rounded-full bg-emerald-400"
                />

                <span className="text-[9px] font-semibold tracking-[0.15em] text-emerald-400">
                  LIVE
                </span>
              </div>

            </div>

            <p className="mt-1 text-xs text-zinc-500">
              Intelligent Border Video Analytics Platform
            </p>
          </div>
        </div>

        {/* Stats */}
        <div className="flex flex-wrap items-center gap-2">

          {/* Cameras */}
          <motion.div
            whileHover={{ y: -2 }}
            className="flex items-center gap-3 rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3"
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500/10">
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
            </div>

            <div>
              <p className="text-[9px] uppercase tracking-widest text-zinc-600">
                Cameras
              </p>

              <p className="mt-0.5 text-xs font-semibold text-zinc-300">
                {onlineCameras}
                <span className="mx-1 text-zinc-700">/</span>
                {totalCameras}

                <span className="ml-1 font-normal text-zinc-600">
                  online
                </span>
              </p>
            </div>
          </motion.div>

          {/* WebSocket */}
          <motion.div
            whileHover={{ y: -2 }}
            className="flex items-center gap-3 rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3"
          >
            <div
              className={`flex h-7 w-7 items-center justify-center rounded-lg ${
                wsOnline
                  ? "bg-emerald-500/10"
                  : wsConnecting
                    ? "bg-amber-500/10"
                    : "bg-red-500/10"
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  wsOnline
                    ? "bg-emerald-400"
                    : wsConnecting
                      ? "bg-amber-400"
                      : "bg-red-400"
                }`}
              />
            </div>

            <div>
              <p className="text-[9px] uppercase tracking-widest text-zinc-600">
                Alerts
              </p>

              <p
                className={`mt-0.5 text-xs font-semibold ${
                  wsOnline
                    ? "text-emerald-400"
                    : wsConnecting
                      ? "text-amber-400"
                      : "text-red-400"
                }`}
              >
                {wsOnline
                  ? "CONNECTED"
                  : wsConnecting
                    ? "CONNECTING"
                    : "OFFLINE"}
              </p>
            </div>
          </motion.div>

          {/* Clock */}
          <motion.div
            whileHover={{ y: -2 }}
            className="rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3"
          >
            <p className="text-[9px] uppercase tracking-widest text-zinc-600">
              Local Time
            </p>

            <p className="mt-0.5 font-mono text-sm font-medium tracking-wide text-zinc-300">
              {time || "--:--:--"}
            </p>
          </motion.div>

        </div>
      </div>
    </motion.header>
  );
}