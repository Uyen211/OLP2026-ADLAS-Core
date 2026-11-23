/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React from "react";
import { clsx } from "clsx";

export interface PillTabItem<T extends string = string> {
  value: T;
  label: string;
  count?: number;
  icon?: React.ReactNode;
}

export interface PillTabsProps<T extends string = string> {
  items: PillTabItem<T>[];
  value: T;
  onChange: (value: T) => void;
  className?: string;
}

export function PillTabs<T extends string = string>({
  items,
  value,
  onChange,
  className,
}: PillTabsProps<T>): React.ReactElement {
  return (
    <div
      role="tablist"
      className={clsx(
        "inline-flex flex-wrap items-center gap-1 rounded-full border border-mm-border bg-mm-bg p-1",
        className
      )}
    >
      {items.map((item) => {
        const active = item.value === value;
        return (
          <button
            key={item.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(item.value)}
            className={clsx(
              "inline-flex items-center gap-2 rounded-full px-4 py-2 font-mm-ui text-sm font-medium transition-colors duration-150",
              active
                ? "bg-black/5 text-mm-heading"
                : "text-mm-text-secondary hover:bg-black/[0.03] hover:text-mm-heading"
            )}
          >
            {item.icon}
            <span>{item.label}</span>
            {typeof item.count === "number" && (
              <span className="rounded-full bg-mm-divider px-2 py-0.5 font-mm-data text-xs text-mm-text-secondary">
                {item.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
