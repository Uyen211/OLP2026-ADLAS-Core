// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authService } from "../../../../services/authService";
import { EduButton, EduInput } from "../../../../design-system";
import { PasswordStrengthMeter } from "../components/PasswordStrengthMeter";
import { AuthShowcasePanel } from "../components/AuthShowcasePanel";
import { ArrowRight } from "lucide-react";

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [role, setRole] = useState<"STUDENT" | "INSTRUCTOR">("STUDENT");

  const [errors, setErrors] = useState<{
    fullName?: string;
    email?: string;
    password?: string;
    confirmPassword?: string;
    general?: string;
  }>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const validate = () => {
    const errs: typeof errors = {};
    if (!fullName.trim()) {
      errs.fullName = "Vui lòng nhập họ và tên của bạn.";
    }
    if (!email.trim()) {
      errs.email = "Vui lòng nhập địa chỉ email.";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      errs.email = "Địa chỉ email không đúng định dạng chuẩn (ví dụ: sv@adlas.edu.vn).";
    }

    if (password.length < 8) {
      errs.password = "Mật khẩu cần tối thiểu 8 ký tự.";
    } else if (
      !/[A-Z]/.test(password) ||
      !/[a-z]/.test(password) ||
      !/[0-9]/.test(password)
    ) {
      errs.password = "Mật khẩu cần chứa cả chữ in hoa, chữ thường và chữ số.";
    }

    if (password !== confirmPassword) {
      errs.confirmPassword = "Mật khẩu xác nhận không khớp với mật khẩu đã nhập.";
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) {
      // Focus first error field for accessibility
      const firstField = document.querySelector('[aria-invalid="true"]') as HTMLElement;
      if (firstField) firstField.focus();
      return;
    }

    setIsLoading(true);
    setErrors({});

    try {
      await authService.register({
        full_name: fullName.trim(),
        email: email.trim(),
        password,
        role,
      });
      setIsSuccess(true);
      setTimeout(() => {
        navigate("/login", {
          state: {
            registeredEmail: email.trim(),
            message: "Đăng ký tài khoản thành công! Vui lòng đăng nhập.",
          },
        });
      }, 1500);
    } catch (err: any) {
      const detail = err?.message || err?.detail || "Đăng ký không thành công. Vui lòng thử lại.";
      if (err?.code === "E-AUTH-02" || detail.includes("Email")) {
        setErrors({ email: "Email này đã được sử dụng trên hệ thống ADLAS." });
      } else {
        setErrors({ general: detail });
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 sm:p-6 bg-[#f5fbfd]">
      <div className="w-full max-w-5xl rounded-3xl overflow-hidden shadow-2xl border border-[rgba(15,34,54,0.12)] grid grid-cols-1 lg:grid-cols-12 bg-white">
        {/* Left Column: Educational Showcase */}
        <div className="hidden lg:block lg:col-span-5 border-r border-[rgba(15,34,54,0.08)]">
          <AuthShowcasePanel />
        </div>

        {/* Right Column: Registration Form */}
        <div className="lg:col-span-7 p-6 sm:p-10 flex flex-col justify-center">
          <div className="max-w-md mx-auto w-full">
            <div className="mb-6">
              <h1 className="text-2xl sm:text-3xl font-extrabold text-[#0f2236] font-['Space_Grotesk'] tracking-tight">
                Tạo tài khoản mới
              </h1>
              <p className="text-sm text-[#4a5f75] mt-1.5 leading-relaxed">
                Tham gia hệ thống học tập tương tác và thẩm định thực lực ADLAS.
              </p>
            </div>

            {errors.general && (
              <div className="mb-5 p-3.5 rounded-xl bg-[#fef2f2] border border-[#b91c1c]/20 text-xs font-semibold text-[#b91c1c]">
                {errors.general}
              </div>
            )}

            {isSuccess && (
              <div className="mb-5 p-3.5 rounded-xl bg-[#ecfdf5] border border-[#15803d]/20 text-xs font-semibold text-[#15803d] animate-edu-fade-in">
                Đăng ký thành công! Đang chuyển hướng sang trang đăng nhập...
              </div>
            )}

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <EduInput
                label="Họ và tên"
                placeholder="Ví dụ: Nguyễn Văn An"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                error={errors.fullName}
                disabled={isLoading || isSuccess}
                autoFocus
              />

              <EduInput
                label="Địa chỉ Email"
                type="email"
                placeholder="tenban@truong.edu.vn"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                error={errors.email}
                disabled={isLoading || isSuccess}
              />

              <div>
                <label className="text-sm font-semibold text-[#0f2236] block mb-1.5">
                  Vai trò chính
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setRole("STUDENT")}
                    className={`py-2 px-3 text-sm font-semibold rounded-xl border transition-all text-center ${
                      role === "STUDENT"
                        ? "bg-[#c4e9f2] text-[#0f2236] border-[#7fbbdd] shadow-sm"
                        : "bg-white text-[#4a5f75] border-[rgba(15,34,54,0.15)] hover:border-[#7fbbdd]"
                    }`}
                  >
                    Sinh viên
                  </button>
                  <button
                    type="button"
                    onClick={() => setRole("INSTRUCTOR")}
                    className={`py-2 px-3 text-sm font-semibold rounded-xl border transition-all text-center ${
                      role === "INSTRUCTOR"
                        ? "bg-[#c4e9f2] text-[#0f2236] border-[#7fbbdd] shadow-sm"
                        : "bg-white text-[#4a5f75] border-[rgba(15,34,54,0.15)] hover:border-[#7fbbdd]"
                    }`}
                  >
                    Giảng viên
                  </button>
                </div>
              </div>

              <div>
                <EduInput
                  label="Mật khẩu"
                  type="password"
                  placeholder="Nhập tối thiểu 8 ký tự..."
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  error={errors.password}
                  disabled={isLoading || isSuccess}
                />
                {password.length > 0 && <PasswordStrengthMeter password={password} />}
              </div>

              <EduInput
                label="Xác nhận mật khẩu"
                type="password"
                placeholder="Nhập lại mật khẩu..."
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                error={errors.confirmPassword}
                disabled={isLoading || isSuccess}
              />

              <div className="pt-2">
                <EduButton
                  type="submit"
                  variant="primary"
                  size="lg"
                  className="w-full"
                  isLoading={isLoading}
                  rightIcon={<ArrowRight className="w-4 h-4" aria-hidden="true" />}
                >
                  Đăng ký tài khoản
                </EduButton>
              </div>
            </form>

            <div className="mt-6 pt-5 border-t border-[rgba(15,34,54,0.08)] text-center text-sm text-[#4a5f75]">
              <span>Đã có tài khoản? </span>
              <Link
                to="/login"
                className="font-bold text-[#0f2236] hover:text-[#f58b05] transition-colors underline-offset-2 hover:underline"
              >
                Đăng nhập ngay
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
