"use client";

import { useState } from "react";
import { 
  ShieldAlert, 
  Video, 
  Activity, 
  Settings, 
  Users, 
  Car, 
  Map, 
  BarChart3,
  ChevronLeft,
  ChevronRight
} from "lucide-react";
import { motion } from "framer-motion";

const navItems = [
  { name: "Operations", icon: Activity, href: "#", active: true },
  { name: "Live Monitoring", icon: Video, href: "#" },
  { name: "Incidents", icon: ShieldAlert, href: "#" },
  { name: "Watchlist", icon: Users, href: "#" },
  { name: "ANPR Log", icon: Car, href: "#" },
  { name: "Zone Editor", icon: Map, href: "#" },
  { name: "Reports", icon: BarChart3, href: "#" },
  { name: "Settings", icon: Settings, href: "#" },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 80 : 260 }}
      className="flex h-screen flex-col border-r border-border-dark bg-nav-bg text-text-inverse transition-all duration-300 z-50 sticky top-0"
    >
      {/* Header */}
      <div className="flex h-16 items-center justify-between border-b border-border-dark px-4">
        {!collapsed && (
          <div className="flex items-center gap-2 overflow-hidden whitespace-nowrap">
            <div className="flex h-8 w-8 items-center justify-center rounded bg-nav-hover">
              <ShieldAlert size={18} className="text-white" />
            </div>
            <span className="font-semibold tracking-wide text-text-inverse">IBVAP</span>
          </div>
        )}
        
        {collapsed && (
          <div className="mx-auto flex h-8 w-8 items-center justify-center rounded bg-nav-hover">
            <ShieldAlert size={18} className="text-white" />
          </div>
        )}

        <button
          onClick={() => setCollapsed(!collapsed)}
          className={`flex h-6 w-6 items-center justify-center rounded-md hover:bg-nav-hover text-text-inverse-muted hover:text-white transition-colors ${collapsed ? 'absolute -right-3 top-5 bg-nav-hover border border-border-dark rounded-full shadow-md z-10' : ''}`}
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto overflow-x-hidden p-3 space-y-1 dark-scroll">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = item.active;

          return (
            <a
              key={item.name}
              href={item.href}
              title={collapsed ? item.name : undefined}
              className={`group flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors ${
                isActive 
                  ? "bg-nav-hover text-white" 
                  : "text-text-inverse-muted hover:bg-nav-hover hover:text-white"
              }`}
            >
              <Icon size={20} className={isActive ? "text-white" : "text-text-inverse-muted group-hover:text-white"} />
              
              {!collapsed && (
                <span className={`text-sm font-medium ${isActive ? "text-white" : ""}`}>
                  {item.name}
                </span>
              )}

              {!collapsed && isActive && (
                <div className="ml-auto h-1.5 w-1.5 rounded-full bg-white" />
              )}
            </a>
          );
        })}
      </nav>

      {/* Footer / Profile */}
      <div className="border-t border-border-dark p-4">
        <div className={`flex items-center ${collapsed ? 'justify-center' : 'gap-3'} overflow-hidden`}>
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-nav-hover border border-border-dark">
            <span className="text-xs font-semibold text-text-inverse">OP</span>
          </div>
          
          {!collapsed && (
            <div className="flex flex-col overflow-hidden">
              <span className="truncate text-sm font-medium text-text-inverse">Operator 01</span>
              <div className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-green-healthy" />
                <span className="text-[10px] text-text-inverse-muted">Secure Session</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.aside>
  );
}
