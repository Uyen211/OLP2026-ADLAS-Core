/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  Clock,
  Download,
  ExternalLink,
  FileText,
  Film,
  Loader2,
  Presentation,
  X,
} from "lucide-react";
import { learningService } from "../../../../services/learningService";
import { ApiError } from "../../../../services/httpClient";
import type { LOResponse } from "../../../../types/course";
import type { LearningMaterial, MaterialType } from "../../../../types/learning";
import { BloomBadge } from "../../components/BloomBadge";
import { MmButton } from "../../components/MmButton";

export interface MaterialViewerModalProps {
  open: boolean;
  courseId: string;
  material: LearningMaterial | null;
  matchingLo?: LOResponse;
  onClose: () => void;
  onDownload: (material: LearningMaterial) => void;
}

const MATERIAL_ICON: Record<MaterialType, React.ReactNode> = {
  SLIDE: <Presentation className="h-5 w-5 text-orange-500" />,
  PDF: <FileText className="h-5 w-5 text-red-500" />,
  VIDEO: <Film className="h-5 w-5 text-blue-500" />,
  DOCUMENT: <FileText className="h-5 w-5 text-emerald-500" />,
};

function toYoutubeEmbedUrl(rawUrl: string): string | null {
  try {
    const parsed = new URL(rawUrl);
    if (parsed.hostname.includes("youtube.com")) {
      const videoId = parsed.searchParams.get("v");
      if (videoId) return `https://www.youtube.com/embed/${videoId}`;
      if (parsed.pathname.startsWith("/embed/")) return rawUrl;
    }
    if (parsed.hostname === "youtu.be") {
      const videoId = parsed.pathname.replace("/", "");
      if (videoId) return `https://www.youtube.com/embed/${videoId}`;
    }
  } catch {
    return null;
  }
  return null;
}

