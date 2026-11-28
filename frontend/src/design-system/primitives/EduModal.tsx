// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React, { useEffect, useRef } from "react";
import { X } from "lucide-react";

export interface EduModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  maxWidth?: "sm" | "md" | "lg" | "xl" | "2xl" | "3xl" | "4xl";
}

const maxWidthMap = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-xl",
  "2xl": "max-w-2xl",
  "3xl": "max-w-3xl",
  "4xl": "max-w-4xl",
};

export const EduModal: React.FC<EduModalProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  footer,
  maxWidth = "lg",
}) => {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-[#0f2236]/40 backdrop-blur-sm animate-edu-fade-in"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={modalRef}
        style={{ overscrollBehavior: "contain" }}
        className={`w-full ${maxWidthMap[maxWidth]} bg-white rounded-2xl border border-[rgba(15,34,54,0.12)] shadow-2xl overflow-hidden flex flex-col max-h-[90vh] animate-edu-scale-in`}
      >
        {(title || description) && (
          <div className="flex items-start justify-between p-5 border-b border-[rgba(15,34,54,0.08)] bg-[#f5fbfd]">
            <div>
              {title && (
                <h3 className="text-lg font-bold text-[#0f2236]">{title}</h3>
              )}
              {description && (
                <p className="text-sm text-[#4a5f75] mt-1">{description}</p>
              )}
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Đóng hộp thoại"
              className="p-1.5 rounded-lg text-[#4a5f75] hover:text-[#0f2236] hover:bg-[#eaf6fa] transition-colors"
            >
              <X className="w-5 h-5" aria-hidden="true" />
            </button>
          </div>
        )}

        <div className="p-6 overflow-y-auto flex-1">{children}</div>

        {footer && (
          <div className="p-4 sm:p-5 border-t border-[rgba(15,34,54,0.08)] bg-[#f5fbfd] flex justify-end gap-3">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};
