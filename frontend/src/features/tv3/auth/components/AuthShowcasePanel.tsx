// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React from "react";
import { ShieldCheck, Sparkles, BookOpen, Award } from "lucide-react";

export const AuthShowcasePanel: React.FC = () => {
  return (
    <div className="w-full h-full bg-[#0f2236] text-white p-8 sm:p-12 flex flex-col justify-between relative overflow-hidden">
      {/* Background geometric accents */}
      <div className="absolute -right-20 -top-20 w-80 h-80 rounded-full bg-[#7fbbdd]/10 blur-3xl pointer-events-none" />
      <div className="absolute -left-16 -bottom-16 w-64 h-64 rounded-full bg-[#f58b05]/10 blur-2xl pointer-events-none" />

      {/* Header Branding */}
      <div className="relative z-10">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#c4e9f2]/15 border border-[#c4e9f2]/30 text-xs font-semibold text-[#c4e9f2] mb-6">
          <Sparkles className="w-3.5 h-3.5 text-[#ffc22f]" aria-hidden="true" />
          <span>DX-OS Open-Core Learning Platform</span>
        </div>
        <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight font-['Space_Grotesk'] leading-tight">
          ADLAS Academy
        </h2>
        <p className="text-sm text-[#94a3b8] mt-2 max-w-md leading-relaxed">
          Nền tảng Quản lý Học tập Tương tác & Thẩm định Năng lực Đa chiều theo khung chuẩn EBAF.
        </p>
      </div>

      {/* Feature Pillars */}
      <div className="relative z-10 my-8 flex flex-col gap-4">
        <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-white/5 border border-white/10">
          <div className="p-2 rounded-lg bg-[#f58b05]/20 text-[#ffc22f] shrink-0">
            <ShieldCheck className="w-5 h-5" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Liêm chính Học thuật Đa tầng</h3>
            <p className="text-xs text-[#94a3b8] mt-0.5">
              Phòng thi Viva Sandbox cách ly clipboard và giám sát Strict Mode 3 gậy tự động.
            </p>
          </div>
        </div>

        <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-white/5 border border-white/10">
          <div className="p-2 rounded-lg bg-[#c4e9f2]/20 text-[#c4e9f2] shrink-0">
            <BookOpen className="w-5 h-5" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Học tập Tương tác & Socratic</h3>
            <p className="text-xs text-[#94a3b8] mt-0.5">
              Giàn giáo tư duy Socratic không giải bài hộ, thúc đẩy người học tự chiếm lĩnh tri thức.
            </p>
          </div>
        </div>

        <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-white/5 border border-white/10">
          <div className="p-2 rounded-lg bg-[#15803d]/20 text-[#4ade80] shrink-0">
            <Award className="w-5 h-5" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Minh chứng Năng lực Thực chất</h3>
            <p className="text-xs text-[#94a3b8] mt-0.5">
              SpeedGrader 3 cột đối soát AI Rubric kết hợp phê chuẩn chuyên gia Human-in-the-Loop.
            </p>
          </div>
        </div>
      </div>

      {/* Footer Info */}
      <div className="relative z-10 pt-4 border-t border-white/10 flex items-center justify-between text-xs text-[#94a3b8]">
        <span>OLP Tin học 2026 — Khối Phần mềm Nguồn Mở</span>
        <span className="font-mono text-[#c4e9f2]">MIT License</span>
      </div>
    </div>
  );
};