export const MaterialViewerModal: React.FC<MaterialViewerModalProps> = ({
  open,
  courseId,
  material,
  matchingLo,
  onClose,
  onDownload,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [contentType, setContentType] = useState<string>("");

  const isExternalUrl = Boolean(
    material?.file_url &&
      (material.file_url.startsWith("http://") || material.file_url.startsWith("https://"))
  );

  useEffect(() => {
    if (!open || !material || !material.file_url) {
      return;
    }

    // Record completion progress in background (unlocks prerequisite modules for students)
    learningService.completeMaterial(courseId, material.id).catch(() => {});

    if (isExternalUrl) {
      setLoading(false);
      setError(null);
      setObjectUrl(null);
      setTextContent(null);
      return;
    }

    let cancelled = false;
    let createdUrl: string | null = null;

    const loadPreview = async () => {
      setLoading(true);
      setError(null);
      setObjectUrl(null);
      setTextContent(null);
      try {
        const { blob, contentType: mime } = await learningService.fetchMaterialPreviewBlob(
          courseId,
          material.id
        );
        if (cancelled) return;
        setContentType(mime.toLowerCase());

        const lowerUrl = (material.file_url || "").toLowerCase();
        if (
          mime.includes("text/") ||
          mime.includes("markdown") ||
          lowerUrl.endsWith(".md") ||
          lowerUrl.endsWith(".txt")
        ) {
          const text = await blob.text();
          if (!cancelled) {
            setTextContent(text);
          }
        } else {
          createdUrl = URL.createObjectURL(blob);
          setObjectUrl(createdUrl);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Không thể tải nội dung xem trước.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadPreview();

    return () => {
      cancelled = true;
      if (createdUrl) {
        URL.revokeObjectURL(createdUrl);
      }
    };
  }, [open, courseId, material, isExternalUrl]);

  if (!open || !material) return null;

  const fileUrl = material.file_url || "";
  const lowerUrl = fileUrl.toLowerCase();
  const youtubeEmbed = isExternalUrl ? toYoutubeEmbedUrl(fileUrl) : null;
  const isPdf = contentType.includes("pdf") || lowerUrl.endsWith(".pdf");
  const isVideo =
    contentType.startsWith("video/") ||
    lowerUrl.endsWith(".mp4") ||
    lowerUrl.endsWith(".webm");
  const isOfficeDoc =
    lowerUrl.endsWith(".pptx") ||
    lowerUrl.endsWith(".ppt") ||
    lowerUrl.endsWith(".docx") ||
    lowerUrl.endsWith(".doc");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-mm border border-mm-border bg-mm-surface shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-mm-divider bg-mm-surface-alt/40 px-5 py-4">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-mm border border-mm-divider bg-mm-surface">
              {MATERIAL_ICON[material.material_type] || <FileText className="h-5 w-5" />}
            </div>
            <div>
              <h3 className="font-mm-mid text-base font-semibold text-mm-heading">
                {material.title}
              </h3>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-mm-text-muted">
                <span className="rounded bg-mm-surface-alt px-2 py-0.5 font-medium border border-mm-divider">
                  {material.material_type}
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  {material.est_duration_minutes} phút
                </span>
                {matchingLo && (
                  <span className="flex items-center gap-1.5">
                    <span className="font-mm-mono font-semibold text-mm-primary">
                      {matchingLo.code}
                    </span>
                    <BloomBadge level={matchingLo.bloom_level} />
                  </span>
                )}
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="rounded-mm p-1.5 text-mm-text-muted transition-colors hover:bg-mm-surface-alt hover:text-mm-heading"
            aria-label="Đóng trình xem"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto bg-mm-bg/50 p-5">
          {!fileUrl ? (
            <div className="flex flex-col items-center justify-center py-16 text-center text-sm text-mm-text-muted">
              <FileText className="mb-2 h-10 w-10 opacity-40" />
              <p>Học liệu này chưa có tệp đính kèm hoặc liên kết.</p>
            </div>
          ) : loading ? (
            <div className="flex flex-col items-center justify-center py-20 text-sm text-mm-text-muted">
              <Loader2 className="mb-3 h-8 w-8 animate-spin text-mm-brand" />
              <p>Đang tải nội dung học liệu...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center gap-3 rounded-mm border border-mm-error/30 bg-mm-error-bg/40 p-8 text-center">
              <AlertCircle className="h-9 w-9 text-mm-error" />
              <p className="text-sm font-medium text-mm-heading">{error}</p>
              <MmButton variant="secondary" size="sm" onClick={() => onDownload(material)}>
                <Download className="h-4 w-4" />
                <span>Thử tải về tệp gốc</span>
              </MmButton>
            </div>
          ) : isExternalUrl ? (
            youtubeEmbed ? (
              <div className="aspect-video w-full overflow-hidden rounded-mm border border-mm-divider bg-black">
                <iframe
                  src={youtubeEmbed}
                  title={material.title}
                  className="h-full w-full"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              </div>
            ) : isVideo ? (
              <video
                controls
                className="max-h-[66vh] w-full rounded-mm border border-mm-divider bg-black"
                src={fileUrl}
              />
            ) : (
              <div className="flex flex-col items-center justify-center gap-4 rounded-mm border border-mm-divider bg-mm-surface p-10 text-center">
                <ExternalLink className="h-10 w-10 text-mm-brand" />
                <div>
                  <p className="font-medium text-mm-heading">Học liệu liên kết trực tuyến</p>
                  <p className="mt-1 break-all text-xs text-mm-text-muted">{fileUrl}</p>
                </div>
                <a
                  href={fileUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 rounded-mm bg-mm-brand px-4 py-2 text-sm font-medium text-white hover:opacity-90"
                >
                  <ExternalLink className="h-4 w-4" />
                  <span>Mở liên kết trong tab mới</span>
                </a>
              </div>
            )
          ) : textContent !== null ? (
            <div className="rounded-mm border border-mm-divider bg-mm-surface p-6">
              <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-mm-text">
                {textContent}
              </pre>
            </div>
          ) : isPdf && objectUrl ? (
            <iframe
              src={objectUrl}
              title={material.title}
              className="h-[68vh] w-full rounded-mm border border-mm-divider bg-white"
            />
          ) : isVideo && objectUrl ? (
            <video
              controls
              className="max-h-[68vh] w-full rounded-mm border border-mm-divider bg-black"
              src={objectUrl}
            />
          ) : isOfficeDoc ? (
            <div className="flex flex-col items-center justify-center gap-4 rounded-mm border border-mm-divider bg-mm-surface p-12 text-center">
              {MATERIAL_ICON[material.material_type]}
              <div className="max-w-md space-y-1.5">
                <h4 className="font-medium text-mm-heading">
                  Tài liệu định dạng Office ({lowerUrl.split(".").pop()?.toUpperCase()})
                </h4>
                <p className="text-sm text-mm-text-muted">
                  Trình duyệt không hỗ trợ hiển thị trực tiếp tệp PowerPoint/Word. Vui lòng tải về để mở bằng Microsoft Office hoặc LibreOffice.
                </p>
              </div>
              <MmButton variant="primary" size="md" onClick={() => onDownload(material)}>
                <Download className="h-4 w-4" />
                <span>Tải về tệp gốc</span>
              </MmButton>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center gap-3 py-14 text-center text-sm text-mm-text-muted">
              <p>Định dạng tệp này không hỗ trợ xem trước trực tiếp.</p>
              <MmButton variant="primary" size="sm" onClick={() => onDownload(material)}>
                <Download className="h-4 w-4" />
                <span>Tải về tệp gốc</span>
              </MmButton>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-mm-divider bg-mm-surface px-5 py-3">
          <span className="text-xs text-mm-text-muted">
            {isExternalUrl ? "Liên kết ngoài" : "Lưu trữ nội bộ ADLAS"}
          </span>
          <div className="flex items-center gap-2">
            {fileUrl && !isExternalUrl && (
              <MmButton variant="secondary" size="sm" onClick={() => onDownload(material)}>
                <Download className="h-4 w-4" />
                <span>Tải về tệp gốc</span>
              </MmButton>
            )}
            <MmButton variant="primary" size="sm" onClick={onClose}>
              Đóng
            </MmButton>
          </div>
        </div>
      </div>
    </div>
  );
};
