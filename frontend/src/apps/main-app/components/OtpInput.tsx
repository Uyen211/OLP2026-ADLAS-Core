/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useRef } from "react";
import { clsx } from "clsx";

export interface OtpInputProps {
  value: string;
  onChange: (value: string) => void;
  length?: number;
  hasError?: boolean;
  disabled?: boolean;
}

export const OtpInput: React.FC<OtpInputProps> = ({
  value,
  onChange,
  length = 6,
  hasError = false,
  disabled = false,
}) => {
  const inputRefs = useRef<Array<HTMLInputElement | null>>([]);
  const digits = Array.from({ length }, (_, idx) => value[idx] ?? "");

  const focusAt = (index: number) => {
    const clamped = Math.max(0, Math.min(length - 1, index));
    inputRefs.current[clamped]?.focus();
  };

  const handleChange = (index: number, raw: string) => {
    const cleaned = raw.replace(/\D/g, "");
    if (!cleaned) {
      const next = [...digits];
      next[index] = "";
      onChange(next.join(""));
      return;
    }

    if (cleaned.length > 1) {
      const pasted = cleaned.slice(0, length);
      onChange(pasted);
      focusAt(Math.min(pasted.length, length - 1));
      return;
    }

    const next = [...digits];
    next[index] = cleaned;
    onChange(next.join(""));
    if (index < length - 1) {
      focusAt(index + 1);
    }
  };

  const handleKeyDown = (index: number, event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Backspace") {
      if (digits[index]) {
        const next = [...digits];
        next[index] = "";
        onChange(next.join(""));
      } else if (index > 0) {
        const next = [...digits];
        next[index - 1] = "";
        onChange(next.join(""));
        focusAt(index - 1);
      }
      event.preventDefault();
    } else if (event.key === "ArrowLeft" && index > 0) {
      focusAt(index - 1);
    } else if (event.key === "ArrowRight" && index < length - 1) {
      focusAt(index + 1);
    }
  };

  const handlePaste = (event: React.ClipboardEvent<HTMLInputElement>) => {
    const text = event.clipboardData.getData("text").replace(/\D/g, "").slice(0, length);
    if (text) {
      event.preventDefault();
      onChange(text);
      focusAt(Math.min(text.length, length - 1));
    }
  };

  return (
    <div className="flex items-center justify-center gap-2.5">
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={(el) => {
            inputRefs.current[index] = el;
          }}
          type="text"
          inputMode="numeric"
          autoComplete={index === 0 ? "one-time-code" : "off"}
          maxLength={1}
          disabled={disabled}
          value={digit}
          aria-label={`Chữ số OTP thứ ${index + 1}`}
          onChange={(e) => handleChange(index, e.target.value)}
          onKeyDown={(e) => handleKeyDown(index, e)}
          onPaste={handlePaste}
          className={clsx(
            "h-14 w-12 rounded-mm-btn border bg-mm-bg text-center font-mm-mono text-2xl font-medium text-mm-heading transition-colors focus:outline-none focus:ring-2 disabled:bg-mm-btn-secondary disabled:text-mm-text-muted",
            hasError
              ? "border-mm-danger focus:border-mm-danger focus:ring-mm-danger/20"
              : "border-mm-border focus:border-mm-blue-hover focus:ring-mm-blue-hover/20"
          )}
        />
      ))}
    </div>
  );
};
