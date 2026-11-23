/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AlertCircle, ArrowLeft, KeyRound } from "lucide-react";
import { authService } from "../../../../services/authService";
import { ApiError } from "../../../../services/httpClient";
import { FormField, mmInputClass } from "../../components/FormField";
import { MmButton } from "../../components/MmButton";
import { showToast } from "../../components/Toast";
import { AuthLayout } from "../../layouts/AuthLayout";

export const ResetPasswordPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialToken = searchParams.get("token") ?? "";

  const [token, setToken] = useState(initialToken);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!token.trim()) {
      setError("Thiếu mã xác thực đặt lại mật khẩu.");
      return;
    }
    if (!newPassword || !confirmPassword) {
      setError("Vui lòng nhập đầy đủ mật khẩu mới và xác nhận mật khẩu.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Mật khẩu xác nhận không trùng khớp.");
      return;
    }

    setError(null);
    setLoading(true);

    try {
      await authService.resetPassword({
        token: token.trim(),
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      showToast("success", "Đặt lại mật khẩu thành công! Vui lòng đăng nhập lại.");
      navigate("/login", { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Không thể đặt lại mật khẩu. Vui lòng thử lại.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Đặt lại mật khẩu"
      subtitle="Tạo mật khẩu mới có ít nhất 8 ký tự gồm chữ hoa, chữ thường, số và ký tự đặc biệt"
    >
      {error && (
        <div
          role="alert"
          className="mb-4 flex items-start gap-2 rounded-mm-panel border border-mm-danger/30 bg-mm-danger-bg px-3.5 py-2.5 text-mm-danger"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span className="font-mm-ui text-sm">{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {!initialToken && (
          <FormField label="Mã đặt lại mật khẩu" htmlFor="reset-token" required>
            <input
              id="reset-token"
              type="text"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Dán mã token nhận được từ email"
              className={mmInputClass(false)}
            />
          </FormField>
        )}

        <FormField label="Mật khẩu mới" htmlFor="reset-new-password" required>
          <input
            id="reset-new-password"
            type="password"
            autoComplete="new-password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="Tối thiểu 8 ký tự"
            className={mmInputClass(false)}
          />
        </FormField>

        <FormField label="Xác nhận mật khẩu mới" htmlFor="reset-confirm-password" required>
          <input
            id="reset-confirm-password"
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Nhập lại mật khẩu mới"
            className={mmInputClass(false)}
          />
        </FormField>

        <MmButton type="submit" variant="brand" fullWidth loading={loading}>
          <KeyRound className="h-4 w-4" />
          <span>Lưu mật khẩu mới</span>
        </MmButton>

        <div className="pt-1 text-center">
          <Link
            to="/login"
            className="inline-flex items-center gap-1.5 font-mm-ui text-sm font-medium text-mm-text-secondary hover:text-mm-heading"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Quay lại đăng nhập</span>
          </Link>
        </div>
      </form>
    </AuthLayout>
  );
};
