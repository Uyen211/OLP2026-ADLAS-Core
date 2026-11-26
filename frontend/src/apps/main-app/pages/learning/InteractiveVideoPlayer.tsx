/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, Clock, Lock } from "lucide-react";
import { learningService } from "../../../../services/learningService";
import { ApiError } from "../../../../services/httpClient";
import type { MaterialCheckpoint } from "../../../../types/learning";
import { showToast } from "../../components/Toast";

export interface InteractiveVideoPlayerProps {
  courseId: string;
  src: string;
  checkpoints: MaterialCheckpoint[];
  isCompleted: boolean;
  onCheckpointPassed: (checkpointId: string) => void;
  onReadyToComplete: () => void;
}

export const InteractiveVideoPlayer: React.FC<InteractiveVideoPlayerProps> = ({
  courseId,
  src,
  checkpoints,
  isCompleted,
  onCheckpointPassed,
  onReadyToComplete,
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [duration, setDuration] = useState(0);
  const [maxWatched, setMaxWatched] = useState(0);
  const [activeCheckpoint, setActiveCheckpoint] = useState<MaterialCheckpoint | null>(null);
  const [countdown, setCountdown] = useState(10);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const [completionTriggered, setCompletionTriggered] = useState(isCompleted);
  const lastTriggeredRef = useRef<Record<string, number>>({});

  // Earliest unpassed blocking checkpoint caps seeking
  const earliestBlockingStop = useMemo(() => {
    const unpassed = checkpoints
      .filter((c) => c.is_blocking && !c.is_passed && c.stop_time_seconds !== null && c.stop_time_seconds !== undefined)
      .sort((a, b) => (a.stop_time_seconds ?? 0) - (b.stop_time_seconds ?? 0));
    return unpassed.length > 0 ? unpassed[0].stop_time_seconds! : Infinity;
  }, [checkpoints]);

  const allBlockingPassed = useMemo(
    () => checkpoints.filter((c) => c.is_blocking).every((c) => c.is_passed),
    [checkpoints]
  );

  const rewindAndResume = (chk: MaterialCheckpoint, msg: string) => {
    setFeedback({ type: "err", text: msg });
    lastTriggeredRef.current[chk.id] = Date.now();
    setTimeout(() => {
      setActiveCheckpoint(null);
      setFeedback(null);
      if (videoRef.current) {
        const stopAt = chk.stop_time_seconds ?? videoRef.current.currentTime;
        const rewindTo = Math.max(0, stopAt - (chk.rewind_seconds ?? 15));
        videoRef.current.currentTime = rewindTo;
        videoRef.current.play().catch(() => {});
      }
    }, 1500);
  };

  // Countdown timer while checkpoint overlay is active
  useEffect(() => {
    if (!activeCheckpoint || feedback) return;
    if (countdown <= 0) {
      rewindAndResume(
        activeCheckpoint,
        `Hết thời gian! Video sẽ tự động lùi lại ${activeCheckpoint.rewind_seconds ?? 15} giây để bạn nghe lại.`
      );
      return;
    }
    const timer = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [activeCheckpoint, countdown, feedback]);

  const handleTimeUpdate = () => {
    const vid = videoRef.current;
    if (!vid || activeCheckpoint) return;
    const current = vid.currentTime;

    if (current > maxWatched && current <= earliestBlockingStop + 0.5) {
      setMaxWatched(current);
    }

    // Trigger earliest unpassed checkpoint at or past stop_time_seconds
    const pendingCheckpoints = checkpoints
      .filter((c) => !c.is_passed && c.stop_time_seconds !== null && c.stop_time_seconds !== undefined)
      .sort((a, b) => (a.stop_time_seconds ?? 0) - (b.stop_time_seconds ?? 0));

    for (const chk of pendingCheckpoints) {
      const stopAt = chk.stop_time_seconds!;
      const cooldown = lastTriggeredRef.current[chk.id] || 0;
      if (Date.now() - cooldown < 3000) continue;

      if (current >= stopAt) {
        vid.pause();
        if (Math.abs(current - stopAt) > 1.5) {
          vid.currentTime = stopAt;
        }
        setActiveCheckpoint(chk);
        setCountdown(chk.time_limit_seconds ?? 10);
        setFeedback(null);
        break;
      }
    }

    // Complete when >= 90% watched and all blocking checkpoints passed
    if (!completionTriggered && duration > 0 && current / duration >= 0.9 && allBlockingPassed) {
      setCompletionTriggered(true);
      onReadyToComplete();
    }
  };

  const handleSeeking = () => {
    const vid = videoRef.current;
    if (!vid) return;
    const cap = Math.min(Math.max(maxWatched + 1, 0), earliestBlockingStop);
    if (vid.currentTime > cap + 0.8) {
      vid.currentTime = Math.max(0, cap - 0.5);
      showToast("warning", "Bạn cần hoàn thành các mốc kiểm tra trước khi tua vượt.");
    }
  };

  const handleEnded = () => {
    if (!completionTriggered && allBlockingPassed) {
      setCompletionTriggered(true);
      onReadyToComplete();
    } else if (!allBlockingPassed) {
      showToast("warning", "Bạn vẫn còn câu hỏi điểm dừng bắt buộc chưa hoàn thành.");
    }
  };

  const handleSelectOption = async (optKey: string) => {
    if (!activeCheckpoint || submitting || feedback) return;
    setSubmitting(true);
    try {
      const res = await learningService.submitCheckpoint(courseId, activeCheckpoint.id, optKey);
      if (res.is_correct) {
        setFeedback({ type: "ok", text: "Chính xác! Video sẽ tiếp tục phát." });
        onCheckpointPassed(activeCheckpoint.id);
        setTimeout(() => {
          setActiveCheckpoint(null);
          setFeedback(null);
          videoRef.current?.play().catch(() => {});
        }, 1000);
      } else {
        rewindAndResume(activeCheckpoint, res.message);
      }
    } catch (err) {
      showToast("error", err instanceof ApiError ? err.message : "Không thể gửi câu trả lời.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Sleek Cinema Container */}
      <div className="relative aspect-video w-full overflow-hidden rounded-2xl border border-slate-800 bg-black shadow-xl">
        <video
          ref={videoRef}
          controls
          preload="metadata"
          src={src}
          onLoadedMetadata={(e) => setDuration(e.currentTarget.duration || 0)}
          onTimeUpdate={handleTimeUpdate}
          onSeeking={handleSeeking}
          onEnded={handleEnded}
          className="h-full w-full object-contain"
        />

        {/* High-Contrast Interactive Checkpoint Overlay */}
        {activeCheckpoint && (
          <div className="absolute inset-0 z-20 flex items-center justify-center bg-black/75 p-4 backdrop-blur-xs">
            <div
              className={`w-full max-w-lg rounded-2xl border bg-white p-6 shadow-2xl transition-all ${
                feedback?.type === "ok"
                  ? "border-emerald-500 ring-4 ring-emerald-50"
                  : feedback?.type === "err"
                  ? "border-amber-500 ring-4 ring-amber-50"
                  : "border-slate-200"
              }`}
            >
              <div className="mb-3.5 flex items-center justify-between">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 border border-amber-200/80 px-3 py-1 text-xs font-semibold text-amber-700">
                  <Lock className="h-3.5 w-3.5" />
                  Điểm dừng kiểm tra nhận thức
                </span>
                <span
                  className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 font-mono text-xs font-bold ${
                    countdown <= 3
                      ? "bg-rose-50 text-rose-600 border border-rose-200"
                      : "bg-slate-100 text-slate-700 border border-slate-200"
                  }`}
                >
                  <Clock className="h-3.5 w-3.5" />
                  {countdown}s
                </span>
              </div>

              <p className="mb-4 text-sm font-bold text-slate-900 leading-snug">
                {activeCheckpoint.question_text}
              </p>

              <div className="grid grid-cols-1 gap-2">
                {Object.entries(activeCheckpoint.options || {}).map(([key, val]) => (
                  <button
                    key={key}
                    type="button"
                    disabled={submitting || Boolean(feedback)}
                    onClick={() => handleSelectOption(key)}
                    className="group flex items-start gap-3 rounded-xl border border-slate-200 bg-slate-50/70 p-3 text-left text-xs font-medium text-slate-800 transition-all hover:border-blue-500 hover:bg-blue-50/50 hover:text-blue-900 disabled:opacity-60 shadow-none hover:shadow-xs"
                  >
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-white border border-slate-200 font-bold text-blue-600 text-[11px] shadow-2xs group-hover:border-blue-300">
                      {key}
                    </span>
                    <span className="pt-0.5">{val}</span>
                  </button>
                ))}
              </div>

              {feedback && (
                <div
                  className={`mt-4 flex items-center gap-2 rounded-xl p-3 text-xs font-medium ${
                    feedback.type === "ok"
                      ? "border border-emerald-200 bg-emerald-50 text-emerald-800"
                      : "border border-amber-200 bg-amber-50 text-amber-800"
                  }`}
                >
                  {feedback.type === "ok" ? (
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
                  ) : (
                    <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />
                  )}
                  <span>{feedback.text}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Modern Polished Timeline Marker Summary */}
      {checkpoints.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-md bg-blue-50 text-blue-600 font-bold text-xs">
                {checkpoints.filter((c) => c.is_passed).length}/{checkpoints.length}
              </div>
              <span className="font-bold text-slate-900">
                Mốc kiểm tra nhận thức trên Video
              </span>
            </div>
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-medium border ${
                allBlockingPassed
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                  : "bg-amber-50 text-amber-700 border-amber-200"
              }`}
            >
              {allBlockingPassed ? (
                <>
                  <CheckCircle2 className="h-3 w-3" />
                  Đã hoàn thành tất cả mốc bắt buộc
                </>
              ) : (
                <>
                  <Lock className="h-3 w-3" />
                  Chặn tua vượt qua mốc chưa đạt
                </>
              )}
            </span>
          </div>

          {/* Progress bar track */}
          <div className="relative my-3 h-2 w-full rounded-full bg-slate-100">
            {duration > 0 &&
              checkpoints.map((chk, idx) => {
                const pos = Math.min(98, Math.max(2, ((chk.stop_time_seconds ?? 0) / duration) * 100));
                return (
                  <div
                    key={chk.id}
                    style={{ left: `${pos}%` }}
                    title={`Mốc ${idx + 1} (${chk.stop_time_seconds ?? 0}s): ${chk.question_text}`}
                    className="group absolute top-1/2 -translate-x-1/2 -translate-y-1/2 cursor-pointer"
                  >
                    <div
                      className={`h-4 w-4 rounded-full border-2 border-white shadow-md transition-transform group-hover:scale-125 ${
                        chk.is_passed
                          ? "bg-emerald-500 ring-2 ring-emerald-200"
                          : chk.is_blocking
                          ? "bg-amber-500 ring-2 ring-amber-200"
                          : "bg-blue-500 ring-2 ring-blue-200"
                      }`}
                    />
                  </div>
                );
              })}
          </div>

          {/* Checkpoint list mini chips */}
          <div className="mt-2.5 flex flex-wrap gap-2 pt-2 border-t border-slate-100">
            {checkpoints.map((chk, idx) => {
              const mm = Math.floor((chk.stop_time_seconds ?? 0) / 60);
              const ss = String(Math.floor((chk.stop_time_seconds ?? 0) % 60)).padStart(2, "0");
              return (
                <div
                  key={chk.id}
                  className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11px] font-medium transition-all ${
                    chk.is_passed
                      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                      : "border-slate-200 bg-slate-50 text-slate-700"
                  }`}
                >
                  <span className="font-mono text-xs font-bold text-slate-500">
                    {mm}:{ss}
                  </span>
                  <span>Mốc {idx + 1}</span>
                  {chk.is_passed ? (
                    <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                  ) : chk.is_blocking ? (
                    <Lock className="h-3 w-3 text-amber-600" />
                  ) : null}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
