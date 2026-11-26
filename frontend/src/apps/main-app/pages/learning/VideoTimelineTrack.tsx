/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useMemo, useRef, useState } from "react";
import type { MaterialCheckpoint } from "../../../../types/learning";

export interface VideoTimelineTrackProps {
  duration: number;
  currentTime: number;
  checkpoints: MaterialCheckpoint[];
  selectedCheckpointId: string | null;
  onScrubVideo: (seconds: number) => void;
  onSelectCheckpoint: (checkpoint: MaterialCheckpoint) => void;
  onMoveCheckpoint: (checkpointId: string, newSeconds: number) => void;
}

export function formatTimecode(secs?: number | null): string {
  if (secs === null || secs === undefined || !Number.isFinite(secs)) return "00:00";
  const clamped = Math.max(0, Math.floor(secs));
  const m = Math.floor(clamped / 60);
  const s = clamped % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export const VideoTimelineTrack: React.FC<VideoTimelineTrackProps> = ({
  duration,
  currentTime,
  checkpoints,
  selectedCheckpointId,
  onScrubVideo,
  onSelectCheckpoint,
  onMoveCheckpoint,
}) => {
  const trackRef = useRef<HTMLDivElement | null>(null);
  const [scrubbingPlayhead, setScrubbingPlayhead] = useState(false);
  const [draggingPin, setDraggingPin] = useState<{
    id: string;
    seconds: number;
    startX: number;
    moved: boolean;
  } | null>(null);

  const safeDuration = duration > 0 ? duration : 1;

  const sortedCheckpoints = useMemo(
    () =>
      [...checkpoints].sort(
        (a, b) => (a.stop_time_seconds ?? 0) - (b.stop_time_seconds ?? 0)
      ),
    [checkpoints]
  );

  // Build evenly spaced ruler ticks
  const ticks = useMemo(() => {
    if (duration <= 0) return [0];
    const step = duration <= 30 ? 5 : duration <= 120 ? 10 : duration <= 300 ? 30 : 60;
    const list: number[] = [];
    for (let t = 0; t <= duration; t += step) {
      list.push(t);
    }
    if (list[list.length - 1] !== Math.floor(duration)) {
      list.push(Math.floor(duration));
    }
    return list;
  }, [duration]);

  const clientXToSeconds = (clientX: number): number => {
    const el = trackRef.current;
    if (!el || duration <= 0) return 0;
    const rect = el.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    return Math.round(ratio * duration);
  };

  // Track background scrubbing (Playhead drag)
  const handleTrackPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if ((e.target as HTMLElement).closest("[data-pin-id]")) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    setScrubbingPlayhead(true);
    onScrubVideo(clientXToSeconds(e.clientX));
  };

  const handleTrackPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!scrubbingPlayhead) return;
    onScrubVideo(clientXToSeconds(e.clientX));
  };

  const handleTrackPointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!scrubbingPlayhead) return;
    setScrubbingPlayhead(false);
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch {
      // ignore if not captured
    }
  };

  // Pin dragging
  const handlePinPointerDown = (
    e: React.PointerEvent<HTMLButtonElement>,
    chk: MaterialCheckpoint
  ) => {
    e.stopPropagation();
    e.currentTarget.setPointerCapture(e.pointerId);
    setDraggingPin({
      id: chk.id,
      seconds: chk.stop_time_seconds ?? 0,
      startX: e.clientX,
      moved: false,
    });
  };

  const handlePinPointerMove = (e: React.PointerEvent<HTMLButtonElement>) => {
    if (!draggingPin) return;
    e.stopPropagation();
    const deltaX = Math.abs(e.clientX - draggingPin.startX);
    const moved = draggingPin.moved || deltaX >= 4;
    const newSec = clientXToSeconds(e.clientX);
    setDraggingPin((prev) => (prev ? { ...prev, seconds: newSec, moved } : null));
    if (moved) {
      onScrubVideo(newSec);
    }
  };

  const handlePinPointerUp = (
    e: React.PointerEvent<HTMLButtonElement>,
    chk: MaterialCheckpoint
  ) => {
    if (!draggingPin) return;
    e.stopPropagation();
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch {
      // ignore
    }
    const { moved, seconds } = draggingPin;
    setDraggingPin(null);

    if (!moved) {
      onSelectCheckpoint(chk);
    } else if (seconds !== (chk.stop_time_seconds ?? 0)) {
      onMoveCheckpoint(chk.id, seconds);
    }
  };

  const playheadPercent = Math.min(100, Math.max(0, (currentTime / safeDuration) * 100));

  return (
    <div className="select-none rounded-lg border border-slate-700 bg-slate-900 p-3 shadow-inner">
      {/* Time Ruler */}
      <div className="relative mb-1.5 h-5 border-b border-slate-800 text-[10px] font-mono text-slate-400">
        {ticks.map((t) => {
          const pct = Math.min(98, Math.max(0, (t / safeDuration) * 100));
          return (
            <div
              key={t}
              style={{ left: `${pct}%` }}
              className="absolute bottom-0 flex -translate-x-1/2 flex-col items-center"
            >
              <span>{formatTimecode(t)}</span>
              <span className="mt-0.5 h-1.5 w-px bg-slate-600" />
            </div>
          );
        })}
      </div>

      {/* Interactive Track Area */}
      <div
        ref={trackRef}
        onPointerDown={handleTrackPointerDown}
        onPointerMove={handleTrackPointerMove}
        onPointerUp={handleTrackPointerUp}
        className="relative h-14 cursor-pointer rounded-md border border-slate-800 bg-slate-950/90 px-1"
      >
        {/* Subtle grid bar */}
        <div className="pointer-events-none absolute inset-x-0 top-1/2 h-2 -translate-y-1/2 rounded-full bg-slate-800/90" />

        {/* Watched / Playhead Progress Fill */}
        <div
          style={{ width: `${playheadPercent}%` }}
          className="pointer-events-none absolute left-0 top-1/2 h-2 -translate-y-1/2 rounded-l-full bg-sky-500/80"
        />

        {/* Draggable Checkpoint Pins */}
        {sortedCheckpoints.map((chk, idx) => {
          const isBeingDragged = draggingPin?.id === chk.id;
          const displaySec = isBeingDragged
            ? draggingPin.seconds
            : (chk.stop_time_seconds ?? 0);
          const pinPct = Math.min(98.5, Math.max(1.5, (displaySec / safeDuration) * 100));
          const isSelected = selectedCheckpointId === chk.id;

          return (
            <button
              key={chk.id}
              type="button"
              data-pin-id={chk.id}
              onPointerDown={(e) => handlePinPointerDown(e, chk)}
              onPointerMove={handlePinPointerMove}
              onPointerUp={(e) => handlePinPointerUp(e, chk)}
              style={{ left: `${pinPct}%` }}
              title={`Câu ${idx + 1} (${formatTimecode(displaySec)}): ${chk.question_text}`}
              className={`group absolute top-1/2 -translate-x-1/2 -translate-y-1/2 touch-none transition-transform ${
                isBeingDragged
                  ? "z-30 scale-125 cursor-grabbing"
                  : isSelected
                  ? "z-20 scale-110 cursor-grab"
                  : "z-10 cursor-grab hover:scale-110"
              }`}
            >
              {/* Floating Live Timecode Tooltip while dragging */}
              {isBeingDragged && (
                <span className="pointer-events-none absolute -top-7 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-amber-400 px-1.5 py-0.5 font-mono text-[10px] font-bold text-slate-950 shadow-lg">
                  {formatTimecode(displaySec)}
                </span>
              )}

              {/* Pin Pill */}
              <div
                className={`flex h-7 min-w-[26px] items-center justify-center rounded-full border-2 px-1.5 font-mono text-[11px] font-bold shadow-md ${
                  chk.is_blocking
                    ? "border-white bg-amber-500 text-slate-950"
                    : "border-white bg-sky-400 text-slate-950"
                } ${isSelected || isBeingDragged ? "ring-2 ring-white ring-offset-2 ring-offset-slate-950" : ""}`}
              >
                {idx + 1}
              </div>
            </button>
          );
        })}

        {/* Playhead Needle (CapCut-style) */}
        <div
          style={{ left: `${playheadPercent}%` }}
          className="pointer-events-none absolute inset-y-0 z-30 -translate-x-1/2"
        >
          <div className="mx-auto h-2.5 w-3 rounded-t-sm bg-rose-500 shadow" />
          <div className="mx-auto h-full w-0.5 bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.9)]" />
        </div>
      </div>

      {/* Footer Hint */}
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400">
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
            Bắt buộc
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-sky-400" />
            Tùy chọn
          </span>
        </div>
        <span>Kéo thả các chấm số để đổi thời điểm dừng như CapCut • Click nền để tua</span>
      </div>
    </div>
  );
};
