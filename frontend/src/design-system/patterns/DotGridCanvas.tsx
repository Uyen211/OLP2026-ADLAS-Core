// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React from "react";

export interface DotGridCanvasProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export const DotGridCanvas: React.FC<DotGridCanvasProps> = ({
  children,
  className = "",
  ...props
}) => {
  return (
    <div
      className={`w-full min-h-[400px] edu-dot-grid rounded-2xl border border-[rgba(127,187,221,0.55)] p-4 sm:p-6 shadow-sm relative ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};
