/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React from "react";
import { clsx } from "clsx";

export interface PillFilterOption<T extends string = string> {
  value: T;
  label: string;
  count?: number;
}

export interface PillFilterProps<T extends string = string> {
  options: PillFilterOption<T>[];
  value: T;
  onChange: (value: T) => void;
  className?: string;
}

export function PillFilter<T extends string = string>({
  options,
  value,
  onChange,
  className,
}: PillFilterProps<T>): React.ReactElement {
  return (
    <div className={clsx("flex flex-wrap items-center gap-2", className)}>
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={clsx(
              "inline-flex items-center gap-1.5 rounded-full border px-4 py-1.5 font-mm-ui text-sm font-medium transition-colors duration-150",
              active
                ? "border-mm-border bg-black/5 text-mm-heading"
                : "border-transparent bg-transparent text-mm-text-secondary hover:bg-black/[0.03] hover:text-mm-heading"
            )}
          >
            <span>{opt.label}</span>
            {typeof opt.count === "number" && (
              <span className="font-mm-data text-xs text-mm-text-muted">
                ({opt.count})
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
