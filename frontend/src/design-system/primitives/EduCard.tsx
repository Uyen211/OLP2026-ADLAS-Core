// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React from "react";

export type EduCardVariant =
  | "surface"
  | "tint"
  | "subtle"
  | "interactive"
  | "dot-grid";

export interface EduCardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: EduCardVariant;
  padding?: "none" | "sm" | "md" | "lg";
}

const variantStyles: Record<EduCardVariant, string> = {
  surface: "bg-white border border-[rgba(15,34,54,0.12)] shadow-sm",
  tint: "bg-[#f5fbfd] border border-[rgba(127,187,221,0.55)]",
  subtle: "bg-[#eaf6fa] border border-[rgba(127,187,221,0.35)]",
  interactive:
    "bg-white border border-[rgba(15,34,54,0.12)] hover:border-[#7fbbdd] hover:shadow-md transition-all duration-150 cursor-pointer",
  "dot-grid": "edu-dot-grid border border-[rgba(127,187,221,0.55)]",
};

const paddingStyles = {
  none: "p-0",
  sm: "p-3 sm:p-4",
  md: "p-4 sm:p-6",
  lg: "p-6 sm:p-8",
};

export const EduCard: React.FC<EduCardProps> = ({
  variant = "surface",
  padding = "md",
  className = "",
  children,
  ...props
}) => {
  return (
    <div
      className={`rounded-2xl ${variantStyles[variant]} ${paddingStyles[padding]} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};
