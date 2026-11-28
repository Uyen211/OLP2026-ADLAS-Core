// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React, { useEffect } from "react";
import { X } from "lucide-react";

export interface EduDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: React.ReactNode;
  width?: "md" | "lg" | "xl";
}

const widthMap = {
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-xl",
};

export const EduDrawer: React.FC<EduDrawerProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  width = "md",
}) => {
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
      className="fixed inset-0 z-50 flex justify-end bg-[#0f2236]/40 backdrop-blur-sm animate-edu-fade-in"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{ overscrollBehavior: "contain" }}
        className={`w-full ${widthMap[width]} bg-white border-l border-[rgba(15,34,54,0.12)] shadow-2xl h-full flex flex-col animate-edu-slide-up sm:animate-edu-slide-down`}
      >
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
            aria-label="Đóng bảng phụ"
            className="p-1.5 rounded-lg text-[#4a5f75] hover:text-[#0f2236] hover:bg-[#eaf6fa] transition-colors"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto flex-1">{children}</div>
      </div>
    </div>
  );
};
