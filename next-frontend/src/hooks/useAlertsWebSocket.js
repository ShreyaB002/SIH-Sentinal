"use client";

import { useEffect, useRef, useState } from "react";

const MAX_BACKOFF_MS = 30000;
const MAX_EVENTS = 200;

export default function useAlertsWebSocket() {
  const [events, setEvents] = useState([]);
  const [wsStatus, setWsStatus] = useState("CONNECTING");

  const socketRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const backoffRef = useRef(1000);

  useEffect(() => {
    let stopped = false;

    function connect() {
      if (stopped) return;

      setWsStatus("CONNECTING");

      const apiUrl =
        process.env.NEXT_PUBLIC_API_URL ||
        "http://127.0.0.1:8000";

      // Convert http:// → ws://
      // Convert https:// → wss://
      const wsProtocol = apiUrl.startsWith("https")
        ? "wss"
        : "ws";

      const wsHost = apiUrl.replace(
        /^https?:\/\//,
        ""
      );

      const wsUrl =
        `${wsProtocol}://${wsHost}/ws/alerts`;

      console.log(
        "[IBVAP] Connecting WebSocket:",
        wsUrl
      );

      const socket = new WebSocket(wsUrl);

      socketRef.current = socket;

      // ------------------------------------------------
      // Connected
      // ------------------------------------------------

      socket.addEventListener("open", () => {
        if (stopped) return;

        console.log(
          "[IBVAP] WebSocket connected"
        );

        setWsStatus("ONLINE");

        // Reset reconnect delay
        backoffRef.current = 1000;
      });

      // ------------------------------------------------
      // New message from FastAPI
      // ------------------------------------------------

      socket.addEventListener(
        "message",
        (message) => {
          if (stopped) return;

          let event;

          try {
            event = JSON.parse(message.data);
          } catch (error) {
            console.warn(
              "[IBVAP] Invalid WebSocket message:",
              message.data
            );

            return;
          }

          // Ignore heartbeat/info messages
          if (
            !event ||
            event.event_type === "PING" ||
            event.event_type === "INFO"
          ) {
            return;
          }

          console.log(
            "[IBVAP] AI Event:",
            event
          );

          // Add newest event to beginning
          setEvents((previousEvents) => {
            const updatedEvents = [
              event,
              ...previousEvents,
            ];

            return updatedEvents.slice(
              0,
              MAX_EVENTS
            );
          });
        }
      );

      // ------------------------------------------------
      // Connection closed
      // ------------------------------------------------

      socket.addEventListener(
        "close",
        (event) => {
          if (stopped) return;

          console.warn(
            "[IBVAP] WebSocket closed:",
            event.code,
            event.reason
          );

          setWsStatus("OFFLINE");

          scheduleReconnect();
        }
      );

      // ------------------------------------------------
      // Error
      // ------------------------------------------------

      socket.addEventListener(
        "error",
        (error) => {
          if (stopped) return;

          console.error(
            "[IBVAP] WebSocket error:",
            error
          );

          setWsStatus("OFFLINE");
        }
      );
    }

    // ------------------------------------------------
    // Reconnect with exponential backoff
    // ------------------------------------------------

    function scheduleReconnect() {
      if (stopped) return;

      const delay = backoffRef.current;

      console.log(
        `[IBVAP] Reconnecting in ${delay}ms...`
      );

      reconnectTimerRef.current =
        setTimeout(() => {
          backoffRef.current = Math.min(
            backoffRef.current * 2,
            MAX_BACKOFF_MS
          );

          connect();
        }, delay);
    }

    // Start connection
    connect();

    // ------------------------------------------------
    // Cleanup
    // ------------------------------------------------

    return () => {
      stopped = true;

      if (reconnectTimerRef.current) {
        clearTimeout(
          reconnectTimerRef.current
        );
      }

      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, []);

  // Clear events
  function clearEvents() {
    setEvents([]);
  }

  return {
    events,
    wsStatus,
    clearEvents,
  };
}