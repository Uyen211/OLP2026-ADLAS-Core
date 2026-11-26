/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React from "react";
import { Lock, Pencil, Plus, Trash2 } from "lucide-react";
import type { MaterialCheckpoint, MaterialPageItem } from "../../../../types/learning";
import { MathCodeContent } from "../../components/MathCodeContent";

export interface DocumentSectionsStageProps {
  items: MaterialPageItem[];
  checkpoints: MaterialCheckpoint[];
  editable?: boolean;
  selectedCheckpointId?: string | null;
  lockedFromIndex?: number; // Student gate: sections > lockedFromIndex are blurred/locked
  onAddAtSection?: (sectionIndex: number) => void;
  onSelectCheckpoint?: (checkpoint: MaterialCheckpoint) => void;
  onEditCheckpoint?: (checkpoint: MaterialCheckpoint) => void;
  onDeleteCheckpoint?: (checkpointId: string) => void;
}

export const DocumentSectionsStage: React.FC<DocumentSectionsStageProps> = ({
  items,
  checkpoints,
  editable = false,
  selectedCheckpointId,
  lockedFromIndex,
  onAddAtSection,
  onSelectCheckpoint,
  onEditCheckpoint,
  onDeleteCheckpoint,
}) => {
  return (
    <div className="space-y-4">
      {items.map((sec) => {
        const isLocked = lockedFromIndex !== undefined && sec.index > lockedFromIndex;
        const secCheckpoints = checkpoints.filter((c) => (c.section_index ?? 1) === sec.index);
        const displayTitle =
          sec.title.replace(new RegExp(`^${sec.index}\\.?\\s*`), "").trim() || sec.title;

        return (
          <div key={sec.index} className="space-y-2.5">
            {/* Section Card */}
            <div
              className={`relative rounded-xl border p-5 transition-all ${
                isLocked
                  ? "border-slate-200 bg-slate-100/80"
                  : "border-slate-200 bg-white shadow-sm hover:border-slate-300"
              }`}
            >
              <div className="mb-3 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="rounded-md bg-blue-50 border border-blue-100 px-2 py-0.5 font-mono text-xs font-bold text-blue-600">
                    Mục {sec.index}
                  </span>
                  <h4 className="text-sm font-bold text-slate-900">{displayTitle}</h4>
                </div>
                {isLocked && (
                  <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-[11px] font-semibold text-amber-700">
                    <Lock className="h-3 w-3" />
                    Cần vượt qua câu hỏi Mục {lockedFromIndex}
                  </span>
                )}
              </div>

              <div
                className={`text-sm leading-relaxed text-slate-800 ${
                  isLocked ? "select-none blur-sm pointer-events-none" : ""
                }`}
              >
                <MathCodeContent content={sec.content_lines.join("\n")} />
              </div>
            </div>

            {/* Inline Checkpoints attached right after this Section (Instructor Studio) */}
            {editable && (
              <div className="space-y-2 pl-4">
                {secCheckpoints.map((chk) => {
                  const isSel = selectedCheckpointId === chk.id;
                  return (
                    <div
                      key={chk.id}
                      onClick={() => onSelectCheckpoint?.(chk)}
                      className={`flex cursor-pointer items-center justify-between gap-3 rounded-lg border px-3.5 py-2.5 text-xs transition-all ${
                        isSel
                          ? "border-amber-500 bg-amber-500/10 ring-2 ring-amber-500/30"
                          : "border-amber-500/40 bg-amber-500/5 hover:border-amber-500"
                      }`}
                    >
                      <div className="min-w-0 flex-1">
                        <span className="mr-2 rounded bg-amber-500/20 px-1.5 py-0.5 font-semibold text-amber-700">
                          {chk.is_blocking ? "Điểm dừng bắt buộc" : "Câu hỏi tùy chọn"}
                        </span>
                        <span className="font-medium text-slate-900">{chk.question_text}</span>
                      </div>
                      <div className="flex shrink-0 items-center gap-1" onClick={(e) => e.stopPropagation()}>
                        <button
                          type="button"
                          onClick={() => onEditCheckpoint?.(chk)}
                          className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-blue-600"
                          title="Chỉnh sửa"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => onDeleteCheckpoint?.(chk.id)}
                          className="rounded p-1 text-rose-500 hover:bg-rose-50"
                          title="Xóa"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })}

                {/* Notion-style Inline Insert Divider */}
                <div className="group flex items-center gap-2 py-0.5">
                  <div className="h-px flex-1 bg-slate-200 transition-colors group-hover:bg-amber-500/60" />
                  <button
                    type="button"
                    onClick={() => onAddAtSection?.(sec.index)}
                    className="inline-flex items-center gap-1 rounded-full border border-dashed border-slate-300 bg-white px-3 py-1 text-[11px] font-semibold text-slate-600 transition-all hover:border-amber-500 hover:bg-amber-50 hover:text-amber-700 shadow-2xs"
                  >
                    <Plus className="h-3 w-3" />
                    <span>Chèn điểm dừng sau Mục {sec.index}</span>
                  </button>
                  <div className="h-px flex-1 bg-slate-200 transition-colors group-hover:bg-amber-500/60" />
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
