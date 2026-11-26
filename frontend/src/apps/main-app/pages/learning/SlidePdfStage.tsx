/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, FileText, Loader2, Lock, Presentation } from "lucide-react";
import { learningService } from "../../../../services/learningService";
import type { MaterialPageItem } from "../../../../types/learning";

export interface SlidePdfStageProps {
  courseId: string;
  materialId: string;
  contentKind: "PDF_PAGES" | "SLIDE_DECK";
  items: MaterialPageItem[];
  currentIndex: number;
  lockedFromIndex?: number; // Student gate: pages > lockedFromIndex are locked
  onChangeIndex: (newIndex: number) => void;
}

export const SlidePdfStage: React.FC<SlidePdfStageProps> = ({
  courseId,
  materialId,
  contentKind,
  items,
  currentIndex,
  lockedFromIndex,
  onChangeIndex,
}) => {
  const [pageImgUrl, setPageImgUrl] = useState<string | null>(null);
  const [imgLoading, setImgLoading] = useState(false);

  const currentItem = items.find((i) => i.index === currentIndex) || items[0];
  const total = items.length;
  const isCurrentLocked =
    lockedFromIndex !== undefined && currentIndex > lockedFromIndex;

  useEffect(() => {
    if (contentKind !== "PDF_PAGES" || !currentItem || isCurrentLocked) {
      setPageImgUrl(null);
      return;
    }

    let cancelled = false;
    let objUrl: string | null = null;
    setImgLoading(true);

    learningService
      .fetchPageImageBlob(courseId, materialId, currentItem.index)
      .then(({ blob }) => {
        if (cancelled) return;
        objUrl = URL.createObjectURL(blob);
        setPageImgUrl(objUrl);
      })
      .catch(() => {
        if (!cancelled) setPageImgUrl(null);
      })
      .finally(() => {
        if (!cancelled) setImgLoading(false);
      });

    return () => {
      cancelled = true;
      if (objUrl) URL.revokeObjectURL(objUrl);
    };
  }, [courseId, materialId, contentKind, currentItem?.index, isCurrentLocked]);

  if (!currentItem) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-slate-800 bg-slate-950 text-sm text-slate-400">
        Không có trang hoặc slide nào để hiển thị.
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      {/* Main Presentation / Page Viewport */}
      <div className="relative flex min-h-[340px] w-full flex-col justify-between overflow-hidden rounded-xl border border-slate-700 bg-slate-950 shadow-lg">
        {/* Top Toolbar */}
        <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/90 px-4 py-2 text-xs text-slate-300">
          <span className="inline-flex items-center gap-1.5 font-semibold">
            {contentKind === "PDF_PAGES" ? (
              <FileText className="h-3.5 w-3.5 text-rose-400" />
            ) : (
              <Presentation className="h-3.5 w-3.5 text-amber-400" />
            )}
            <span>
              {contentKind === "PDF_PAGES" ? "Trang PDF" : "Slide"} {currentItem.index} / {total}
            </span>
          </span>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              disabled={currentItem.index <= 1}
              onClick={() => onChangeIndex(Math.max(1, currentItem.index - 1))}
              className="inline-flex items-center gap-1 rounded-md border border-slate-700 bg-slate-800 px-2.5 py-1 font-medium text-white transition-colors hover:bg-slate-700 disabled:opacity-40"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              <span>Trước</span>
            </button>
            <button
              type="button"
              disabled={currentItem.index >= total}
              onClick={() => onChangeIndex(Math.min(total, currentItem.index + 1))}
              className="inline-flex items-center gap-1 rounded-md border border-slate-700 bg-slate-800 px-2.5 py-1 font-medium text-white transition-colors hover:bg-slate-700 disabled:opacity-40"
            >
              <span>Sau</span>
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {/* Stage Content */}
        {isCurrentLocked ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-amber-500/20 text-amber-400">
              <Lock className="h-6 w-6" />
            </div>
            <h4 className="text-base font-bold text-white">
              Nội dung Trang/Slide {currentItem.index} đang tạm khóa
            </h4>
            <p className="max-w-md text-xs text-slate-300">
              Vui lòng hoàn thành câu hỏi kiểm tra bắt buộc ở Trang/Slide {lockedFromIndex} bên phải
              để mở khóa các trang tiếp theo.
            </p>
            <button
              type="button"
              onClick={() => onChangeIndex(lockedFromIndex!)}
              className="mt-1 rounded-lg bg-amber-500 px-4 py-2 text-xs font-bold text-slate-950 hover:bg-amber-400"
            >
              Quay lại Trang/Slide {lockedFromIndex}
            </button>
          </div>
        ) : contentKind === "PDF_PAGES" ? (
          <div className="flex flex-1 items-center justify-center bg-slate-900/50 p-3">
            {imgLoading ? (
              <div className="flex items-center gap-2 py-16 text-xs text-slate-400">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Đang kết xuất trang PDF...</span>
              </div>
            ) : pageImgUrl ? (
              <img
                src={pageImgUrl}
                alt={`Trang ${currentItem.index}`}
                className="max-h-[46vh] w-auto rounded-md border border-slate-700 bg-white object-contain shadow-xl"
              />
            ) : (
              <div className="w-full max-w-xl rounded-lg bg-white p-6 text-slate-800">
                <h4 className="mb-2 text-sm font-bold">{currentItem.title}</h4>
                <div className="space-y-1.5 text-xs">
                  {currentItem.content_lines.map((ln, idx) => (
                    <p key={idx}>{ln}</p>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          /* 16:9 Academic Slide Canvas for PowerPoint */
          <div className="flex flex-1 items-center justify-center p-4">
            <div className="flex aspect-video w-full max-w-2xl flex-col justify-between rounded-xl border border-slate-600 bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 p-7 text-white shadow-2xl">
              <div>
                <span className="inline-block rounded bg-amber-500/20 px-2.5 py-0.5 font-mono text-[11px] font-bold text-amber-300">
                  SLIDE {currentItem.index}
                </span>
                <h3 className="mt-3 text-xl font-bold leading-snug text-white">
                  {currentItem.title}
                </h3>
              </div>

              <ul className="my-auto space-y-2.5 py-3">
                {currentItem.content_lines.length > 0 ? (
                  currentItem.content_lines.map((line, i) => (
                    <li key={i} className="flex items-start gap-2.5 text-sm text-slate-200">
                      <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-amber-400" />
                      <span>{line}</span>
                    </li>
                  ))
                ) : (
                  <li className="text-xs italic text-slate-400">(Slide tiêu đề / hình ảnh)</li>
                )}
              </ul>

              <div className="flex items-center justify-between border-t border-white/10 pt-2 text-[11px] text-slate-400">
                <span>ADLAS Interactive Slide Deck</span>
                <span>
                  {currentItem.index} / {total}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
