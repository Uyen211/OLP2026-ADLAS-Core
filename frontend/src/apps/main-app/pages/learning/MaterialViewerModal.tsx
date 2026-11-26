/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useCallback, useEffect, useState } from "react";
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
import type {
  LearningMaterial,
  MaterialCheckpoint,
  MaterialStructuredContent,
  MaterialType,
} from "../../../../types/learning";
import { BloomBadge } from "../../components/BloomBadge";
import { MmButton } from "../../components/MmButton";
import { showToast } from "../../components/Toast";
import { DocumentCheckpointsPanel } from "./DocumentCheckpointsPanel";
import { DocumentFilmstripTrack } from "./DocumentFilmstripTrack";
import { DocumentSectionsStage } from "./DocumentSectionsStage";
import { InteractiveVideoPlayer } from "./InteractiveVideoPlayer";
import { SlidePdfStage } from "./SlidePdfStage";

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
  const [checkpoints, setCheckpoints] = useState<MaterialCheckpoint[]>([]);
  const [structuredContent, setStructuredContent] = useState<MaterialStructuredContent | null>(null);
  const [currentPageIndex, setCurrentPageIndex] = useState(1);
  const [isCompleted, setIsCompleted] = useState(false);
  const [completing, setCompleting] = useState(false);

  const isExternalUrl = Boolean(
    material?.file_url &&
      (material.file_url.startsWith("http://") || material.file_url.startsWith("https://"))
  );

  const handleCheckpointPassed = useCallback((checkpointId: string) => {
    setCheckpoints((prev) =>
      prev.map((c) => (c.id === checkpointId ? { ...c, is_passed: true } : c))
    );
  }, []);

  const handleCompleteMaterial = useCallback(async () => {
    if (!material || completing || isCompleted) return;
    setCompleting(true);
    try {
      await learningService.completeMaterial(courseId, material.id);
      setIsCompleted(true);
      showToast("success", "Chúc mừng! Bạn đã hoàn thành học liệu này.");
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Chưa thể hoàn thành học liệu."
      );
    } finally {
      setCompleting(false);
    }
  }, [courseId, material, completing, isCompleted]);

  useEffect(() => {
    if (!open || !material) {
      return;
    }

    setIsCompleted(false);
    setCheckpoints([]);
    setStructuredContent(null);
    setCurrentPageIndex(1);
    learningService
      .listCheckpoints(courseId, material.id)
      .then((list) => setCheckpoints(list))
      .catch(() => setCheckpoints([]));

    if (!material.file_url) {
      return;
    }

    if (isExternalUrl) {
      setLoading(false);
      setError(null);
      setObjectUrl(null);
      setTextContent(null);
      return;
    }

    let cancelled = false;
    let createdUrl: string | null = null;
    const isVideoMat =
      material.material_type === "VIDEO" ||
      material.file_url.toLowerCase().endsWith(".mp4") ||
      material.file_url.toLowerCase().endsWith(".webm");

    const loadPreview = async () => {
      setLoading(true);
      setError(null);
      setObjectUrl(null);
      setTextContent(null);
      try {
        if (!isVideoMat) {
          const structured = await learningService.getMaterialStructuredContent(
            courseId,
            material.id
          );
          if (cancelled) return;
          if (structured.content_kind !== "UNSUPPORTED" && structured.items.length > 0) {
            setStructuredContent(structured);
            return;
          }
        }

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

  const unpassedBlockingSections = checkpoints
    .filter((c) => c.is_blocking && !c.is_passed)
    .map((c) => c.section_index ?? 1);
  const lockedFromIndex =
    unpassedBlockingSections.length > 0 ? Math.min(...unpassedBlockingSections) : undefined;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="flex max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-slate-100 bg-white px-6 py-4">
          <div className="flex items-start gap-3.5">
            <div className="mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-blue-100 bg-blue-50 text-blue-600 shadow-xs">
              {MATERIAL_ICON[material.material_type] || <FileText className="h-5 w-5" />}
            </div>
            <div>
              <h3 className="font-display text-base font-bold text-slate-900">
                {material.title}
              </h3>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                <span className="rounded-full bg-slate-100 px-2.5 py-0.5 font-semibold text-slate-700 border border-slate-200">
                  {material.material_type}
                </span>
                <span className="flex items-center gap-1 font-medium">
                  <Clock className="h-3.5 w-3.5 text-slate-400" />
                  {material.est_duration_minutes} phút
                </span>
                {matchingLo && (
                  <span className="flex items-center gap-1.5">
                    <span className="font-mono font-bold text-blue-600">
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
            className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
            aria-label="Đóng trình xem"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto bg-slate-50/80 p-6">
          {!fileUrl ? (
            <div className="flex flex-col items-center justify-center py-16 text-center text-sm text-slate-500">
              <FileText className="mb-2 h-10 w-10 opacity-40 text-slate-400" />
              <p>Học liệu này chưa có tệp đính kèm hoặc liên kết.</p>
            </div>
          ) : loading ? (
            <div className="flex flex-col items-center justify-center py-20 text-sm text-slate-500">
              <Loader2 className="mb-3 h-8 w-8 animate-spin text-blue-600" />
              <p>Đang tải nội dung học liệu...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-rose-200 bg-rose-50 p-8 text-center">
              <AlertCircle className="h-9 w-9 text-rose-600" />
              <p className="text-sm font-medium text-slate-900">{error}</p>
              <MmButton variant="secondary" size="sm" onClick={() => onDownload(material)}>
                <Download className="h-4 w-4" />
                <span>Thử tải về tệp gốc</span>
              </MmButton>
            </div>
          ) : isVideo && (isExternalUrl ? !youtubeEmbed : Boolean(objectUrl)) ? (
            <InteractiveVideoPlayer
              courseId={courseId}
              src={isExternalUrl ? fileUrl : objectUrl!}
              checkpoints={checkpoints}
              isCompleted={isCompleted}
              onCheckpointPassed={handleCheckpointPassed}
              onReadyToComplete={handleCompleteMaterial}
            />
          ) : (
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
              <div className="lg:col-span-7">
                {isExternalUrl ? (
                  youtubeEmbed ? (
                    <div className="aspect-video w-full overflow-hidden rounded-2xl border border-slate-800 bg-black shadow-lg">
                      <iframe
                        src={youtubeEmbed}
                        title={material.title}
                        className="h-full w-full"
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                        allowFullScreen
                      />
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-slate-200 bg-white p-10 text-center shadow-sm">
                      <ExternalLink className="h-10 w-10 text-blue-600" />
                      <div>
                        <p className="font-bold text-slate-900">Học liệu liên kết trực tuyến</p>
                        <p className="mt-1 break-all text-xs text-slate-500">{fileUrl}</p>
                      </div>
                      <a
                        href={fileUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90 shadow-sm"
                      >
                        <ExternalLink className="h-4 w-4" />
                        <span>Mở liên kết trong tab mới</span>
                      </a>
                    </div>
                  )
                ) : structuredContent &&
                  (structuredContent.content_kind === "PDF_PAGES" ||
                    structuredContent.content_kind === "SLIDE_DECK") ? (
                  <div className="space-y-3">
                    <SlidePdfStage
                      courseId={courseId}
                      materialId={material.id}
                      contentKind={structuredContent.content_kind}
                      items={structuredContent.items}
                      currentIndex={currentPageIndex}
                      lockedFromIndex={lockedFromIndex}
                      onChangeIndex={setCurrentPageIndex}
                    />
                    <DocumentFilmstripTrack
                      items={structuredContent.items}
                      currentIndex={currentPageIndex}
                      checkpoints={checkpoints}
                      lockedFromIndex={lockedFromIndex}
                      onSelectIndex={setCurrentPageIndex}
                    />
                  </div>
                ) : structuredContent && structuredContent.content_kind === "DOC_SECTIONS" ? (
                  <div className="max-h-[65vh] overflow-y-auto pr-1">
                    <DocumentSectionsStage
                      items={structuredContent.items}
                      checkpoints={checkpoints}
                      lockedFromIndex={lockedFromIndex}
                    />
                  </div>
                ) : textContent !== null ? (
                  <div className="max-h-[65vh] overflow-y-auto rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                    <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-800">
                      {textContent}
                    </pre>
                  </div>
                ) : isPdf && objectUrl ? (
                  <iframe
                    src={objectUrl}
                    title={material.title}
                    className="h-[65vh] w-full rounded-xl border border-slate-200 bg-white shadow-sm"
                  />
                ) : isOfficeDoc ? (
                  <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-slate-200 bg-white p-12 text-center shadow-sm">
                    {MATERIAL_ICON[material.material_type]}
                    <div className="max-w-md space-y-1.5">
                      <h4 className="font-bold text-slate-900">
                        Tài liệu định dạng Office ({lowerUrl.split(".").pop()?.toUpperCase()})
                      </h4>
                      <p className="text-sm text-slate-500">
                        Trình duyệt không hỗ trợ hiển thị trực tiếp tệp PowerPoint/Word. Vui lòng tải về để mở bằng Microsoft Office hoặc LibreOffice.
                      </p>
                    </div>
                    <MmButton variant="brand" size="md" onClick={() => onDownload(material)}>
                      <Download className="h-4 w-4" />
                      <span>Tải về tệp gốc</span>
                    </MmButton>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center gap-3 py-14 text-center text-sm text-slate-500">
                    <p>Định dạng tệp này không hỗ trợ xem trước trực tiếp.</p>
                    <MmButton variant="brand" size="sm" onClick={() => onDownload(material)}>
                      <Download className="h-4 w-4" />
                      <span>Tải về tệp gốc</span>
                    </MmButton>
                  </div>
                )}
              </div>

              <div className="lg:col-span-5">
                <div className="max-h-[65vh] overflow-y-auto">
                  <DocumentCheckpointsPanel
                    courseId={courseId}
                    checkpoints={checkpoints}
                    isCompleted={isCompleted}
                    completing={completing}
                    onCheckpointPassed={handleCheckpointPassed}
                    onCompleteMaterial={handleCompleteMaterial}
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-100 bg-white px-6 py-3.5">
          <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            <span>{isExternalUrl ? "Liên kết ngoài" : "Lưu trữ nội bộ ADLAS"}</span>
          </div>
          <div className="flex items-center gap-2.5">
            {fileUrl && !isExternalUrl && (
              <MmButton variant="brand" size="sm" onClick={() => onDownload(material)}>
                <Download className="h-4 w-4" />
                <span>Tải về tệp gốc</span>
              </MmButton>
            )}
            <MmButton variant="secondary" size="sm" onClick={onClose}>
              Đóng
            </MmButton>
          </div>
        </div>
      </div>
    </div>
  );
};
