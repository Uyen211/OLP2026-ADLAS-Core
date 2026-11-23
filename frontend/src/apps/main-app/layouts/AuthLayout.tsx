/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React from "react";
import { Link } from "react-router-dom";
import { MmCard } from "../components/MmCard";

export interface AuthLayoutProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({ title, subtitle, children }) => {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-mm-bg px-4 py-10">
      <div className="mb-8 flex items-center gap-2.5">
        <Link to="/login" className="inline-flex items-center gap-2 focus:outline-none">
          <span className="flex h-9 w-9 items-center justify-center rounded-mm-btn bg-mm-dark font-mm-display text-lg font-semibold text-white">
            A
          </span>
          <span className="flex items-center gap-1 font-mm-display text-2xl font-semibold tracking-tight text-mm-heading">
            ADLAS
            <span className="mm-logo-dot inline-block h-2 w-2 rounded-full" />
          </span>
        </Link>
      </div>

      <MmCard
        variant="featured"
        radius="card-lg"
        padding="lg"
        className="w-full max-w-[420px] sm:p-8"
      >
        <div className="mb-6 text-center">
          <h1 className="mm-hero-title font-mm-display text-[32px] font-semibold tracking-tight text-mm-heading">
            {title}
          </h1>
          {subtitle && (
            <p className="mt-2 font-mm-ui text-sm text-mm-text-secondary">{subtitle}</p>
          )}
        </div>
        {children}
      </MmCard>

      <p className="mt-8 text-center font-mm-ui text-xs text-mm-text-muted">
        Nền tảng học tập và đánh giá số ADLAS - OLP 2026
      </p>
    </div>
  );
};
