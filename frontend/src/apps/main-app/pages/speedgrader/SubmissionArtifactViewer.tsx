/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useState } from "react";
import {
  Bot,
  Download,
  FileCode2,
  FileText,
  GitBranch,
  GitCompare,
  History,
  MessageSquare,
} from "lucide-react";
import { clsx } from "clsx";

import { gradebookService } from "../../../../services/gradebookService";
import type {
  SpeedGraderWorkspaceResponse,
  VersionDiffResponse,
} from "../../../../types/gradebook";
import { MmButton } from "../../components/MmButton";
import { toast } from "../../components/Toast";
import { resolveErrorMessage } from "../../constants/errorMessages";

interface SubmissionArtifactViewerProps {
  workspace: SpeedGraderWorkspaceResponse;
  highlightedRef: string | null;
  onSelectVersion: (submissionId: string) => void;
}

export const SubmissionArtifactViewer: React.FC<SubmissionArtifactViewerProps> = ({
  workspace,
  highlightedRef,
  onSelectVersion,
}) => {
  const [previewText, setPreviewText] = useState<string>("");
  const [loadingPreview, setLoadingPreview] = useState<boolean>(false);
  const [viewMode, setViewMode] = useState<"preview" | "diff">("preview");
  const [diffData, setDiffData] = useState<VersionDiffResponse | null>(null);
  const [loadingDiff, setLoadingDiff] = useState<boolean>(false);
  const [downloading, setDownloading] = useState<boolean>(false);

  useEffect(() => {
    let active = true;
    setViewMode("preview");
    setDiffData(null);
    const loadPreview = async () => {
      setLoadingPreview(true);
      try {
        const res = await gradebookService.getSubmissionPreview(workspace.submission_id);
        if (active) {
          setPreviewText(res.preview_text || "");
        }
      } catch {
        if (active) {
          setPreviewText("");
        }
      } finally {
        if (active) setLoadingPreview(false);
      }
    };
    void loadPreview();
    return () => {
      active = false;
    };
  }, [workspace.submission_id]);

  const handleLoadDiff = async () => {
    setViewMode("diff");
    if (diffData) return;
    setLoadingDiff(true);
    try {
      const res = await gradebookService.getVersionsDiff(workspace.submission_id);
      setDiffData(res);
    } catch (err: any) {
      toast.error(resolveErrorMessage(err?.code, "Không thể tính khác biệt giữa các phiên bản."));
    } finally {
      setLoadingDiff(false);
    }
  };

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const fallbackName = `submission-v${workspace.version}-${workspace.student_code || "student"}.bin`;
      const rawUrl = workspace.file_url || "";
      const filename = rawUrl.split("/").pop() || fallbackName;
      await gradebookService.downloadSubmissionFile(workspace.submission_id, filename);
    } catch (err: any) {
      toast.error(resolveErrorMessage(err?.code, "Không thể tải tệp bài nộp."));
    } finally {
      setDownloading(false);
    }
  };

  const hasMultipleVersions = workspace.versions.length >= 2;

  return (
    <div className="flex h-full flex-col rounded-2xl border border-[#e5e7eb] bg-white shadow-xs">
      {/* Column Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#f3f4f6] px-4 py-3">
        <div className="flex items-center gap-2">
          <FileCode2 className="h-4 w-4 text-mm-blue-primary" />
          <h2 className="font-mm-display text-sm font-bold text-mm-dark">
            1. Sản phẩm bài nộp
          </h2>
        </div>

        <div className="flex items-center gap-1.5">
          {workspace.versions.length > 0 && (
            <div className="flex items-center gap-1 rounded-lg border border-[#e5e7eb] bg-[#f9fafb] px-2 py-1 text-[11px]">
              <History className="h-3 w-3 text-[#6b7280]" />
              <select
                value={workspace.submission_id}
                onChange={(e) => onSelectVersion(e.target.value)}
                className="bg-transparent font-mm-mono text-[11px] font-semibold text-mm-dark focus:outline-none"
                aria-label="Chọn phiên bản bài nộp"
              >
                {workspace.versions.map((ver) => (
                  <option key={ver.submission_id} value={ver.submission_id}>
                    v{ver.version} ({new Date(ver.submitted_at).toLocaleDateString("vi-VN")})
                  </option>
                ))}
              </select>
            </div>
          )}

          {hasMultipleVersions && (
            <button
              type="button"
              onClick={() => (viewMode === "diff" ? setViewMode("preview") : void handleLoadDiff())}
              className={clsx(
                "inline-flex items-center gap-1 rounded-lg border px-2.5 py-1 text-[11px] font-medium transition-colors",
                viewMode === "diff"
                  ? "border-mm-blue-primary bg-[#eff6ff] text-mm-blue-primary"
                  : "border-[#e5e7eb] bg-white text-[#374151] hover:bg-[#f9fafb]"
              )}
            >
              <GitCompare className="h-3 w-3" />
              {viewMode === "diff" ? "Xem nội dung" : "So sánh phiên bản"}
            </button>
          )}

          {workspace.file_url && (
            <MmButton
              variant="secondary"
              size="sm"
              onClick={() => void handleDownload()}
              disabled={downloading}
              title="Tải xuống bài nộp gốc"
            >
              <Download className="h-3.5 w-3.5" />
            </MmButton>
          )}
        </div>
      </div>

      {/* Scrollable Body */}
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {/* Submission Metadata */}
        <div className="rounded-xl border border-[#e5e7eb] bg-[#f9fafb] p-3 text-xs space-y-1.5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-semibold text-mm-dark">
              {workspace.project_title || workspace.assignment_title}
            </span>
            <span
              className={clsx(
                "rounded-full px-2 py-0.5 text-[10px] font-semibold",
                workspace.is_late
                  ? "bg-rose-50 text-rose-700"
                  : "bg-[#ecfdf5] text-[#047857]"
              )}
            >
              {workspace.is_late
                ? `Trễ hạn (-${workspace.late_penalty_applied}%)`
                : "Đúng hạn"}
            </span>
          </div>
          <p className="font-mm-mono text-[11px] text-[#6b7280]">
            v{workspace.version} · Nộp lúc {new Date(workspace.submitted_at).toLocaleString("vi-VN")}
          </p>
          {workspace.git_repo_url ? (
            <div className="flex items-center gap-1.5 truncate">
              <GitBranch className="h-3.5 w-3.5 shrink-0 text-mm-blue-primary" />
              <a
                href={workspace.git_repo_url}
                target="_blank"
                rel="noreferrer"
                className="truncate font-mm-mono text-mm-blue-primary hover:underline"
              >
                {workspace.git_repo_url}
              </a>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 truncate text-[#4b5563]">
              <FileText className="h-3.5 w-3.5 shrink-0 text-mm-blue-primary" />
              <span className="truncate font-mm-mono">
                {workspace.file_url || "Không có tệp đính kèm"}
              </span>
            </div>
          )}
        </div>

        {/* AI Disclosure Summary */}
        <div className="rounded-xl border border-[#dbeafe] bg-[#eff6ff]/60 p-3 text-xs space-y-1">
          <div className="flex items-center justify-between">
            <span className="inline-flex items-center gap-1.5 font-semibold text-[#1e3a8a]">
              <Bot className="h-3.5 w-3.5" />
              Khai báo AI (Tự thực hiện: {workspace.self_contribution_pct}%)
            </span>
          </div>
          <p className="text-[#1e40af]">
            Công cụ:{" "}
            <span className="font-medium">
              {workspace.ai_disclosure_data?.tools_used?.length
                ? workspace.ai_disclosure_data.tools_used.join(", ")
                : "Không sử dụng AI"}
            </span>
          </p>
          {workspace.ai_disclosure_data?.usage_description && (
            <p className="text-[#374151]">{workspace.ai_disclosure_data.usage_description}</p>
          )}
        </div>

        {workspace.comments && (
          <div className="rounded-xl border border-[#e5e7eb] bg-white p-3 text-xs">
            <div className="mb-1 flex items-center gap-1.5 font-semibold text-mm-dark">
              <MessageSquare className="h-3.5 w-3.5 text-[#6b7280]" />
              Ghi chú của sinh viên
            </div>
            <p className="whitespace-pre-wrap text-[#374151]">{workspace.comments}</p>
          </div>
        )}

        {/* Highlight Banner when instructor clicks citation */}
        {highlightedRef && (
          <div className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
            Đang đối chiếu trích dẫn: <strong className="font-mm-mono">{highlightedRef}</strong>
          </div>
        )}

        {/* Main Viewer: Preview or Version Diff */}
        {viewMode === "diff" ? (
          <div className="rounded-xl border border-[#e5e7eb] bg-[#0f172a] text-xs text-slate-100">
            <div className="flex items-center justify-between border-b border-slate-700 px-3 py-2 text-[11px] font-mm-mono text-slate-300">
              <span>
                {diffData
                  ? `So sánh v${diffData.v1_version} -> v${diffData.v2_version}`
                  : "Đang so sánh phiên bản..."}
              </span>
              {diffData && <span>{diffData.summary}</span>}
            </div>
            {loadingDiff ? (
              <div className="p-6 text-center text-slate-400">Đang tính khác biệt...</div>
            ) : diffData && diffData.lines.length > 0 ? (
              <pre className="max-h-[420px] overflow-auto p-3 font-mm-mono text-[11px] leading-relaxed">
                {diffData.lines.map((line, idx) => (
                  <div
                    key={idx}
                    className={clsx(
                      "px-2 py-0.5",
                      line.line_type === "added" && "bg-emerald-950/80 text-emerald-300",
                      line.line_type === "removed" && "bg-rose-950/80 text-rose-300",
                      line.line_type === "context" && "text-slate-300"
                    )}
                  >
                    <span className="mr-2 inline-block w-3 select-none opacity-70">
                      {line.line_type === "added"
                        ? "+"
                        : line.line_type === "removed"
                          ? "-"
                          : " "}
                    </span>
                    {line.content}
                  </div>
                ))}
              </pre>
            ) : (
              <div className="p-4 text-center text-slate-400">
                Không có thay đổi văn bản nào giữa hai phiên bản.
              </div>
            )}
          </div>
        ) : (
          <div className="rounded-xl border border-[#e5e7eb] bg-[#fafafa]">
            <div className="border-b border-[#e5e7eb] px-3 py-2 text-[11px] font-semibold text-[#4b5563]">
              Xem trước nội dung bài nộp
            </div>
            {loadingPreview ? (
              <div className="p-6 text-center text-xs text-[#6b7280]">
                Đang trích xuất nội dung xem trước...
              </div>
            ) : previewText ? (
              <pre className="max-h-[440px] overflow-auto whitespace-pre-wrap p-3 font-mm-mono text-[11px] leading-relaxed text-[#1f2937]">
                {previewText}
              </pre>
            ) : (
              <div className="p-6 text-center text-xs text-[#6b7280]">
                Không thể hiển thị trực tiếp định dạng tệp này. Vui lòng sử dụng nút tải xuống phía trên hoặc đối chiếu qua bản tóm tắt AI ở cột giữa.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
