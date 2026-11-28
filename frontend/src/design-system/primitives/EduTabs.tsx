// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React from "react";

export interface EduTabItem {
  id: string;
  label: string;
  icon?: React.ReactNode;
  badge?: number | string;
}

export interface EduTabsProps {
  tabs: EduTabItem[];
  activeTab: string;
  onChange: (tabId: string) => void;
  className?: string;
}

export const EduTabs: React.FC<EduTabsProps> = ({
  tabs,
  activeTab,
  onChange,
  className = "",
}) => {
  return (
    <div
      role="tablist"
      className={`inline-flex items-center gap-1.5 p-1 rounded-xl bg-[#f5fbfd] border border-[rgba(127,187,221,0.4)] ${className}`}
    >
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={`flex items-center gap-2 px-3.5 py-1.5 text-sm font-semibold rounded-lg transition-all duration-100 select-none min-h-[36px] ${
              isActive
                ? "bg-[#0f2236] text-white shadow-sm"
                : "text-[#4a5f75] hover:text-[#0f2236] hover:bg-white/60"
            }`}
          >
            {tab.icon && <span className="shrink-0">{tab.icon}</span>}
            <span>{tab.label}</span>
            {tab.badge !== undefined && (
              <span
                className={`ml-1 px-1.5 py-0.5 text-xs rounded-full font-mono ${
                  isActive
                    ? "bg-[#f58b05] text-[#1a1400]"
                    : "bg-[#eaf6fa] text-[#0f2236]"
                }`}
              >
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
};
