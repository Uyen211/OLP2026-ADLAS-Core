/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React from "react";
import { clsx } from "clsx";
import type { BloomLevel } from "../../../types/course";

export const BLOOM_META: Record<
  BloomLevel,
  { label: string; groupLabel: string; badgeClass: string }
> = {
  REMEMBER: {
    label: "Nhận biết",
    groupLabel: "Nhận biết",
    badgeClass: "bg-mm-btn-secondary text-mm-text-secondary",
  },
  UNDERSTAND: {
    label: "Thông hiểu",
    groupLabel: "Thông hiểu",
    badgeClass: "bg-mm-blue-light text-mm-blue-active",
  },
  APPLY: {
    label: "Vận dụng",
    groupLabel: "Vận dụng",
    badgeClass: "bg-mm-blue-500 text-white",
  },
  ANALYZE: {
    label: "Phân tích",
    groupLabel: "Phân tích - Đánh giá",
    badgeClass: "bg-mm-blue-deep text-white",
  },
  EVALUATE: {
    label: "Đánh giá",
    groupLabel: "Phân tích - Đánh giá",
    badgeClass: "bg-mm-blue-deep text-white",
  },
  CREATE: {
    label: "Sáng tạo",
    groupLabel: "Sáng tạo",
    badgeClass: "bg-mm-blue-primary text-white",
  },
};

export interface BloomBadgeProps {
  level: BloomLevel;
  className?: string;
}

export const BloomBadge: React.FC<BloomBadgeProps> = ({ level, className }) => {
  const meta = BLOOM_META[level] ?? BLOOM_META.UNDERSTAND;
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-3 py-0.5 font-mm-ui text-xs font-medium",
        meta.badgeClass,
        className
      )}
    >
      {meta.label}
    </span>
  );
};
