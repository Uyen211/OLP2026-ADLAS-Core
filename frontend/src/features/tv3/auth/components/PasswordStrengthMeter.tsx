// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React from "react";
import { Check, X } from "lucide-react";

export interface PasswordStrengthMeterProps {
  password: string;
}

export const PasswordStrengthMeter: React.FC<PasswordStrengthMeterProps> = ({
  password,
}) => {
  const hasMinLength = password.length >= 8;
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasDigit = /[0-9]/.test(password);

  const criteria = [
    { label: "Tối thiểu 8 ký tự", met: hasMinLength },
    { label: "Có chữ cái in hoa (A-Z)", met: hasUpper },
    { label: "Có chữ cái in thường (a-z)", met: hasLower },
    { label: "Có chữ số (0-9)", met: hasDigit },
  ];

  const score = [hasMinLength, hasUpper, hasLower, hasDigit].filter(Boolean).length;

  const strengthColor =
    score === 4
      ? "bg-[#15803d]"
      : score >= 2
      ? "bg-[#f58b05]"
      : "bg-[#b91c1c]";

  return (
    <div className="w-full flex flex-col gap-2 mt-1">
      <div className="w-full h-1.5 bg-[#f1f5f9] rounded-full overflow-hidden flex">
        <div
          className={`h-full transition-all duration-200 ${strengthColor}`}
          style={{ width: `${(score / 4) * 100}%` }}
        />
      </div>

      <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-xs">
        {criteria.map((item, idx) => (
          <div
            key={idx}
            className={`flex items-center gap-1.5 transition-colors ${
              item.met ? "text-[#15803d] font-medium" : "text-[#94a3b8]"
            }`}
          >
            {item.met ? (
              <Check className="w-3.5 h-3.5 shrink-0 stroke-[2.5]" aria-hidden="true" />
            ) : (
              <X className="w-3.5 h-3.5 shrink-0 stroke-[2]" aria-hidden="true" />
            )}
            <span>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
