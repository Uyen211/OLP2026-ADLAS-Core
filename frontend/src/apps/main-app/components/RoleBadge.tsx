/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React from "react";
import { clsx } from "clsx";
import type { ContextualRole } from "../../../types/course";

export interface RoleBadgeProps {
  role?: ContextualRole | string | null;
  className?: string;
}

export const RoleBadge: React.FC<RoleBadgeProps> = ({ role, className }) => {
  if (!role) return null;

  const upper = role.toUpperCase();
  let label = "SINH VIÊN";
  let styleClass = "bg-mm-btn-secondary text-mm-text-secondary";

  if (upper === "INSTRUCTOR") {
    label = "GIẢNG VIÊN";
    styleClass = "bg-mm-blue-light text-mm-blue-deep";
  } else if (upper === "TA") {
    label = "TRỢ GIẢNG";
    styleClass = "bg-mm-blue-light/70 text-mm-blue-deep";
  } else if (upper === "ADMIN") {
    label = "QUẢN TRỊ";
    styleClass = "bg-mm-dark text-white";
  }

  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-3 py-0.5 font-mm-ui text-xs font-medium tracking-wide",
        styleClass,
        className
      )}
    >
      {label}
    </span>
  );
};
