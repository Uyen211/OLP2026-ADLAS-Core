/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React from "react";
import { AlertTriangle } from "lucide-react";
import { MmButton } from "./MmButton";
import { MmModal } from "./MmModal";

export interface ConfirmModalProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export const ConfirmModal: React.FC<ConfirmModalProps> = ({
  open,
  title,
  description,
  confirmLabel = "Xác nhận",
  cancelLabel = "Hủy bỏ",
  danger = true,
  loading = false,
  onConfirm,
  onCancel,
}) => {
  return (
    <MmModal
      open={open}
      title={title}
      onClose={onCancel}
      maxWidthClass="max-w-md"
      footer={
        <>
          <MmButton variant="secondary" onClick={onCancel} disabled={loading}>
            {cancelLabel}
          </MmButton>
          <MmButton
            variant={danger ? "danger" : "brand"}
            onClick={onConfirm}
            loading={loading}
          >
            {confirmLabel}
          </MmButton>
        </>
      }
    >
      <div className="flex items-start gap-3">
        <div
          className={
            danger
              ? "flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-mm-danger-bg text-mm-danger"
              : "flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-mm-blue-light/50 text-mm-blue-deep"
          }
        >
          <AlertTriangle className="h-5 w-5" />
        </div>
        <p className="font-mm-ui text-sm leading-relaxed text-mm-text-secondary">
          {description}
        </p>
      </div>
    </MmModal>
  );
};
