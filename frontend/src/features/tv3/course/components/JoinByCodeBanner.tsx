// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React, { useState } from "react";
import { KeyRound, ArrowRight, CheckCircle2 } from "lucide-react";
import { EduButton, EduCard } from "../../../../design-system";
import { httpRequest } from "../../../../services/httpClient";

export interface JoinByCodeBannerProps {
  onSuccess?: (courseId: string) => void;
  className?: string;
}

export const JoinByCodeBanner: React.FC<JoinByCodeBannerProps> = ({
  onSuccess,
  className = "",
}) => {
  const [code, setCode] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const handleJoin = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanCode = code.trim().toUpperCase();
    if (!cleanCode || cleanCode.length !== 6) {
      setError("Mã tham gia lớp gồm đúng 6 ký tự viết hoa hoặc số.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const res = await httpRequest<{ course_id: string; message?: string }>("/courses/join-by-code", {
        method: "POST",
        body: { join_code: cleanCode },
      });
      setSuccessMsg("Ghi danh vào lớp học thành công!");
      setCode("");
      if (onSuccess && res.course_id) {
        onSuccess(res.course_id);
      }
    } catch (err: any) {
      const code = err?.code;
      if (code === "E-ROSTER-03") {
        setError("Mã tham gia không tồn tại hoặc đã bị thu hồi.");
      } else if (code === "E-ROSTER-04") {
        setError("Lớp học đã đóng cổng ghi danh mới.");
      } else {
        setError(err?.message || "Không thể tham gia lớp bằng mã này. Vui lòng kiểm tra lại.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <EduCard
      variant="tint"
      padding="md"
      className={`flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${className}`}
    >
      <div className="flex items-center gap-3.5">
        <div className="w-10 h-10 rounded-xl bg-[#c4e9f2] border border-[#7fbbdd]/50 flex items-center justify-center text-[#0f2236] shrink-0">
          <KeyRound className="w-5 h-5" aria-hidden="true" />
        </div>
        <div>
          <h3 className="text-sm sm:text-base font-bold text-[#0f2236]">
            Tham gia lớp bằng Mã mời (Join Code)
          </h3>
          <p className="text-xs sm:text-sm text-[#4a5f75] mt-0.5">
            Nhập mã 6 ký tự do giảng viên cung cấp để tự động ghi danh vào lớp.
          </p>
        </div>
      </div>

      <form onSubmit={handleJoin} className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
        <div className="w-full sm:w-44">
          <input
            type="text"
            maxLength={6}
            placeholder="VD: C5MZ3Q"
            value={code}
            onChange={(e) => {
              setCode(e.target.value.toUpperCase());
              setError(null);
            }}
            translate="no"
            disabled={isLoading}
            className="w-full px-3.5 py-2 text-center text-sm font-bold tracking-widest font-mono uppercase rounded-xl border border-[rgba(15,34,54,0.18)] bg-white text-[#0f2236] outline-none focus:ring-2 focus:ring-[#7fbbdd] focus:border-[#7fbbdd]"
          />
        </div>

        <EduButton
          type="submit"
          variant="amber"
          size="sm"
          isLoading={isLoading}
          rightIcon={<ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />}
        >
          Tham gia
        </EduButton>
      </form>

      {error && (
        <div className="w-full text-xs font-semibold text-[#b91c1c] animate-edu-fade-in sm:col-span-2">
          {error}
        </div>
      )}

      {successMsg && (
        <div className="w-full text-xs font-semibold text-[#15803d] flex items-center gap-1.5 animate-edu-fade-in sm:col-span-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" aria-hidden="true" />
          <span>{successMsg}</span>
        </div>
      )}
    </EduCard>
  );
};
