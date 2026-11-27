/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useMemo, useRef, useState } from "react";
import { clsx } from "clsx";
import {
  AlertCircle,
  Bot,
  CheckCircle2,
  Lock,
  ShieldAlert,
  ShieldCheck,
  ShieldOff,
} from "lucide-react";
import { assessmentService } from "../../../../services/assessmentService";
import { ApiError } from "../../../../services/httpClient";
import type {
  AIPolicyLevel,
  PledgeSignResponse,
  PledgeStatusResponse,
  PledgeTerm,
} from "../../../../types/assessment";
import { MmButton } from "../../components/MmButton";
import { MmModal } from "../../components/MmModal";
import { showToast } from "../../components/Toast";
import { resolveErrorMessage } from "../../constants/errorMessages";

export interface SignedPledgeResult {
  pledge: PledgeSignResponse;
  selfContributionPct: number;
  toolsUsed: string[];
  usageDescription: string;
}

export interface AcademicIntegrityModalProps {
  open: boolean;
  assignmentId: string;
  assignmentTitle: string;
  aiPolicyLevel: AIPolicyLevel | string;
  pledgeStatus: PledgeStatusResponse | null;
  initialSelfContributionPct?: number;
  initialToolsUsed?: string[];
  initialUsageDescription?: string;
  onCancel: () => void;
  onSigned: (result: SignedPledgeResult) => void;
}

const DEFAULT_TERMS: PledgeTerm[] = [
  {
    code: "ORIGINAL_WORK",
    text: "Tôi cam đoan bài nộp là sản phẩm do chính tôi thực hiện, không sao chép hay thuê người khác làm.",
  },
  {
    code: "AI_DISCLOSURE",
    text: "Tôi khai báo trung thực mọi công cụ trí tuệ nhân tạo đã sử dụng theo đúng chính sách của bài tập.",
  },
  {
    code: "VIVA_AND_CONSEQUENCES",
    text: "Tôi đồng ý tham gia vấn đáp xác thực và chấp nhận xử lý theo quy chế nếu vi phạm liêm chính học thuật.",
  },
];

const AI_TOOL_OPTIONS = [
  { id: "chatgpt", label: "ChatGPT (OpenAI)" },
  { id: "claude", label: "Claude (Anthropic)" },
  { id: "copilot", label: "GitHub Copilot" },
  { id: "gemini", label: "Google Gemini" },
  { id: "cursor", label: "Cursor AI" },
  { id: "other", label: "Công cụ khác" },
];

export const RED_POLICY_AUTO_DESCRIPTION =
  "Tôi cam đoan 100% bài làm do chính tôi tự thực hiện và không sử dụng bất kỳ công cụ AI nào theo quy định mức Đỏ.";

const MIN_YELLOW_DESCRIPTION_LENGTH = 20;

const FOCUSABLE_SELECTOR =
  'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])';

