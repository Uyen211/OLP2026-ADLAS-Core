// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React, { useId } from "react";
import { AlertCircle } from "lucide-react";

export interface EduInputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helperText?: string;
  error?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const EduInput = React.forwardRef<HTMLInputElement, EduInputProps>(
  (
    {
      label,
      helperText,
      error,
      leftIcon,
      rightIcon,
      className = "",
      id,
      disabled,
      ...props
    },
    ref
  ) => {
    const generatedId = useId();
    const inputId = id || generatedId;
    const errorId = `${inputId}-error`;
    const helperId = `${inputId}-helper`;

    return (
      <div className="w-full flex flex-col gap-1.5 text-left">
        {label && (
          <label
            htmlFor={inputId}
            className="text-sm font-semibold text-[#0f2236] cursor-pointer select-none"
          >
            {label}
          </label>
        )}

        <div className="relative flex items-center">
          {leftIcon && (
            <div className="absolute left-3.5 pointer-events-none text-[#4a5f75] shrink-0">
              {leftIcon}
            </div>
          )}

          <input
            ref={ref}
            id={inputId}
            disabled={disabled}
            aria-invalid={Boolean(error)}
            aria-describedby={
              error ? errorId : helperText ? helperId : undefined
            }
            className={`w-full rounded-xl border bg-white px-3.5 py-2.5 text-base text-[#0f2236] placeholder-[#94a3b8] transition-colors outline-none focus:ring-2 focus:ring-[#7fbbdd] focus:border-[#7fbbdd] disabled:opacity-60 disabled:cursor-not-allowed min-h-[44px] ${
              leftIcon ? "pl-10" : ""
            } ${rightIcon ? "pr-10" : ""} ${
              error
                ? "border-[#b91c1c] focus:ring-[#b91c1c]/30 focus:border-[#b91c1c]"
                : "border-[rgba(15,34,54,0.18)] hover:border-[rgba(15,34,54,0.3)]"
            } ${className}`}
            {...props}
          />

          {rightIcon && (
            <div className="absolute right-3.5 text-[#4a5f75] shrink-0">
              {rightIcon}
            </div>
          )}
        </div>

        {error ? (
          <p
            id={errorId}
            className="flex items-center gap-1.5 text-xs font-medium text-[#b91c1c] mt-0.5 animate-edu-fade-in"
          >
            <AlertCircle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
            <span>{error}</span>
          </p>
        ) : helperText ? (
          <p id={helperId} className="text-xs text-[#4a5f75] mt-0.5">
            {helperText}
          </p>
        ) : null}
      </div>
    );
  }
);

EduInput.displayName = "EduInput";
