// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React from "react";
import { FolderOpen } from "lucide-react";
import { EduButton } from "./EduButton";

export interface EduEmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EduEmptyState: React.FC<EduEmptyStateProps> = ({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  className = "",
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 sm:p-12 text-center rounded-2xl border border-dashed border-[rgba(127,187,221,0.6)] bg-[#f5fbfd] ${className}`}
    >
      <div className="w-14 h-14 rounded-2xl bg-[#eaf6fa] border border-[rgba(127,187,221,0.5)] flex items-center justify-center text-[#7fbbdd] mb-4 shadow-sm">
        {icon || <FolderOpen className="w-7 h-7" aria-hidden="true" />}
      </div>
      <h4 className="text-base sm:text-lg font-bold text-[#0f2236]">{title}</h4>
      <p className="text-sm text-[#4a5f75] max-w-md mt-1.5 mb-5 leading-relaxed">
        {description}
      </p>
      {actionLabel && onAction && (
        <EduButton variant="sky" onClick={onAction}>
          {actionLabel}
        </EduButton>
      )}
    </div>
  );
};
