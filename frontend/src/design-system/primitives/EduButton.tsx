// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React from "react";
import { Loader2 } from "lucide-react";

export type EduButtonVariant =
  | "primary"
  | "secondary"
  | "amber"
  | "sky"
  | "ghost"
  | "danger";

export type EduButtonSize = "sm" | "md" | "lg";

export interface EduButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: EduButtonVariant;
  size?: EduButtonSize;
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const variantStyles: Record<EduButtonVariant, string> = {
  primary:
    "bg-[#0f2236] text-white hover:bg-[#1a334d] active:bg-[#091522] border border-transparent shadow-sm",
  secondary:
    "bg-[#f5fbfd] text-[#0f2236] hover:bg-[#eaf6fa] active:bg-[#d8eef5] border border-[rgba(15,34,54,0.15)]",
  amber:
    "bg-[#f58b05] text-[#1a1400] font-semibold hover:bg-[#e07e04] active:bg-[#cc7203] border border-transparent shadow-sm",
  sky:
    "bg-[#c4e9f2] text-[#0f2236] font-medium hover:bg-[#b0dfec] active:bg-[#9bd4e5] border border-[rgba(127,187,221,0.55)]",
  ghost:
    "bg-transparent text-[#0f2236] hover:bg-[#f5fbfd] active:bg-[#eaf6fa] border border-transparent",
  danger:
    "bg-[#b91c1c] text-white hover:bg-[#991b1b] active:bg-[#7f1d1d] border border-transparent shadow-sm",
};

const sizeStyles: Record<EduButtonSize, string> = {
  sm: "px-3 py-1.5 text-xs rounded-md min-h-[32px] gap-1.5",
  md: "px-4 py-2 text-sm rounded-lg min-h-[40px] md:min-h-[40px] min-h-[44px] gap-2",
  lg: "px-5 py-2.5 text-base rounded-xl min-h-[48px] gap-2.5",
};

export const EduButton: React.FC<EduButtonProps> = ({
  variant = "primary",
  size = "md",
  isLoading = false,
  leftIcon,
  rightIcon,
  children,
  className = "",
  disabled,
  ...props
}) => {
  const isDisabled = disabled || isLoading;

  return (
    <button
      type={props.type || "button"}
      disabled={isDisabled}
      aria-busy={isLoading}
      className={`inline-flex items-center justify-center font-medium transition-colors duration-100 touch-manipulation select-none outline-none focus-visible:ring-2 focus-visible:ring-[#7fbbdd] focus-visible:ring-offset-2 ${
        variantStyles[variant]
      } ${sizeStyles[size]} ${
        isDisabled ? "opacity-60 cursor-not-allowed pointer-events-none" : ""
      } ${className}`}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 animate-spin shrink-0" aria-hidden="true" />
      ) : (
        leftIcon && <span className="shrink-0">{leftIcon}</span>
      )}
      <span>{children}</span>
      {!isLoading && rightIcon && <span className="shrink-0">{rightIcon}</span>}
    </button>
  );
};
