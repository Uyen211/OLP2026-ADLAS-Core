/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React from "react";
import { clsx } from "clsx";

export type MmButtonVariant = "primary" | "brand" | "secondary" | "ghost" | "danger";
export type MmButtonSize = "sm" | "md" | "lg";

export interface MmButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: MmButtonVariant;
  size?: MmButtonSize;
  loading?: boolean;
  fullWidth?: boolean;
}

const VARIANT_CLASSES: Record<MmButtonVariant, string> = {
  primary:
    "bg-mm-dark text-white hover:bg-mm-heading active:bg-black disabled:bg-mm-btn-secondary disabled:text-mm-text-muted",
  brand:
    "bg-mm-blue-hover text-white hover:bg-mm-blue-active active:bg-mm-blue-deep disabled:bg-mm-btn-secondary disabled:text-mm-text-muted",
  secondary:
    "bg-mm-btn-secondary text-[#333333] hover:bg-mm-border active:bg-mm-border/80 disabled:opacity-60",
  ghost:
    "bg-transparent text-mm-text-secondary hover:bg-black/5 active:bg-black/10 disabled:opacity-50",
  danger:
    "bg-mm-danger text-white hover:bg-[#b42318] active:bg-[#912018] disabled:bg-mm-btn-secondary disabled:text-mm-text-muted",
};

const SIZE_CLASSES: Record<MmButtonSize, string> = {
  sm: "px-3.5 py-2 text-xs",
  md: "px-5 py-[11px] text-sm",
  lg: "px-6 py-3 text-base",
};

export const MmButton: React.FC<MmButtonProps> = ({
  variant = "primary",
  size = "md",
  loading = false,
  fullWidth = false,
  disabled,
  className,
  children,
  type = "button",
  ...rest
}) => {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-mm-btn font-mm-ui font-semibold transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-mm-blue-hover/30 disabled:cursor-not-allowed",
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        fullWidth && "w-full",
        className
      )}
      {...rest}
    >
      {loading && (
        <span
          aria-hidden="true"
          className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
        />
      )}
      {children}
    </button>
  );
};
