/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useState } from "react";
import { AlertCircle, Sliders, Zap } from "lucide-react";
import { Modal } from "../../../components/ui/Modal";
import { GatewayService } from "../../../services/gatewayService";
import { RateLimitConfig, RateLimitUpdatePayload } from "../../../types/gateway";

interface RateLimitModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentConfig: RateLimitConfig | null;
  onSuccess: () => void;
}

export const RateLimitModal: React.FC<RateLimitModalProps> = ({
  isOpen,
  onClose,
  currentConfig,
  onSuccess,
}) => {
  const [standardRpm, setStandardRpm] = useState(120);
  const [examRpm, setExamRpm] = useState(300);
  const [blockDuration, setBlockDuration] = useState(5);
  const [examModeEnabled, setExamModeEnabled] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (currentConfig) {
      setStandardRpm(currentConfig.standard_rpm);
      setExamRpm(currentConfig.exam_rpm);
      setBlockDuration(currentConfig.ip_block_duration_minutes);
      setExamModeEnabled(currentConfig.exam_mode_enabled);
    }
  }, [currentConfig]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    // Rule E-GATEWAY-02
    if (standardRpm < 10 || standardRpm > 10000) {
      setErrorMessage("Regular rate limit must be between 10 and 10,000 req/min (Rule E-GATEWAY-02).");
      return;
    }

    // Rule BR-GATEWAY-01
    if (examRpm < 300) {
      setErrorMessage("Exam room rate limit must be at least 300 req/min to guarantee autosave throughput (Rule BR-GATEWAY-01).");
      return;
    }

    if (examRpm > 10000) {
      setErrorMessage("Exam room rate limit cannot exceed 10,000 req/min.");
      return;
    }

    const payload: RateLimitUpdatePayload = {
      standard_rpm: Number(standardRpm),
      exam_rpm: Number(examRpm),
      ip_block_duration_minutes: Number(blockDuration),
      exam_mode_enabled: examModeEnabled,
    };

    setIsSubmitting(true);
    try {
      await GatewayService.updateRateLimits(payload);
      onSuccess();
      onClose();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Failed to update rate limit policies.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Configure Gateway Rate Limiting & Protection" maxWidth="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        {errorMessage && (
          <div className="flex items-start gap-2.5 p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-sm">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        <div>
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
            Regular User Rate Limit (req/min) <span className="text-rose-500">*</span>
          </label>
          <input
            type="number"
            min={10}
            max={10000}
            required
            value={standardRpm}
            onChange={(e) => setStandardRpm(Number(e.target.value))}
            className="w-full px-3.5 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          />
          <p className="text-[11px] text-slate-500 mt-1">
            Allowed range: 10 - 10,000 req/min. Default: 120 req/min (Rule E-GATEWAY-02).
          </p>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
            Exam Room Priority Limit (req/min) <span className="text-rose-500">*</span>
          </label>
          <input
            type="number"
            min={300}
            max={10000}
            required
            value={examRpm}
            onChange={(e) => setExamRpm(Number(e.target.value))}
            className="w-full px-3.5 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          />
          <p className="text-[11px] text-slate-500 mt-1">
            Minimum threshold: 300 req/min to protect autosave transactions from packet throttling (Rule BR-GATEWAY-01).
          </p>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
            Temporary IP Block Duration
          </label>
          <select
            value={blockDuration}
            onChange={(e) => setBlockDuration(Number(e.target.value))}
            className="w-full px-3.5 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          >
            <option value={1}>1 minute</option>
            <option value={5}>5 minutes (Standard recommendation)</option>
            <option value={15}>15 minutes (High security mode)</option>
          </select>
          <p className="text-[11px] text-slate-500 mt-1">
            Duration for edge firewall ban when an IP triggers spam protection (Rule BR-GATEWAY-02).
          </p>
        </div>

        <div className="p-3.5 bg-blue-50/70 border border-blue-100 rounded-xl flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Zap className="w-5 h-5 text-blue-600" />
            <div>
              <p className="text-xs font-semibold text-blue-900">Active High-Stakes Exam Mode</p>
              <p className="text-[11px] text-blue-700">Enforce strict traffic priority on /examination routes.</p>
            </div>
          </div>
          <input
            type="checkbox"
            checked={examModeEnabled}
            onChange={(e) => setExamModeEnabled(e.target.checked)}
            className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
          />
        </div>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 rounded-pill transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="inline-flex items-center gap-2 px-5 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-pill shadow-brand transition-all"
          >
            <Sliders className="w-4 h-4" />
            {isSubmitting ? "Applying..." : "Apply Policy"}
          </button>
        </div>
      </form>
    </Modal>
  );
};
