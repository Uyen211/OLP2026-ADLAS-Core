/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React from "react";
import { clsx } from "clsx";

export interface FormFieldProps {
  label: string;
  htmlFor?: string;
  required?: boolean;
  error?: string | null;
  helper?: string;
  className?: string;
  children: React.ReactNode;
}

export const FormField: React.FC<FormFieldProps> = ({
  label,
  htmlFor,
  required = false,
  error,
  helper,
  className,
  children,
}) => {
  return (
    <div className={clsx("space-y-1.5", className)}>
      <label
        htmlFor={htmlFor}
        className="block font-mm-ui text-sm font-medium text-mm-heading"
      >
        {label}
        {required && <span className="ml-1 text-mm-danger">*</span>}
      </label>
      {children}
      {error ? (
        <p role="alert" className="font-mm-ui text-xs text-mm-danger">
          {error}
        </p>
      ) : helper ? (
        <p className="mm-caption font-mm-ui text-xs text-mm-text-helper">
          {helper}
        </p>
      ) : null}
    </div>
  );
};

export function mmInputClass(hasError?: boolean): string {
  return clsx(
    "w-full rounded-mm-btn border bg-mm-bg px-3.5 py-2.5 font-mm-ui text-sm text-mm-text placeholder:text-mm-text-muted transition-colors focus:outline-none focus:ring-2",
    hasError
      ? "border-mm-danger focus:border-mm-danger focus:ring-mm-danger/20"
      : "border-mm-border focus:border-mm-blue-hover focus:ring-mm-blue-hover/20"
  );
}
