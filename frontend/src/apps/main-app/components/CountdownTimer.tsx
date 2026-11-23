/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useState } from "react";

export interface CountdownTimerProps {
  initialSeconds: number;
  onExpire?: () => void;
  className?: string;
}

export const CountdownTimer: React.FC<CountdownTimerProps> = ({
  initialSeconds,
  onExpire,
  className,
}) => {
  const [remaining, setRemaining] = useState<number>(Math.max(0, Math.floor(initialSeconds)));

  useEffect(() => {
    setRemaining(Math.max(0, Math.floor(initialSeconds)));
  }, [initialSeconds]);

  useEffect(() => {
    if (remaining <= 0) {
      onExpire?.();
      return;
    }
    const timer = window.setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 1) {
          window.clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [remaining, onExpire]);

  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;
  const formatted = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;

  return (
    <span className={className ?? "font-mm-mono font-medium tabular-nums"}>
      {formatted}
    </span>
  );
};
