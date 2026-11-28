// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

export interface MemberScoreInput {
  student_id: string;
  student_name: string;
  scores_received: number[];
}

export interface MemberFactorResult {
  student_id: string;
  student_name: string;
  s_i: number; // Điểm trung bình nhận được
  s_bar: number; // Điểm trung bình chung cả nhóm
  raw_factor: number;
  f_i: number; // Hệ số đóng góp Fi sau khi clamp [0.50, 1.20]
  raw_grade?: number;
  adjusted_grade?: number; // Điểm cá nhân sau khi áp dụng Fi
}

/**
 * Tính toán hệ số đóng góp Fi theo công thức chuẩn:
 * Si = (1 / (N - 1)) * tổng(s_ji) (với j khác i)
 * S_bar = (1 / M) * tổng(Sk)
 * Fi = clamp(Si / S_bar, 0.50, 1.20)
 */
export function calculatePeerReviewFactors(
  members: MemberScoreInput[],
  groupRawGrade?: number,
  maxGrade: number = 10.0
): MemberFactorResult[] {
  if (members.length === 0) return [];

  // Bước 1: Tính S_i cho từng thành viên
  const memberAverages = members.map((m) => {
    if (m.scores_received.length === 0) {
      return { ...m, s_i: 0 };
    }
    const sum = m.scores_received.reduce((a, b) => a + b, 0);
    const avg = Number((sum / m.scores_received.length).toFixed(2));
    return { ...m, s_i: avg };
  });

  // Bước 2: Tính S_bar (trung bình nhóm)
  const sumSi = memberAverages.reduce((sum, m) => sum + m.s_i, 0);
  const s_bar = memberAverages.length > 0 ? Number((sumSi / memberAverages.length).toFixed(2)) : 0;

  // Bước 3: Tính Fi cho từng thành viên
  return memberAverages.map((m) => {
    let raw_factor = 1.0;
    let f_i = 1.0;

    if (s_bar > 0) {
      raw_factor = Number((m.s_i / s_bar).toFixed(4));
      // Clamp vào khoảng [0.50, 1.20]
      const clamped = Math.min(1.2, Math.max(0.5, raw_factor));
      f_i = Number(clamped.toFixed(2));
    }

    let adjusted_grade: number | undefined = undefined;
    if (groupRawGrade !== undefined) {
      const calcGrade = groupRawGrade * f_i;
      adjusted_grade = Number(Math.min(maxGrade, calcGrade).toFixed(2));
    }

    return {
      student_id: m.student_id,
      student_name: m.student_name,
      s_i: m.s_i,
      s_bar,
      raw_factor,
      f_i,
      raw_grade: groupRawGrade,
      adjusted_grade,
    };
  });
}
