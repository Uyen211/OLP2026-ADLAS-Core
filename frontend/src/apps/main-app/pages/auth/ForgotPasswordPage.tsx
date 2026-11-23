/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Mail } from "lucide-react";
import { authService } from "../../../../services/authService";
import { ApiError } from "../../../../services/httpClient";
import { FormField, mmInputClass } from "../../components/FormField";
import { MmButton } from "../../components/MmButton";
import { AuthLayout } from "../../layouts/AuthLayout";

export const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const cleaned = email.trim();
    if (!cleaned || !cleaned.includes("@")) {
      setError("Vui lòng nhập địa chỉ email hợp lệ.");
      return;
    }

    setError(null);
    setLoading(true);

    try {
      await authService.forgotPassword(cleaned);
      setSubmitted(true);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Không thể gửi yêu cầu lúc này. Vui lòng thử lại sau.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Quên mật khẩu"
      subtitle="Nhập email đã đăng ký để nhận hướng dẫn đặt lại mật khẩu"
    >
      {submitted ? (
        <div className="space-y-5 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-mm-success-bg text-mm-success">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <p className="font-mm-ui text-sm leading-relaxed text-mm-text-secondary">
            Nếu địa chỉ email <span className="font-medium text-mm-heading">{email}</span>{" "}
            tồn tại trong hệ thống, liên kết đặt lại mật khẩu (hiệu lực 15 phút) đã được
            gửi đến hộp thư của bạn.
          </p>
          <Link to="/login" className="block">
            <MmButton variant="secondary" fullWidth>
              <ArrowLeft className="h-4 w-4" />
              <span>Quay lại đăng nhập</span>
            </MmButton>
          </Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <FormField label="Email đã đăng ký" htmlFor="forgot-email" required error={error}>
            <input
              id="forgot-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (error) setError(null);
              }}
              placeholder="vd: sinhvien@adlas.edu.vn"
              className={mmInputClass(Boolean(error))}
            />
          </FormField>

          <MmButton type="submit" variant="primary" fullWidth loading={loading}>
            <Mail className="h-4 w-4" />
            <span>Gửi yêu cầu đặt lại mật khẩu</span>
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
      )}
    </AuthLayout>
  );
};
