/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useState } from "react";
import { Lock } from "lucide-react";
import type { MaterialCheckpoint, MaterialPageItem } from "../../../../types/learning";

export interface DocumentFilmstripTrackProps {
  items: MaterialPageItem[];
  currentIndex: number; // 1-based
  checkpoints: MaterialCheckpoint[];
  selectedCheckpointId?: string | null;
  editable?: boolean;
  lockedFromIndex?: number; // For student progressive gate (e.g. > maxUnlockedIndex)
  onSelectIndex: (index: number) => void;
  onSelectCheckpoint?: (checkpoint: MaterialCheckpoint) => void;
  onMoveCheckpoint?: (checkpointId: string, newSectionIndex: number) => void;
}

export const DocumentFilmstripTrack: React.FC<DocumentFilmstripTrackProps> = ({
  items,
  currentIndex,
  checkpoints,
  selectedCheckpointId,
  editable = false,
  lockedFromIndex,
  onSelectIndex,
  onSelectCheckpoint,
  onMoveCheckpoint,
}) => {
  const [draggingCheckpointId, setDraggingCheckpointId] = useState<string | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

  const sortedCheckpoints = [...checkpoints].sort(
    (a, b) => (a.section_index ?? 1) - (b.section_index ?? 1)
  );

  // Map 1-based index -> checkpoints attached there
  const indexMap = new Map<number, { chk: MaterialCheckpoint; order: number }[]>();
  sortedCheckpoints.forEach((chk, i) => {
    const idx = chk.section_index ?? 1;
    const list = indexMap.get(idx) || [];
    list.push({ chk, order: i + 1 });
    indexMap.set(idx, list);
  });

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900 p-3 shadow-inner">
      <div className="flex items-stretch gap-2.5 overflow-x-auto pb-1">
        {items.map((item) => {
          const isCurrent = item.index === currentIndex;
          const isLocked = lockedFromIndex !== undefined && item.index > lockedFromIndex;
          const isDropTarget = dragOverIndex === item.index && draggingCheckpointId !== null;
          const attached = indexMap.get(item.index) || [];

          return (
            <div
              key={item.index}
              onClick={() => onSelectIndex(item.index)}
              onDragOver={(e) => {
                if (!editable || !draggingCheckpointId) return;
                e.preventDefault();
                setDragOverIndex(item.index);
              }}
              onDragLeave={() => {
                if (dragOverIndex === item.index) setDragOverIndex(null);
              }}
              onDrop={(e) => {
                if (!editable || !draggingCheckpointId) return;
                e.preventDefault();
                setDragOverIndex(null);
                const chkId = draggingCheckpointId;
                setDraggingCheckpointId(null);
                const original = checkpoints.find((c) => c.id === chkId);
                if (original && (original.section_index ?? 1) !== item.index) {
                  onMoveCheckpoint?.(chkId, item.index);
                }
              }}
              className={`group relative flex w-32 shrink-0 cursor-pointer flex-col justify-between rounded-lg border-2 p-2 transition-all ${
                isDropTarget
                  ? "border-amber-400 bg-amber-500/20 scale-105"
                  : isCurrent
                  ? "border-amber-500 bg-slate-800 ring-2 ring-amber-500/40"
                  : isLocked
                  ? "border-slate-800 bg-slate-950/60 opacity-60"
                  : "border-slate-700 bg-slate-950 hover:border-slate-500"
              }`}
            >
              {/* Top row: Page/Slide number + Attached Checkpoint Pins */}
              <div className="flex items-center justify-between gap-1">
                <span
                  className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-bold ${
                    isCurrent
                      ? "bg-amber-500 text-slate-950"
                      : "bg-slate-800 text-slate-300"
                  }`}
                >
                  #{item.index}
                </span>

                <div className="flex flex-wrap items-center justify-end gap-1">
                  {isLocked && <Lock className="h-3 w-3 text-slate-400" />}
                  {attached.map(({ chk, order }) => {
                    const isSel = selectedCheckpointId === chk.id;
                    return (
                      <button
                        key={chk.id}
                        type="button"
                        draggable={editable}
                        onDragStart={(e) => {
                          if (!editable) return;
                          e.stopPropagation();
                          setDraggingCheckpointId(chk.id);
                        }}
                        onDragEnd={() => {
                          setDraggingCheckpointId(null);
                          setDragOverIndex(null);
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectIndex(item.index);
                          onSelectCheckpoint?.(chk);
                        }}
                        title={
                          editable
                            ? `Kéo thả sang trang/slide khác • Câu ${order}: ${chk.question_text}`
                            : `Câu ${order}: ${chk.question_text}`
                        }
                        className={`flex h-5 min-w-[20px] items-center justify-center rounded-full border border-white px-1 font-mono text-[10px] font-bold shadow ${
                          editable ? "cursor-grab active:cursor-grabbing" : "cursor-pointer"
                        } ${
                          chk.is_blocking
                            ? "bg-amber-500 text-slate-950"
                            : "bg-sky-400 text-slate-950"
                        } ${isSel ? "ring-2 ring-white" : ""}`}
                      >
                        {order}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Mini title preview */}
              <p className="mt-2 line-clamp-2 text-[11px] font-medium leading-tight text-slate-200">
                {item.title}
              </p>
            </div>
          );
        })}
      </div>

      {editable && (
        <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
          <span>
            Click thẻ trang/slide để xem •{" "}
            <strong className="text-slate-300">Kéo thả chấm số</strong> sang trang khác để dời câu hỏi
          </span>
        </div>
      )}
    </div>
  );
};
