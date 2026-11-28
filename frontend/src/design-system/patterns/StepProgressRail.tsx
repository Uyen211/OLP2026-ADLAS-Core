// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React from "react";
import { Check } from "lucide-react";

export interface StepItem {
  id: string | number;
  title: string;
  description?: string;
}

export interface StepProgressRailProps {
  steps: StepItem[];
  currentStepIndex: number;
  className?: string;
}

export const StepProgressRail: React.FC<StepProgressRailProps> = ({
  steps,
  currentStepIndex,
  className = "",
}) => {
  return (
    <div className={`w-full py-4 ${className}`}>
      <ol className="flex items-center w-full">
        {steps.map((step, idx) => {
          const isDone = idx < currentStepIndex;
          const isCurrent = idx === currentStepIndex;

          return (
            <li
              key={step.id}
              className={`flex items-center ${
                idx < steps.length - 1 ? "w-full" : ""
              }`}
            >
              <div className="flex flex-col items-center sm:items-start text-center sm:text-left">
                <div className="flex items-center gap-2.5">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold font-mono transition-colors shrink-0 ${
                      isDone
                        ? "bg-[#15803d] text-white"
                        : isCurrent
                        ? "bg-[#f58b05] text-[#1a1400] ring-4 ring-[#f58b05]/20"
                        : "bg-[#eaf6fa] text-[#4a5f75] border border-[rgba(15,34,54,0.15)]"
                    }`}
                  >
                    {isDone ? (
                      <Check className="w-4 h-4 stroke-[3]" aria-hidden="true" />
                    ) : (
                      idx + 1
                    )}
                  </div>
                  <span
                    className={`text-sm font-semibold hidden md:inline truncate ${
                      isCurrent
                        ? "text-[#0f2236]"
                        : isDone
                        ? "text-[#15803d]"
                        : "text-[#4a5f75]"
                    }`}
                  >
                    {step.title}
                  </span>
                </div>
              </div>

              {idx < steps.length - 1 && (
                <div
                  className={`flex-1 h-0.5 mx-3 transition-colors ${
                    idx < currentStepIndex ? "bg-[#15803d]" : "bg-[rgba(15,34,54,0.12)]"
                  }`}
                />
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
};
