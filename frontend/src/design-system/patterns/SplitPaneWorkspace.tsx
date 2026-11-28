// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React from "react";

export interface SplitPaneWorkspaceProps {
  leftPane: React.ReactNode;
  rightPane: React.ReactNode;
  leftTitle?: string;
  rightTitle?: string;
  className?: string;
}

export const SplitPaneWorkspace: React.FC<SplitPaneWorkspaceProps> = ({
  leftPane,
  rightPane,
  leftTitle,
  rightTitle,
  className = "",
}) => {
  return (
    <div
      className={`w-full grid grid-cols-1 lg:grid-cols-12 gap-6 items-start ${className}`}
    >
      <div className="lg:col-span-5 flex flex-col gap-3">
        {leftTitle && (
          <h2 className="text-sm font-bold text-[#4a5f75] uppercase tracking-wider px-1">
            {leftTitle}
          </h2>
        )}
        <div className="w-full">{leftPane}</div>
      </div>

      <div className="lg:col-span-7 flex flex-col gap-3">
        {rightTitle && (
          <h2 className="text-sm font-bold text-[#4a5f75] uppercase tracking-wider px-1">
            {rightTitle}
          </h2>
        )}
        <div className="w-full">{rightPane}</div>
      </div>
    </div>
  );
};