export const AcademicIntegrityModal: React.FC<AcademicIntegrityModalProps> = ({
  open,
  assignmentId,
  assignmentTitle,
  aiPolicyLevel,
  pledgeStatus,
  initialSelfContributionPct = 80,
  initialToolsUsed = [],
  initialUsageDescription = "",
  onCancel,
  onSigned,
}) => {
  const normalizedPolicy: AIPolicyLevel = useMemo(() => {
    const raw = (pledgeStatus?.ai_policy_level || aiPolicyLevel || "YELLOW").toUpperCase();
    if (raw === "GREEN" || raw === "RED") return raw;
    return "YELLOW";
  }, [pledgeStatus?.ai_policy_level, aiPolicyLevel]);

  const terms = useMemo(() => {
    if (pledgeStatus?.terms && pledgeStatus.terms.length > 0) {
      return pledgeStatus.terms;
    }
    return DEFAULT_TERMS;
  }, [pledgeStatus?.terms]);

  const [accepted, setAccepted] = useState(false);
  const [selfContributionPct, setSelfContributionPct] = useState(80);
  const [toolsUsed, setToolsUsed] = useState<string[]>([]);
  const [usageDescription, setUsageDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const trapContainerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    setAccepted(false);
    setErrorMessage(null);
    setSubmitting(false);

    if (normalizedPolicy === "RED") {
      setSelfContributionPct(100);
      setToolsUsed([]);
      setUsageDescription(RED_POLICY_AUTO_DESCRIPTION);
    } else {
      setSelfContributionPct(initialSelfContributionPct);
      setToolsUsed(initialToolsUsed);
      setUsageDescription(initialUsageDescription);
    }
  }, [
    open,
    normalizedPolicy,
    initialSelfContributionPct,
    initialToolsUsed,
    initialUsageDescription,
  ]);

  // Khóa tiêu điểm bàn phím (Focus-Trap) trong phạm vi hộp thoại cam kết
  useEffect(() => {
    if (!open) return;
    const container = trapContainerRef.current;
    if (!container) return;

    const focusables = container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
    if (focusables.length > 0) {
      focusables[0].focus();
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Tab") return;
      const items = container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey) {
        if (document.activeElement === first || !container.contains(document.activeElement)) {
          event.preventDefault();
          last.focus();
        }
      } else if (document.activeElement === last || !container.contains(document.activeElement)) {
        event.preventDefault();
        first.focus();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open]);

  const toggleTool = (toolId: string) => {
    if (normalizedPolicy === "RED") return;
    setToolsUsed((prev) =>
      prev.includes(toolId) ? prev.filter((id) => id !== toolId) : [...prev, toolId]
    );
  };

  const yellowDescriptionTooShort =
    normalizedPolicy === "YELLOW" &&
    toolsUsed.length > 0 &&
    usageDescription.trim().length < MIN_YELLOW_DESCRIPTION_LENGTH;

  const canConfirm = accepted && !yellowDescriptionTooShort && !submitting;

  const policyMeta = useMemo(() => {
    if (normalizedPolicy === "GREEN") {
      return {
        label: "Mức Xanh — Cho phép AI hỗ trợ kèm khai báo",
        badgeClass: "bg-mm-success-bg text-mm-success border-mm-success/30",
        description:
          "Bạn được phép sử dụng các công cụ AI để tra cứu, gợi ý và cải thiện bài làm. Vui lòng khai báo minh bạch bên dưới.",
        Icon: ShieldCheck,
      };
    }
    if (normalizedPolicy === "RED") {
      return {
        label: "Mức Đỏ — Cấm sử dụng AI tạo sinh",
        badgeClass: "bg-mm-danger-bg text-mm-danger border-mm-danger/30",
        description:
          "Bài tập này yêu cầu 100% sinh viên tự thực hiện, không sử dụng AI hỗ trợ sinh mã nguồn hoặc văn bản.",
        Icon: ShieldOff,
      };
    }
    return {
      label: "Mức Vàng — Giới hạn có kiểm soát",
      badgeClass: "bg-mm-warning-bg text-mm-warning border-mm-warning/30",
      description:
        "Chỉ sử dụng AI ở phạm vi cho phép. Nếu có dùng công cụ AI, bạn bắt buộc mô tả phương thức sử dụng tối thiểu 20 ký tự.",
      Icon: ShieldAlert,
    };
  }, [normalizedPolicy]);

  const PolicyIcon = policyMeta.Icon;

  const handleConfirm = async () => {
    if (!accepted) {
      setErrorMessage(
        resolveErrorMessage(
          "E-PLG-01",
          "E-PLG-01: Bạn phải tích xác nhận cam kết liêm chính học thuật trước khi tiếp tục."
        )
      );
      return;
    }

    if (yellowDescriptionTooShort) {
      setErrorMessage(
        "Mức Vàng yêu cầu mô tả giải trình cách sử dụng công cụ AI tối thiểu 20 ký tự."
      );
      return;
    }

    const effectiveSelfPct = normalizedPolicy === "RED" ? 100 : selfContributionPct;
    const effectiveTools = normalizedPolicy === "RED" ? [] : toolsUsed;
    const effectiveDesc =
      normalizedPolicy === "RED"
        ? RED_POLICY_AUTO_DESCRIPTION
        : usageDescription.trim();

    setSubmitting(true);
    setErrorMessage(null);
    try {
      const signed = await assessmentService.signIntegrityPledge(assignmentId, {
        accepted: true,
        self_contribution_pct: effectiveSelfPct,
        tools_used: effectiveTools,
        usage_description: effectiveDesc || null,
      });
      showToast(
        "success",
        "Đã ký xác nhận cam kết liêm chính học thuật. Vùng nộp bài đã được mở khóa."
      );
      onSigned({
        pledge: signed,
        selfContributionPct: effectiveSelfPct,
        toolsUsed: effectiveTools,
        usageDescription: effectiveDesc,
      });
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? resolveErrorMessage(err.code, err.message)
          : "Không thể lưu biên bản cam kết liêm chính học thuật. Vui lòng thử lại.";
      setErrorMessage(msg);
      showToast("error", msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <MmModal
      open={open}
      title="Cam kết Liêm chính Học thuật & Khai báo AI"
      subtitle={`Bắt buộc hoàn tất trước khi mở khóa khu vực tải tệp bài làm: ${assignmentTitle}`}
      maxWidthClass="max-w-2xl"
      closeOnBackdrop={false}
      closeOnEscape={false}
      showCloseButton={false}
      onClose={onCancel}
      footer={
        <div className="flex w-full flex-col-reverse items-stretch justify-between gap-3 sm:flex-row sm:items-center">
          <span className="font-mm-ui text-xs text-mm-text-muted">
            Phiên bản biên bản: {pledgeStatus?.pledge_version || "v1.0"} · Lưu vết bất biến
          </span>
          <div className="flex flex-wrap items-center justify-end gap-2.5">
            <MmButton variant="secondary" onClick={onCancel} disabled={submitting}>
              Hủy bỏ
            </MmButton>
            <div
              title={
                !accepted
                  ? "E-PLG-01: Bạn phải tích chọn ô xác nhận 3 điều khoản cam kết liêm chính học thuật để tiếp tục."
                  : yellowDescriptionTooShort
                    ? "Vui lòng nhập mô tả giải trình sử dụng AI tối thiểu 20 ký tự."
                    : undefined
              }
            >
              <MmButton
                variant="brand"
                loading={submitting}
                disabled={!canConfirm}
                onClick={() => void handleConfirm()}
              >
                <ShieldCheck className="h-4 w-4" />
                <span>Tôi cam đoan &amp; Tiếp tục nộp bài</span>
              </MmButton>
            </div>
          </div>
        </div>
      }
    >
      <div ref={trapContainerRef} className="space-y-5">
        {errorMessage && (
          <div
            role="alert"
            className="flex items-start gap-2.5 rounded-mm-panel border border-mm-danger/30 bg-mm-danger-bg px-4 py-3 text-mm-danger"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span className="font-mm-ui text-sm">{errorMessage}</span>
          </div>
        )}

        {/* Khối chính sách AI của bài tập */}
        <div
          className={clsx(
            "flex items-start gap-3 rounded-mm-card border p-4",
            policyMeta.badgeClass
          )}
        >
          <PolicyIcon className="mt-0.5 h-5 w-5 shrink-0" />
          <div className="space-y-1">
            <h3 className="font-mm-mid text-sm font-semibold">{policyMeta.label}</h3>
            <p className="font-mm-ui text-xs leading-relaxed opacity-90">
              {policyMeta.description}
            </p>
          </div>
        </div>

        {/* 3 Điều khoản liêm chính học thuật */}
        <section className="space-y-3 rounded-mm-card border border-mm-border bg-mm-bg p-5">
          <div className="flex items-center gap-2 border-b border-mm-divider pb-2.5">
            <Lock className="h-4 w-4 text-mm-blue-hover" />
            <h3 className="font-mm-display text-sm font-semibold text-mm-heading">
              Nội dung 3 điều khoản cam kết liêm chính học thuật
            </h3>
          </div>
          <ol className="space-y-2.5">
            {terms.map((term, index) => (
              <li
                key={term.code}
                className="flex items-start gap-3 rounded-mm-panel bg-mm-divider/35 px-3.5 py-2.5"
              >
                <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-mm-bg font-mm-data text-xs font-semibold text-mm-blue-deep">
                  {index + 1}
                </span>
                <p className="font-mm-ui text-xs leading-relaxed text-mm-heading">
                  {term.text}
                </p>
              </li>
            ))}
          </ol>
        </section>

        {/* Bảng khai báo AI thích ứng theo mức GREEN / YELLOW / RED */}
        <section className="space-y-4 rounded-mm-card border border-mm-border bg-mm-bg p-5">
          <div className="flex items-center gap-2 border-b border-mm-divider pb-2.5">
            <Bot className="h-4 w-4 text-mm-blue-hover" />
            <h3 className="font-mm-display text-sm font-semibold text-mm-heading">
              Khai báo mức độ sử dụng Trí tuệ nhân tạo (AI Disclosure)
            </h3>
          </div>

          {/* Thanh tỷ lệ tự thực hiện */}
          <div className="space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
              <span className="font-mm-ui font-medium text-mm-heading">
                Tỷ lệ tự thực hiện của bạn:
              </span>
              <span className="rounded-full bg-mm-blue-light/35 px-3 py-0.5 font-mm-data text-xs font-semibold text-mm-blue-deep">
                {selfContributionPct}% Tự làm ({100 - selfContributionPct}% AI hỗ trợ)
              </span>
            </div>
            <input
              type="range"
              aria-label="Tỷ lệ tự thực hiện"
              min={0}
              max={100}
              step={5}
              value={selfContributionPct}
              disabled={normalizedPolicy === "RED"}
              onChange={(e) => setSelfContributionPct(Number(e.target.value))}
              className={clsx(
                "h-2 w-full appearance-none rounded-lg bg-mm-divider accent-mm-blue-primary",
                normalizedPolicy === "RED"
                  ? "cursor-not-allowed opacity-60"
                  : "cursor-pointer"
              )}
            />
            {normalizedPolicy === "RED" ? (
              <p className="font-mm-ui text-xs text-mm-danger">
                Chính sách mức Đỏ khóa cố định tỷ lệ tự thực hiện ở 100% và không cho phép khai báo công cụ AI.
              </p>
            ) : (
              <div className="flex justify-between font-mm-data text-[11px] text-mm-text-muted">
                <span>0%</span>
                <span>50%</span>
                <span>100% Tự làm</span>
              </div>
            )}
          </div>

          {normalizedPolicy === "RED" ? (
            <div className="space-y-1.5">
              <label
                htmlFor="pledge-red-statement"
                className="block font-mm-ui text-xs font-medium text-mm-heading"
              >
                Xác nhận không sử dụng AI (tự động điền hợp lệ):
              </label>
              <textarea
                id="pledge-red-statement"
                rows={2}
                readOnly
                value={usageDescription}
                className="w-full cursor-not-allowed rounded-mm-btn border border-mm-border bg-mm-divider/40 p-3 font-mm-ui text-xs text-mm-text-secondary"
              />
            </div>
          ) : (
            <>
              <div className="space-y-2">
                <span className="block font-mm-ui text-xs font-medium text-mm-heading">
                  Các công cụ AI đã sử dụng (để trống nếu không dùng):
                </span>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {AI_TOOL_OPTIONS.map((tool) => {
                    const checked = toolsUsed.includes(tool.id);
                    return (
                      <button
                        key={tool.id}
                        type="button"
                        onClick={() => toggleTool(tool.id)}
                        className={clsx(
                          "flex items-center gap-2 rounded-mm-btn border px-3 py-2 text-left font-mm-ui text-xs transition-colors",
                          checked
                            ? "border-mm-blue-hover bg-mm-blue-light/30 font-medium text-mm-blue-deep"
                            : "border-mm-border bg-mm-bg text-mm-text-secondary hover:bg-mm-divider/40"
                        )}
                      >
                        <span
                          className={clsx(
                            "inline-flex h-4 w-4 shrink-0 items-center justify-center rounded border",
                            checked
                              ? "border-mm-blue-hover bg-mm-blue-hover text-white"
                              : "border-mm-border bg-mm-bg"
                          )}
                        >
                          {checked && <CheckCircle2 className="h-3 w-3" />}
                        </span>
                        <span>{tool.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between gap-2 text-xs">
                  <label
                    htmlFor="pledge-ai-description"
                    className="font-mm-ui font-medium text-mm-heading"
                  >
                    Mô tả phương thức sử dụng AI
                    {normalizedPolicy === "YELLOW" && toolsUsed.length > 0
                      ? " (Bắt buộc tối thiểu 20 ký tự)"
                      : " (Khuyến nghị tối thiểu 20 ký tự)"}
                  </label>
                  <span
                    className={clsx(
                      "font-mm-data text-[11px]",
                      yellowDescriptionTooShort ? "text-mm-danger" : "text-mm-text-muted"
                    )}
                  >
                    {usageDescription.trim().length} ký tự
                  </span>
                </div>
                <textarea
                  id="pledge-ai-description"
                  rows={3}
                  value={usageDescription}
                  onChange={(e) => {
                    setUsageDescription(e.target.value);
                    if (errorMessage) setErrorMessage(null);
                  }}
                  placeholder="Nêu rõ công đoạn bạn sử dụng AI hỗ trợ, cách kiểm chứng và phần nội dung do bạn tự triển khai..."
                  className={clsx(
                    "w-full rounded-mm-btn border bg-mm-bg p-3 font-mm-ui text-xs text-mm-heading focus:outline-none focus:ring-2 focus:ring-mm-blue-hover/25",
                    yellowDescriptionTooShort ? "border-mm-danger" : "border-mm-border"
                  )}
                />
                {yellowDescriptionTooShort && (
                  <p className="font-mm-ui text-xs text-mm-danger">
                    E-PLG-01: Khi sử dụng công cụ AI ở mức Vàng, cần mô tả ít nhất 20 ký tự.
                  </p>
                )}
              </div>
            </>
          )}
        </section>

        {/* Checkbox xác nhận cam kết bắt buộc kèm gợi ý E-PLG-01 */}
        <div className="space-y-2 rounded-mm-card border border-mm-border bg-mm-divider/30 p-4">
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={accepted}
              onChange={(e) => {
                setAccepted(e.target.checked);
                if (e.target.checked && errorMessage) setErrorMessage(null);
              }}
              className="mt-0.5 h-4 w-4 rounded border-mm-border text-mm-blue-hover focus:ring-mm-blue-hover/30"
            />
            <span className="font-mm-ui text-xs leading-relaxed text-mm-heading">
              Tôi đã đọc kỹ 3 điều khoản nêu trên, xác nhận khai báo sử dụng AI là hoàn toàn trung thực và đồng ý lưu vết biên bản cam kết điện tử này (BR-11 / BR-PLG-02).
            </span>
          </label>
          {!accepted && (
            <p className="pl-7 font-mm-ui text-xs text-mm-warning">
              E-PLG-01: Vui lòng tích chọn xác nhận cam kết để kích hoạt nút tiếp tục nộp bài.
            </p>
          )}
        </div>
      </div>
    </MmModal>
  );
};
