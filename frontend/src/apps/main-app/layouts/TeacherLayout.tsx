/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React from "react";
import { AppTopNav } from "./AppTopNav";

export interface TeacherLayoutProps {
  children: React.ReactNode;
}

export const TeacherLayout: React.FC<TeacherLayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen bg-mm-bg text-mm-text">
      <AppTopNav />
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">{children}</main>
    </div>
  );
};
