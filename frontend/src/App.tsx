/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useState } from "react";
import {
  Activity,
  Boxes,
  Database,
  Globe,
  Radio,
  Server,
  Shield,
  UserCheck,
} from "lucide-react";
import { UserManagement } from "./apps/admin-console/pages/UserManagement";

export const App: React.FC = () => {
  const [activeMenu, setActiveMenu] = useState("identity");

  const navigationItems = [
    {
      id: "identity",
      label: "Identity & RBAC",
      badge: "T1-C-M0-01",
      icon: Shield,
    },
    {
      id: "gateway",
      label: "Kong API Gateway",
      badge: "T1-C-M0-02",
      icon: Globe,
    },
    {
      id: "storage",
      label: "Database & Storage",
      badge: "T1-C-M0-03",
      icon: Database,
    },
    {
      id: "eventbus",
      label: "Event Bus & Workers",
      badge: "T1-C-M0-04",
      icon: Radio,
    },
    {
      id: "health",
      label: "Health & Audit Trail",
      badge: "T1-C-M0-05",
      icon: Activity,
    },
  ];

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      {/* Sidebar Navigation */}
      <aside className="w-72 bg-white border-r border-slate-200 flex flex-col justify-between flex-shrink-0">
        <div>
          {/* Logo Brand Header */}
          <div className="p-6 border-b border-slate-100 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-brand">
              <Boxes className="w-6 h-6" />
            </div>
            <div>
              <h2 className="font-bold text-slate-900 tracking-tight leading-none">
                ADLAS Core
              </h2>
              <span className="text-xs text-slate-400 font-mono">
                Tier-1 Admin Console
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1">
            <div className="px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Platform Modules
            </div>

            {navigationItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeMenu === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setActiveMenu(item.id)}
                  className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    isActive
                      ? "bg-blue-50 text-blue-700 shadow-sm"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`w-4 h-4 ${isActive ? "text-blue-600" : "text-slate-400"}`} />
                    <span>{item.label}</span>
                  </div>
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded-md ${
                      isActive ? "bg-blue-100/80 text-blue-800" : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {item.badge}
                  </span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Sidebar Footer: System Status */}
        <div className="p-4 border-t border-slate-100 bg-slate-50/50">
          <div className="flex items-center gap-3 p-3 bg-white rounded-xl border border-slate-200">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-slate-800 truncate">Supabase & Kong Online</p>
              <p className="text-[10px] font-mono text-slate-400">PostgreSQL 16 - ACID Mode</p>
            </div>
            <Server className="w-4 h-4 text-slate-400" />
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Navbar */}
        <header className="h-16 bg-white border-b border-slate-200 px-8 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
            <span>PLATFORM</span>
            <span>/</span>
            <span className="text-slate-800 font-semibold uppercase">{activeMenu}</span>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2.5 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-pill text-xs">
              <UserCheck className="w-4 h-4 text-emerald-600" />
              <span className="text-slate-600">Logged in as:</span>
              <span className="font-semibold text-slate-900">admin@adlas.edu.vn</span>
              <span className="px-1.5 py-0.2 text-[10px] bg-blue-100 text-blue-700 font-mono font-bold rounded">
                SYSADMIN
              </span>
            </div>
          </div>
        </header>

        {/* Main Scrollable View */}
        <main className="flex-1 overflow-y-auto p-8">
          {activeMenu === "identity" ? (
            <UserManagement />
          ) : (
            <div className="p-12 text-center bg-white rounded-2xl border border-slate-200 shadow-card">
              <Server className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <h3 className="text-base font-semibold text-slate-700">Module View In Progress</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                This administrative sub-view will be activated in the respective development phase according to the Tier-1 execution schedule.
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};
