/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { BookOpen, LogOut, Menu, Shield, User, X } from "lucide-react";
import { authService } from "../../../services/authService";
import { useAuthStore } from "../../../stores/authStore";
import { useCourseContextStore } from "../../../stores/courseContextStore";
import { RoleBadge } from "../components/RoleBadge";
import { showToast } from "../components/Toast";
import { CourseContextSwitcher } from "./CourseContextSwitcher";

export const AppTopNav: React.FC = () => {
  const navigate = useNavigate();
  const { me, clearSession } = useAuthStore();
  const clearActiveCourse = useCourseContextStore((s) => s.clearActiveCourse);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    try {
      await authService.logout();
    } catch {
      // Clear local session even if server token already expired
    } finally {
      clearActiveCourse();
      clearSession();
      showToast("info", "Đã đăng xuất khỏi hệ thống.");
      navigate("/login", { replace: true });
    }
  };

  return (
    <header className="sticky top-0 z-30 border-b border-mm-border bg-mm-bg/95 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-4">
          <Link
            to="/courses"
            onClick={() => clearActiveCourse()}
            className="inline-flex items-center gap-2 focus:outline-none"
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-mm-btn bg-mm-dark font-mm-display text-base font-semibold text-white">
              A
            </span>
            <span className="flex items-center gap-1 font-mm-display text-xl font-semibold tracking-tight text-mm-heading">
              ADLAS
              <span className="mm-logo-dot inline-block h-1.5 w-1.5 rounded-full" />
            </span>
          </Link>

          <nav className="hidden items-center gap-1 md:flex">
            <Link
              to="/courses"
              className="inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 font-mm-ui text-sm font-medium text-mm-text-secondary transition-colors hover:bg-black/5 hover:text-mm-heading"
            >
              <BookOpen className="h-4 w-4" />
              Môn học của tôi
            </Link>
            {me?.system_role === "ADMIN" && (
              <Link
                to="/admin"
                className="inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 font-mm-ui text-sm font-medium text-mm-text-secondary transition-colors hover:bg-black/5 hover:text-mm-heading"
              >
                <Shield className="h-4 w-4" />
                Bảng điều khiển quản trị
              </Link>
            )}
          </nav>

          <div className="hidden lg:block">
            <CourseContextSwitcher />
          </div>
        </div>

        <div className="hidden items-center gap-3 md:flex">
          {me && (
            <div className="flex items-center gap-2.5 rounded-full border border-mm-border bg-mm-bg py-1 pl-1.5 pr-3">
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-mm-blue-light text-mm-blue-deep">
                <User className="h-4 w-4" />
              </div>
              <div className="text-left leading-tight">
                <p className="font-mm-ui text-xs font-medium text-mm-heading">
                  {me.full_name}
                </p>
                <p className="font-mm-data text-[11px] text-mm-text-muted">
                  {me.user_code || me.email}
                </p>
              </div>
              {me.system_role === "ADMIN" && <RoleBadge role="ADMIN" />}
            </div>
          )}

          <button
            type="button"
            onClick={handleLogout}
            className="inline-flex items-center gap-1.5 rounded-mm-btn border border-mm-border px-3 py-1.5 font-mm-ui text-sm font-medium text-mm-text-secondary transition-colors hover:bg-mm-divider hover:text-mm-heading"
          >
            <LogOut className="h-4 w-4" />
            <span>Đăng xuất</span>
          </button>
        </div>

        <button
          type="button"
          aria-label="Mở menu điều hướng"
          onClick={() => setMobileMenuOpen((prev) => !prev)}
          className="inline-flex items-center justify-center rounded-mm-btn border border-mm-border p-2 text-mm-heading md:hidden"
        >
          {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {mobileMenuOpen && (
        <div className="border-t border-mm-divider bg-mm-bg px-4 py-4 md:hidden">
          <div className="space-y-3">
            {me && (
              <div className="flex items-center justify-between rounded-mm-panel border border-mm-border p-3">
                <div>
                  <p className="font-mm-ui text-sm font-medium text-mm-heading">
                    {me.full_name}
                  </p>
                  <p className="font-mm-data text-xs text-mm-text-muted">
                    {me.user_code || me.email}
                  </p>
                </div>
                {me.system_role === "ADMIN" && <RoleBadge role="ADMIN" />}
              </div>
            )}

            <CourseContextSwitcher />

            <div className="flex flex-col gap-1">
              <Link
                to="/courses"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-2 rounded-mm-btn px-3 py-2 font-mm-ui text-sm font-medium text-mm-heading hover:bg-mm-divider"
              >
                <BookOpen className="h-4 w-4" />
                Môn học của tôi
              </Link>
              {me?.system_role === "ADMIN" && (
                <Link
                  to="/admin"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2 rounded-mm-btn px-3 py-2 font-mm-ui text-sm font-medium text-mm-heading hover:bg-mm-divider"
                >
                  <Shield className="h-4 w-4" />
                  Bảng điều khiển quản trị
                </Link>
              )}
              <button
                type="button"
                onClick={handleLogout}
                className="flex items-center gap-2 rounded-mm-btn px-3 py-2 text-left font-mm-ui text-sm font-medium text-mm-danger hover:bg-mm-danger-bg"
              >
                <LogOut className="h-4 w-4" />
                Đăng xuất
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
};
