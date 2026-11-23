/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertCircle, ArrowLeft, ShieldCheck } from "lucide-react";
import { authService } from "../../../../services/authService";
import { ApiError } from "../../../../services/httpClient";
import { useAuthStore } from "../../../../stores/authStore";
import { CountdownTimer } from "../../components/CountdownTimer";
import { MmButton } from "../../components/MmButton";
import { OtpInput } from "../../components/OtpInput";
import { showToast } from "../../components/Toast";
import { AuthLayout } from "../../layouts/AuthLayout";
import { resolveLandingPath } from "./LoginPage";

export const MfaVerifyPage: React.FC = () => {
  const navigate = useNavigate();
  const { pendingMfaToken, setSession, setPendingMfaToken } = useAuthStore();

  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lockSeconds, setLockSeconds] = useState(0);

  useEffect(() => {
    if (!pendingMfaToken) {
      navigate("/login", { replace: true });
    }
  }, [pendingMfaToken, navigate]);

  const isLocked = lockSeconds > 0;

  const handleVerify = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!pendingMfaToken || isLocked || loading) return;

    if (code.length !== 6) {
      setErrorMessage("Vui lòng nhập đầy đủ 6 chữ số xác thực.");
      return;
    }

    setErrorMessage(null);
    setLoading(true);

    try {
      const response = await authService.verifyMfa({
        mfa_token: pendingMfaToken,
        code,
      });
      setSession(response);
      showToast("success", "Đăng nhập thành công!");
      navigate(resolveLandingPath(response.user.landing), { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === "E-6") {
          setLockSeconds(err.retryAfterSeconds ?? 900);
          setErrorMessage(err.message);
        } else {
          setErrorMessage(err.message);
        }
      } else {
        setErrorMessage("Không thể xác thực mã OTP. Vui lòng thử lại.");
      }
      setCode("");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Xác thực hai lớp"
      subtitle="Nhập mã 6 chữ số từ ứng dụng xác thực của bạn"
    >
      <form onSubmit={handleVerify} className="space-y-5">
        <div className="flex flex-col items-center">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-mm-blue-light/50 text-mm-blue-deep">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <p className="mb-5 text-center font-mm-ui text-base text-mm-text-secondary">
            Bạn có thể dán trực tiếp chuỗi 6 chữ số từ ứng dụng Authenticator.
          </p>

          <OtpInput
            value={code}
            onChange={(val) => {
              setCode(val);
              if (errorMessage) setErrorMessage(null);
            }}
            hasError={Boolean(errorMessage)}
            disabled={isLocked || loading}
          />
        </div>

        {errorMessage && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-mm-panel border border-mm-danger/30 bg-mm-danger-bg px-3.5 py-2.5 text-mm-danger"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <div className="font-mm-ui text-sm">
              <p>{errorMessage}</p>
              {isLocked && (
                <p className="mt-1 text-xs">
                  Mở khóa sau:{" "}
                  <CountdownTimer
                    initialSeconds={lockSeconds}
                    onExpire={() => {
                      setLockSeconds(0);
                      setErrorMessage(null);
                    }}
                  />
                </p>
              )}
            </div>
          </div>
        )}

        <MmButton
          type="submit"
          variant="brand"
          fullWidth
          loading={loading}
          disabled={isLocked || code.length !== 6}
        >
          Xác nhận mã OTP
        </MmButton>

        <div className="text-center">
          <Link
            to="/login"
            onClick={() => setPendingMfaToken(null)}
            className="inline-flex items-center gap-1.5 font-mm-ui text-sm font-medium text-mm-text-secondary hover:text-mm-heading"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Quay lại trang đăng nhập</span>
          </Link>
        </div>
      </form>
    </AuthLayout>
  );
};
