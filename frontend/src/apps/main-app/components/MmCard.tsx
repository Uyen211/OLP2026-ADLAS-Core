/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React from "react";
import { clsx } from "clsx";

export interface MmCardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "standard" | "featured" | "ambient";
  radius?: "card" | "card-lg";
  interactive?: boolean;
  padding?: "none" | "sm" | "md" | "lg";
}

const SHADOW_CLASSES = {
  standard: "shadow-mm-standard",
  featured: "shadow-mm-brand",
  ambient: "shadow-mm-ambient",
};

const PADDING_CLASSES = {
  none: "",
  sm: "p-4",
  md: "p-5",
  lg: "p-6",
};

export const MmCard: React.FC<MmCardProps> = ({
  variant = "standard",
  radius = "card",
  interactive = false,
  padding = "lg",
  className,
  children,
  ...rest
}) => {
  return (
    <div
      className={clsx(
        "bg-mm-bg border border-mm-border transition-shadow duration-200",
        radius === "card-lg" ? "rounded-mm-card-lg" : "rounded-mm-card",
        SHADOW_CLASSES[variant],
        PADDING_CLASSES[padding],
        interactive && "hover:shadow-mm-elevated cursor-pointer",
        className
      )}
      {...rest}
    >
      {children}
    </div>
  );
};
