/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useRef, useState } from "react";
import { clsx } from "clsx";
import { FileSpreadsheet, UploadCloud, X } from "lucide-react";

export interface FileDropzoneProps {
  accept?: string;
  file: File | null;
  onFileSelect: (file: File | null) => void;
  hasError?: boolean;
  helperText?: string;
  disabled?: boolean;
}

export const FileDropzone: React.FC<FileDropzoneProps> = ({
  accept = ".xlsx,.csv",
  file,
  onFileSelect,
  hasError = false,
  helperText = "Hỗ trợ định dạng .xlsx, .csv (tối đa 5MB, 2.000 dòng)",
  disabled = false,
}) => {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    onFileSelect(files[0]);
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        if (!disabled) handleFiles(e.dataTransfer.files);
      }}
      onClick={() => !disabled && inputRef.current?.click()}
      className={clsx(
        "relative flex cursor-pointer flex-col items-center justify-center rounded-mm-card border-2 border-dashed px-6 py-8 text-center transition-colors",
        disabled && "cursor-not-allowed opacity-60",
        hasError
          ? "border-mm-danger bg-mm-danger-bg/40"
          : isDragging
            ? "border-mm-blue-hover bg-mm-blue-light/20"
            : "border-mm-border bg-mm-bg hover:border-mm-blue-hover/60 hover:bg-mm-divider/40"
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        disabled={disabled}
        className="hidden"
        onChange={(e) => {
          handleFiles(e.target.files);
          e.target.value = "";
        }}
      />

      {file ? (
        <div className="flex w-full max-w-md items-center justify-between gap-3 rounded-mm-panel border border-mm-border bg-mm-bg px-4 py-3 text-left">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-mm-btn bg-mm-blue-light/50 text-mm-blue-deep">
              <FileSpreadsheet className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <p className="truncate font-mm-ui text-sm font-medium text-mm-heading">
                {file.name}
              </p>
              <p className="font-mm-data text-xs text-mm-text-muted">
                {(file.size / 1024).toFixed(1)} KB
              </p>
            </div>
          </div>
          <button
            type="button"
            aria-label="Xóa tệp đã chọn"
            onClick={(e) => {
              e.stopPropagation();
              onFileSelect(null);
            }}
            className="rounded-full p-1 text-mm-text-muted hover:bg-mm-divider hover:text-mm-heading"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ) : (
        <>
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-mm-divider text-mm-blue-primary">
            <UploadCloud className="h-6 w-6" />
          </div>
          <p className="font-mm-ui text-sm font-medium text-mm-heading">
            Kéo thả tệp vào đây hoặc nhấn để chọn tệp
          </p>
          <p className="mt-1 font-mm-ui text-xs text-mm-text-helper">{helperText}</p>
        </>
      )}
    </div>
  );
};
