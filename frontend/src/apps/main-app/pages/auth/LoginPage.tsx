/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertCircle, Eye, EyeOff, Lock, LogIn } from "lucide-react";
import { authService } from "../../../../services/authService";
import { ApiError } from "../../../../services/httpClient";
import { useAuthStore } from "../../../../stores/authStore";
import type { LandingTarget } from "../../../../types/auth";
import { CountdownTimer } from "../../components/CountdownTimer";
import { FormField, mmInputClass } from "../../components/FormField";
import { MmButton } from "../../components/MmButton";
import { showToast } from "../../components/Toast";
import { AuthLayout } from "../../layouts/AuthLayout";

export function resolveLandingPath(landing: LandingTarget): string {
  if (landing === "ADMIN_CONSOLE") return "/admin";
  if (landing === "TEACHING") return "/courses?filter=teaching";
  return "/courses?filter=learning";
}

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { setSession, setPendingMfaToken } = useAuthStore();

  const identifierRef = useRef<HTMLInputElement | null>(null);
  const passwordRef = useRef<HTMLInputElement | null>(null);

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const [fieldErrors, setFieldErrors] = useState<{
    identifier?: string;
    password?: string;
  }>({});
  const [bannerError, setBannerError] = useState<string | null>(null);
  const [lockSeconds, setLockSeconds] = useState<number>(0);

  const isLocked = lockSeconds > 0;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (isLocked || loading) return;

    const nextErrors: { identifier?: string; password?: string } = {};
    if (!identifier.trim()) {
      nextErrors.identifier = "Vui lòng nhập email hoặc MSSV / Mã giảng viên.";
    }
    if (!password) {
      nextErrors.password = "Vui lòng nhập mật khẩu.";
    }

    if (Object.keys(nextErrors).length > 0) {
      setFieldErrors(nextErrors);
      setBannerError(null);
      if (nextErrors.identifier) {
        identifierRef.current?.focus();
      } else if (nextErrors.password) {
        passwordRef.current?.focus();
      }
      return;
    }

    setFieldErrors({});
    setBannerError(null);
    setLoading(true);

    try {
      const response = await authService.login({
        identifier: identifier.trim(),
        password,
        remember_me: rememberMe,
      });

      if (response.requires_mfa && response.mfa_token) {
        setPendingMfaToken(response.mfa_token);
        navigate("/mfa-verify");
        return;
      }

      if (response.access_token && response.refresh_token && response.user) {
        setSession({
          access_token: response.access_token,
          refresh_token: response.refresh_token,
          token_type: response.token_type,
          expires_in: response.expires_in,
          user: response.user,
        });
        showToast("success", "Đăng nhập thành công!");
        navigate(resolveLandingPath(response.user.landing), { replace: true });
      }
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === "E-6") {
          setLockSeconds(err.retryAfterSeconds ?? 900);
          setBannerError(err.message);
          setPassword("");
        } else if (err.code === "E-5") {
          const attemptsNote =
            typeof err.remainingAttempts === "number"
              ? ` Bạn còn ${err.remainingAttempts} lần thử trước khi tài khoản tạm khóa.`
              : "";
          setBannerError(`${err.message}${attemptsNote}`);
          setPassword("");
          passwordRef.current?.focus();
        } else if (err.code === "E-1") {
          setBannerError(err.message);
        } else {
          setBannerError(err.message);
        }
      } else {
        setBannerError("Đã xảy ra lỗi khi đăng nhập. Vui lòng thử lại.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Đăng nhập ADLAS"
      subtitle="Sử dụng email trường hoặc MSSV / Mã giảng viên để tiếp tục"
    >
      {bannerError && (
        <div
          role="alert"
          className="mb-5 flex items-start gap-2.5 rounded-mm-panel border border-mm-danger/30 bg-mm-danger-bg px-4 py-3 text-mm-danger"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <div className="font-mm-ui text-sm leading-snug">
            <p>{bannerError}</p>
            {isLocked && (
              <p className="mt-1.5 flex items-center gap-1.5 text-xs">
                <Lock className="h-3.5 w-3.5" />
                <span>Mở khóa sau:</span>
                <CountdownTimer
                  initialSeconds={lockSeconds}
                  onExpire={() => {
                    setLockSeconds(0);
                    setBannerError(null);
                  }}
                  className="font-mm-mono text-sm font-medium tabular-nums"
                />
              </p>
            )}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        <FormField
          label="Email hoặc MSSV / Mã giảng viên"
          htmlFor="login-identifier"
          required
          error={fieldErrors.identifier}
        >
          <input
            ref={identifierRef}
            id="login-identifier"
            type="text"
            autoComplete="username"
            disabled={isLocked || loading}
            value={identifier}
            onChange={(e) => {
              setIdentifier(e.target.value);
              if (fieldErrors.identifier) {
                setFieldErrors((prev) => ({ ...prev, identifier: undefined }));
              }
            }}
            placeholder="vd: gv001@adlas.edu.vn hoặc SV2026001"
            className={mmInputClass(Boolean(fieldErrors.identifier))}
          />
        </FormField>

        <FormField
          label="Mật khẩu"
          htmlFor="login-password"
          required
          error={fieldErrors.password}
        >
          <div className="relative">
            <input
              ref={passwordRef}
              id="login-password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              disabled={isLocked || loading}
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (fieldErrors.password) {
                  setFieldErrors((prev) => ({ ...prev, password: undefined }));
                }
              }}
              placeholder="Nhập mật khẩu của bạn"
              className={`${mmInputClass(Boolean(fieldErrors.password))} pr-10`}
            />
            <button
              type="button"
              tabIndex={-1}
              aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
              onClick={() => setShowPassword((prev) => !prev)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-mm-text-muted hover:text-mm-heading"
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </FormField>

        <div className="flex items-center justify-between pt-1">
          <label className="inline-flex cursor-pointer items-center gap-2 font-mm-ui text-sm text-mm-text-secondary">
            <input
              type="checkbox"
              checked={rememberMe}
              disabled={isLocked || loading}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="h-4 w-4 rounded border-mm-border text-mm-blue-hover focus:ring-mm-blue-hover/30"
            />
            <span>Ghi nhớ đăng nhập trên thiết bị này trong 7 ngày</span>
          </label>

          <Link
            to="/forgot-password"
            className="font-mm-ui text-sm font-medium text-mm-blue-hover hover:text-mm-blue-active"
          >
            Quên mật khẩu?
          </Link>
        </div>

        <MmButton
          type="submit"
          variant="primary"
          fullWidth
          loading={loading}
          disabled={isLocked}
          className="mt-2"
        >
          <LogIn className="h-4 w-4" />
          <span>{isLocked ? "Tài khoản đang tạm khóa" : "Đăng nhập"}</span>
        </MmButton>

        <div className="mt-4 text-center font-mm-ui text-sm text-mm-text-secondary border-t border-mm-divider pt-4">
          <span>Chưa có tài khoản? </span>
          <Link
            to="/register"
            className="font-semibold text-mm-blue-hover hover:text-mm-blue-active underline-offset-2 hover:underline"
          >
            Đăng ký ngay
          </Link>
        </div>
      </form>
    </AuthLayout>
  );
};
