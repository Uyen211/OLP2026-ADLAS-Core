// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React from "react";
import { CheckCircle2, AlertCircle, HelpCircle, Star, Sparkles, Info } from "lucide-react";

export type EduBadgeVariant =
  | "correct"
  | "incorrect"
  | "hint"
  | "sky"
  | "gold"
  | "neutral";

export interface EduBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: EduBadgeVariant;
  label: string;
  showIcon?: boolean;
}

const variantStyles: Record<EduBadgeVariant, { bg: string; text: string; border: string; defaultIcon: React.ReactNode }> = {
  correct: {
    bg: "bg-[#ecfdf5]",
    text: "text-[#15803d]",
    border: "border-[#15803d]/20",
    defaultIcon: <CheckCircle2 className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />,
  },
  incorrect: {
    bg: "bg-[#fef2f2]",
    text: "text-[#b91c1c]",
    border: "border-[#b91c1c]/20",
    defaultIcon: <AlertCircle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />,
  },
  hint: {
    bg: "bg-[#fffbeb]",
    text: "text-[#7a4100]",
    border: "border-[#f58b05]/30",
    defaultIcon: <HelpCircle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />,
  },
  sky: {
    bg: "bg-[#eaf6fa]",
    text: "text-[#0f2236]",
    border: "border-[#7fbbdd]/40",
    defaultIcon: <Sparkles className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />,
  },
  gold: {
    bg: "bg-[#fff8e1]",
    text: "text-[#1a1400]",
    border: "border-[#ffc22f]/50",
    defaultIcon: <Star className="w-3.5 h-3.5 shrink-0 fill-current" aria-hidden="true" />,
  },
  neutral: {
    bg: "bg-[#f1f5f9]",
    text: "text-[#475569]",
    border: "border-[#cbd5e1]",
    defaultIcon: <Info className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />,
  },
};

export const EduBadge: React.FC<EduBadgeProps> = ({
  variant = "neutral",
  label,
  showIcon = true,
  className = "",
  ...props
}) => {
  const current = variantStyles[variant];

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full border ${current.bg} ${current.text} ${current.border} ${className}`}
      {...props}
    >
      {showIcon && current.defaultIcon}
      <span>{label}</span>
    </span>
  );
};
