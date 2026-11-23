/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect } from "react";
import { clsx } from "clsx";
import { X } from "lucide-react";

export interface MmModalProps {
  open: boolean;
  title: string;
  subtitle?: string;
  onClose: () => void;
  maxWidthClass?: string;
  footer?: React.ReactNode;
  children: React.ReactNode;
}

export const MmModal: React.FC<MmModalProps> = ({
  open,
  title,
  subtitle,
  onClose,
  maxWidthClass = "max-w-lg",
  footer,
  children,
}) => {
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-40 flex items-center justify-center bg-mm-dark/45 p-4 backdrop-blur-[2px]"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className={clsx(
          "flex max-h-[90vh] w-full flex-col overflow-hidden rounded-mm-card-lg border border-mm-border bg-mm-bg shadow-mm-elevated",
          maxWidthClass
        )}
      >
        <div className="flex items-start justify-between gap-4 border-b border-mm-divider px-6 py-5">
          <div>
            <h2 className="font-mm-mid text-lg font-medium text-mm-heading">{title}</h2>
            {subtitle && (
              <p className="mt-1 font-mm-ui text-sm text-mm-text-secondary">{subtitle}</p>
            )}
          </div>
          <button
            type="button"
            aria-label="Đóng hộp thoại"
            onClick={onClose}
            className="rounded-full p-1.5 text-mm-text-muted transition-colors hover:bg-mm-divider hover:text-mm-heading"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-5">{children}</div>

        {footer && (
          <div className="flex items-center justify-end gap-3 border-t border-mm-divider px-6 py-4">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};
