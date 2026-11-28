// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React from "react";
import { EduModal } from "./EduModal";
import { EduButton } from "./EduButton";
import { AlertTriangle } from "lucide-react";

export interface EduConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "amber" | "primary";
  isLoading?: boolean;
}

export const EduConfirmDialog: React.FC<EduConfirmDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = "Xác nhận",
  cancelLabel = "Hủy bỏ",
  variant = "danger",
  isLoading = false,
}) => {
  return (
    <EduModal isOpen={isOpen} onClose={onClose} maxWidth="md">
      <div className="flex gap-4 items-start">
        <div
          className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
            variant === "danger"
              ? "bg-[#fef2f2] text-[#b91c1c] border border-[#b91c1c]/20"
              : "bg-[#fffbeb] text-[#f58b05] border border-[#f58b05]/30"
          }`}
        >
          <AlertTriangle className="w-5 h-5" aria-hidden="true" />
        </div>
        <div>
          <h3 className="text-base font-bold text-[#0f2236]">{title}</h3>
          <p className="text-sm text-[#4a5f75] mt-1.5 leading-relaxed">
            {message}
          </p>
        </div>
      </div>

      <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-[rgba(15,34,54,0.08)]">
        <EduButton variant="secondary" onClick={onClose} disabled={isLoading}>
          {cancelLabel}
        </EduButton>
        <EduButton
          variant={variant}
          onClick={onConfirm}
          isLoading={isLoading}
        >
          {confirmLabel}
        </EduButton>
      </div>
    </EduModal>
  );
};
