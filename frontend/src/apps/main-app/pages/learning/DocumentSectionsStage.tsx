/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React from "react";
import { Lock, Pencil, Plus, Trash2 } from "lucide-react";
import type { MaterialCheckpoint, MaterialPageItem } from "../../../../types/learning";

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

        return (
          <div key={sec.index} className="space-y-2.5">
            {/* Section Card */}
            <div
              className={`relative rounded-xl border p-5 transition-all ${
                isLocked
                  ? "border-mm-border bg-mm-surface-alt/50"
                  : "border-mm-border bg-mm-surface shadow-sm"
              }`}
            >
              <div className="mb-2.5 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="rounded-md bg-mm-brand/15 px-2 py-0.5 font-mono text-xs font-bold text-mm-brand">
                    Mục {sec.index}
                  </span>
                  <h4 className="text-sm font-bold text-mm-heading">{sec.title}</h4>
                </div>
                {isLocked && (
                  <span className="inline-flex items-center gap-1 rounded bg-amber-500/15 px-2 py-0.5 text-[11px] font-semibold text-amber-600">
                    <Lock className="h-3 w-3" />
                    Cần vượt qua câu hỏi Mục {lockedFromIndex}
                  </span>
                )}
              </div>

              <div className={`space-y-2 text-sm leading-relaxed text-mm-text ${isLocked ? "select-none blur-sm" : ""}`}>
                {sec.content_lines.map((line, i) => (
                  <p key={i}>{line}</p>
                ))}
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
                        <span className="font-medium text-mm-heading">{chk.question_text}</span>
                      </div>
                      <div className="flex shrink-0 items-center gap-1" onClick={(e) => e.stopPropagation()}>
                        <button
                          type="button"
                          onClick={() => onEditCheckpoint?.(chk)}
                          className="rounded p-1 text-mm-text-muted hover:bg-mm-surface hover:text-mm-brand"
                          title="Chỉnh sửa"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => onDeleteCheckpoint?.(chk.id)}
                          className="rounded p-1 text-mm-error hover:bg-mm-error-bg"
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
                  <div className="h-px flex-1 bg-mm-border transition-colors group-hover:bg-amber-500/60" />
                  <button
                    type="button"
                    onClick={() => onAddAtSection?.(sec.index)}
                    className="inline-flex items-center gap-1 rounded-full border border-dashed border-mm-border bg-mm-surface px-3 py-1 text-[11px] font-semibold text-mm-text-muted transition-all hover:border-amber-500 hover:bg-amber-500/10 hover:text-amber-700"
                  >
                    <Plus className="h-3 w-3" />
                    <span>Chèn điểm dừng sau Mục {sec.index}</span>
                  </button>
                  <div className="h-px flex-1 bg-mm-border transition-colors group-hover:bg-amber-500/60" />
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
