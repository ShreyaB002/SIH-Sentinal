"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

export default function CameraCard({ camera, apiUrl }) {
  const [isFullscreen, setIsFullscreen] = useState(false);

  const online = camera.status === "ONLINE";
  const connecting = camera.status === "CONNECTING";

  const statusColor = online
    ? "bg-emerald-500"
    : connecting
      ? "bg-amber-400"
      : "bg-red-500";

  const statusTextColor = online
    ? "text-emerald-400"
    : connecting
      ? "text-amber-400"
      : "text-red-400";

  // Close fullscreen with Escape
  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === "Escape") {
        setIsFullscreen(false);
      }
    }

    if (isFullscreen) {
      document.addEventListener(
        "keydown",
        handleKeyDown
      );

      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener(
        "keydown",
        handleKeyDown
      );

      document.body.style.overflow = "";
    };
  }, [isFullscreen]);

  return (
    <>
      {/* =====================================================
          CAMERA CARD
      ====================================================== */}

      <motion.button
        type="button"
        onClick={() => setIsFullscreen(true)}
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{
          duration: 0.4,
          ease: "easeOut",
        }}
        whileHover={{ y: -3 }}
        whileTap={{ scale: 0.995 }}
        className="
          group
          relative
          w-full
          overflow-hidden
          rounded-2xl
          border
          border-zinc-800/80
          bg-zinc-950
          text-left
          shadow-lg
          shadow-black/20
          transition
          duration-300
          hover:border-zinc-700
          hover:shadow-2xl
          hover:shadow-black/40
          focus:outline-none
          focus:ring-2
          focus:ring-zinc-600
        "
      >
        {/* =================================================
            VIDEO
        ================================================== */}

        <div className="relative aspect-video overflow-hidden bg-zinc-950">

          {online || connecting ? (
            <motion.img
              src={`${apiUrl}/api/stream/${camera.id}`}
              alt={`${camera.name} live feed`}
              className="
                h-full
                w-full
                object-cover
                transition-transform
                duration-700
                ease-out
                group-hover:scale-[1.025]
              "
            />
          ) : (
            /* Offline state */
            <div className="flex h-full items-center justify-center bg-zinc-950">

              <div className="text-center">

                <motion.div
                  animate={{
                    opacity: [0.35, 0.7, 0.35],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: "easeInOut",
                  }}
                  className="
                    mx-auto
                    mb-3
                    flex
                    h-12
                    w-12
                    items-center
                    justify-center
                    rounded-full
                    border
                    border-zinc-800
                    bg-zinc-900
                  "
                >
                  <span className="text-lg text-zinc-600">
                    ◌
                  </span>
                </motion.div>

                <p className="text-xs font-semibold tracking-wider text-zinc-500">
                  CAMERA OFFLINE
                </p>

                <p className="mt-1 text-[10px] text-zinc-700">
                  No video signal
                </p>

              </div>
            </div>
          )}

          {/* =================================================
              TOP GRADIENT
          ================================================== */}

          <div className="
            pointer-events-none
            absolute
            inset-x-0
            top-0
            h-24
            bg-gradient-to-b
            from-black/70
            to-transparent
          " />

          {/* =================================================
              CAMERA NAME
          ================================================== */}

          <div className="
            absolute
            left-3
            top-3
            flex
            items-center
            gap-2
            rounded-lg
            border
            border-white/10
            bg-black/60
            px-3
            py-2
            backdrop-blur-md
          ">

            <span className="text-xs font-semibold text-white">
              {camera.name}
            </span>

          </div>

          {/* =================================================
              LIVE BADGE
          ================================================== */}

          {online && (
            <div className="
              absolute
              right-3
              top-3
              flex
              items-center
              gap-1.5
              rounded-lg
              border
              border-emerald-500/20
              bg-black/60
              px-2.5
              py-1.5
              backdrop-blur-md
            ">

              <motion.span
                animate={{
                  opacity: [1, 0.35, 1],
                }}
                transition={{
                  duration: 1.5,
                  repeat: Infinity,
                }}
                className="h-1.5 w-1.5 rounded-full bg-emerald-400"
              />

              <span className="text-[9px] font-semibold tracking-widest text-emerald-400">
                LIVE
              </span>

            </div>
          )}

          {connecting && (
            <div className="
              absolute
              right-3
              top-3
              flex
              items-center
              gap-1.5
              rounded-lg
              border
              border-amber-500/20
              bg-black/60
              px-2.5
              py-1.5
              backdrop-blur-md
            ">

              <motion.span
                animate={{
                  opacity: [1, 0.3, 1],
                }}
                transition={{
                  duration: 1,
                  repeat: Infinity,
                }}
                className="h-1.5 w-1.5 rounded-full bg-amber-400"
              />

              <span className="text-[9px] font-semibold tracking-widest text-amber-400">
                CONNECTING
              </span>

            </div>
          )}

          {/* =================================================
              HOVER EXPAND
          ================================================== */}

          <motion.div
            initial={{ opacity: 0 }}
            whileHover={{ opacity: 1 }}
            className="
              pointer-events-none
              absolute
              inset-0
              flex
              items-center
              justify-center
              bg-black/10
            "
          >
            <div className="
              flex
              h-10
              w-10
              items-center
              justify-center
              rounded-xl
              border
              border-white/15
              bg-black/60
              text-lg
              text-white
              shadow-xl
              backdrop-blur-md
            ">
              ⛶
            </div>
          </motion.div>

        </div>

        {/* =================================================
            STATUS BAR
        ================================================== */}

        <div className="
          flex
          items-center
          gap-3
          border-t
          border-zinc-800/80
          bg-zinc-950
          px-4
          py-3
        ">

          {/* Status indicator */}

          <div className="relative flex h-2 w-2 items-center justify-center">

            {online && (
              <motion.span
                animate={{
                  scale: [1, 1.8, 1],
                  opacity: [0.5, 0, 0.5],
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                }}
                className={`absolute h-2 w-2 rounded-full ${statusColor}`}
              />
            )}

            <span
              className={`relative h-1.5 w-1.5 rounded-full ${statusColor}`}
            />

          </div>

          {/* Status */}

          <span
            className={`text-[10px] font-semibold tracking-wider ${statusTextColor}`}
          >
            {camera.status}
          </span>

          {/* Divider */}

          <span className="h-3 w-px bg-zinc-800" />

          {/* Camera ID */}

          <span className="font-mono text-[10px] text-zinc-600">
            {camera.id}
          </span>

          {/* Expand text */}

          <span className="
            ml-auto
            text-[9px]
            font-medium
            uppercase
            tracking-wider
            text-zinc-700
            transition
            group-hover:text-zinc-400
          ">
            View
          </span>

        </div>

      </motion.button>

      {/* =====================================================
          FULLSCREEN MODAL
      ====================================================== */}

      <AnimatePresence>
        {isFullscreen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="
              fixed
              inset-0
              z-[100]
              flex
              items-center
              justify-center
              bg-black/90
              p-3
              backdrop-blur-xl
              sm:p-6
            "
            onClick={() => setIsFullscreen(false)}
          >

            {/* Fullscreen container */}

            <motion.div
              initial={{
                opacity: 0,
                scale: 0.96,
                y: 10,
              }}
              animate={{
                opacity: 1,
                scale: 1,
                y: 0,
              }}
              exit={{
                opacity: 0,
                scale: 0.96,
                y: 10,
              }}
              transition={{
                duration: 0.25,
                ease: "easeOut",
              }}
              onClick={(event) =>
                event.stopPropagation()
              }
              className="
                relative
                flex
                h-full
                w-full
                flex-col
                overflow-hidden
                rounded-2xl
                border
                border-zinc-800
                bg-zinc-950
                shadow-2xl
              "
            >

              {/* ==========================================
                  FULLSCREEN HEADER
              =========================================== */}

              <div className="
                flex
                items-center
                justify-between
                border-b
                border-zinc-800
                bg-zinc-950/95
                px-4
                py-3
                sm:px-5
                sm:py-4
              ">

                <div className="flex items-center gap-3">

                  <div className="relative flex h-2 w-2">

                    {online && (
                      <motion.span
                        animate={{
                          scale: [1, 2, 1],
                          opacity: [0.6, 0, 0.6],
                        }}
                        transition={{
                          duration: 2,
                          repeat: Infinity,
                        }}
                        className={`absolute h-2 w-2 rounded-full ${statusColor}`}
                      />
                    )}

                    <span
                      className={`relative h-2 w-2 rounded-full ${statusColor}`}
                    />

                  </div>

                  <div>

                    <h2 className="
                      text-sm
                      font-semibold
                      text-white
                    ">
                      {camera.name}
                    </h2>

                    <div className="
                      mt-0.5
                      flex
                      items-center
                      gap-2
                    ">

                      <span className="font-mono text-[10px] text-zinc-600">
                        {camera.id}
                      </span>

                      <span className="text-zinc-800">
                        /
                      </span>

                      <span
                        className={`text-[10px] font-medium ${statusTextColor}`}
                      >
                        {camera.status}
                      </span>

                    </div>

                  </div>

                </div>

                {/* Close */}

                <button
                  type="button"
                  onClick={() =>
                    setIsFullscreen(false)
                  }
                  className="
                    flex
                    h-9
                    w-9
                    items-center
                    justify-center
                    rounded-xl
                    border
                    border-zinc-800
                    bg-zinc-900/50
                    text-lg
                    text-zinc-500
                    transition
                    hover:border-zinc-600
                    hover:bg-zinc-900
                    hover:text-white
                    focus:outline-none
                    focus:ring-2
                    focus:ring-zinc-700
                  "
                  aria-label="Close camera"
                >
                  ×
                </button>

              </div>

              {/* ==========================================
                  FULLSCREEN VIDEO
              =========================================== */}

              <div className="
                relative
                flex
                min-h-0
                flex-1
                items-center
                justify-center
                overflow-hidden
                bg-black
              ">

                {online || connecting ? (
                  <img
                    src={`${apiUrl}/api/stream/${camera.id}`}
                    alt={`${camera.name} live feed`}
                    className="
                      max-h-full
                      max-w-full
                      object-contain
                    "
                  />
                ) : (
                  <div className="text-center">

                    <div className="
                      mx-auto
                      mb-4
                      flex
                      h-14
                      w-14
                      items-center
                      justify-center
                      rounded-full
                      border
                      border-zinc-800
                      bg-zinc-950
                    ">
                      <span className="text-zinc-600">
                        ◌
                      </span>
                    </div>

                    <p className="
                      text-sm
                      font-semibold
                      tracking-wide
                      text-zinc-500
                    ">
                      CAMERA OFFLINE
                    </p>

                    <p className="
                      mt-1
                      font-mono
                      text-[10px]
                      text-zinc-700
                    ">
                      {camera.id}
                    </p>

                  </div>
                )}

                {/* Live indicator inside video */}

                {online && (
                  <div className="
                    absolute
                    bottom-4
                    left-4
                    flex
                    items-center
                    gap-2
                    rounded-lg
                    border
                    border-emerald-500/20
                    bg-black/60
                    px-3
                    py-2
                    backdrop-blur-md
                  ">

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

                    <span className="
                      text-[9px]
                      font-semibold
                      tracking-widest
                      text-emerald-400
                    ">
                      LIVE FEED
                    </span>

                  </div>
                )}

              </div>

            </motion.div>

          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}