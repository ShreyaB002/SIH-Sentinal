"use client";

import { motion, AnimatePresence } from "framer-motion";

const MAX_LOG_ENTRIES = 200;

function formatTime(iso) {
  try {
    const date = new Date(iso);

    const pad = (number) =>
      String(number).padStart(2, "0");

    return `${pad(date.getHours())}:${pad(
      date.getMinutes()
    )}:${pad(date.getSeconds())}`;
  } catch {
    return "--:--:--";
  }
}

function EventCard({ event }) {
  const isIntrusion =
    event?.event_type === "INTRUSION";

  const confidence =
    event?.confidence !== undefined &&
    event?.confidence !== null
      ? `${(event.confidence * 100).toFixed(0)}%`
      : "";

  const zone = event?.zone || "";

  return (
    <motion.div
      layout
      initial={{
        opacity: 0,
        x: 20,
        scale: 0.98,
      }}
      animate={{
        opacity: 1,
        x: 0,
        scale: 1,
      }}
      exit={{
        opacity: 0,
        x: 20,
        scale: 0.98,
      }}
      transition={{
        duration: 0.25,
        ease: "easeOut",
      }}
      whileHover={{
        y: -1,
      }}
      className={`rounded-xl border p-3 transition-colors ${
        isIntrusion
          ? "border-red-900/60 bg-red-950/20 hover:border-red-800"
          : "border-zinc-800 bg-zinc-950 hover:border-zinc-700"
      }`}
    >
      {/* Top row */}
      <div className="flex items-center justify-between gap-3">
        <span
          className={`text-[10px] font-semibold tracking-wider ${
            isIntrusion
              ? "text-red-400"
              : "text-zinc-400"
          }`}
        >
          {isIntrusion
            ? "! INTRUSION"
            : "DETECTED"}
        </span>

        <span className="font-mono text-[10px] text-zinc-600">
          {formatTime(event?.timestamp)}
        </span>
      </div>

      {/* Detection */}
      <div className="mt-2 text-sm font-semibold text-zinc-200">
        {event?.label || "Unknown"}

        {confidence && (
          <span className="ml-1 text-xs font-normal text-zinc-500">
            ({confidence})
          </span>
        )}
      </div>

      {/* Camera + track */}
      <div className="mt-1 text-[11px] text-zinc-500">
        {event?.camera_name || event?.camera_id}

        <span className="mx-1 text-zinc-700">
          •
        </span>

        Track #{event?.track_id || 0}
      </div>

      {/* Zone */}
      {zone && (
        <div className="mt-2 flex items-center gap-1 text-[11px] text-zinc-500">
          <span className="text-zinc-600">
            ▶
          </span>

          {zone}
        </div>
      )}
    </motion.div>
  );
}

export default function EventLog({
  events = [],
  onClear,
}) {
  const visibleEvents =
    events.slice(0, MAX_LOG_ENTRIES);

  return (
    <aside className="flex h-full min-h-[500px] flex-col border-l border-zinc-800 bg-black">

      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-4">

        <div>
          <h2 className="text-sm font-semibold text-white">
            Event Log
          </h2>

          <p className="mt-0.5 text-[10px] uppercase tracking-widest text-zinc-600">
            AI Detection Events
          </p>
        </div>

        <div className="flex items-center gap-2">

          <span className="rounded-md border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-[10px] text-zinc-500">
            {events.length}
          </span>

          {events.length > 0 && (
            <motion.button
              type="button"
              whileTap={{ scale: 0.96 }}
              onClick={onClear}
              className="rounded-md border border-zinc-800 px-2.5 py-1 text-[10px] text-zinc-500 transition hover:border-zinc-600 hover:bg-zinc-900 hover:text-zinc-200"
            >
              CLEAR
            </motion.button>
          )}
        </div>
      </div>

      {/* Events */}
      <div className="flex-1 overflow-y-auto p-3">

        {visibleEvents.length === 0 ? (
          <div className="flex min-h-[350px] items-center justify-center">
            <div className="text-center">

              <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full border border-zinc-800 bg-zinc-950">
                <span className="text-zinc-700">
                  ◌
                </span>
              </div>

              <p className="text-xs font-medium text-zinc-500">
                No events yet
              </p>

              <p className="mt-1 text-[10px] text-zinc-700">
                AI detection events will appear here
              </p>

            </div>
          </div>
        ) : (
          <motion.div
            layout
            className="space-y-2"
          >
            <AnimatePresence initial={false}>
              {visibleEvents.map((event, index) => (
                <EventCard
                  key={
                    event?.id ??
                    `${event?.timestamp}-${index}`
                  }
                  event={event}
                />
              ))}
            </AnimatePresence>
          </motion.div>
        )}

      </div>

      {/* Footer */}
      <div className="border-t border-zinc-800 px-4 py-3">
        <div className="flex items-center justify-between">

          <span className="text-[10px] uppercase tracking-widest text-zinc-700">
            Events
          </span>

          <span className="font-mono text-[10px] text-zinc-500">
            {events.length}
          </span>

        </div>
      </div>

    </aside>
  );
}