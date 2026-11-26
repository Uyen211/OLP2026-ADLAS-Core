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
    <div className="space-y-3">
      <div className="relative aspect-video w-full overflow-hidden rounded-mm border border-mm-divider bg-black">
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

        {/* Interactive Checkpoint Overlay */}
        {activeCheckpoint && (
          <div className="absolute inset-0 z-20 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm">
            <div
              className={`w-full max-w-lg rounded-mm border-2 bg-mm-surface p-5 shadow-2xl transition-colors ${
                feedback?.type === "ok"
                  ? "border-emerald-500"
                  : feedback?.type === "err"
                  ? "border-amber-500"
                  : "border-mm-brand"
              }`}
            >
              <div className="mb-3 flex items-center justify-between">
                <span className="inline-flex items-center gap-1.5 rounded bg-amber-500/15 px-2.5 py-1 text-xs font-semibold text-amber-600">
                  <Lock className="h-3.5 w-3.5" />
                  Điểm dừng kiểm tra nhận thức
                </span>
                <span
                  className={`inline-flex items-center gap-1 font-mm-mono text-sm font-bold ${
                    countdown <= 3 ? "text-red-500" : "text-mm-heading"
                  }`}
                >
                  <Clock className="h-4 w-4" />
                  {countdown}s
                </span>
              </div>

              <p className="mb-4 text-sm font-semibold text-mm-heading">
                {activeCheckpoint.question_text}
              </p>

              <div className="grid grid-cols-1 gap-2">
                {Object.entries(activeCheckpoint.options || {}).map(([key, val]) => (
                  <button
                    key={key}
                    type="button"
                    disabled={submitting || Boolean(feedback)}
                    onClick={() => handleSelectOption(key)}
                    className="flex items-start gap-2.5 rounded-mm border border-mm-border bg-mm-bg/60 px-3.5 py-2.5 text-left text-xs text-mm-heading transition-colors hover:border-mm-brand hover:bg-mm-brand/10 disabled:opacity-60"
                  >
                    <span className="font-bold text-mm-brand">{key}.</span>
                    <span>{val}</span>
                  </button>
                ))}
              </div>

              {feedback && (
                <div
                  className={`mt-4 flex items-center gap-2 rounded-mm px-3 py-2 text-xs font-medium ${
                    feedback.type === "ok"
                      ? "bg-emerald-500/15 text-emerald-600"
                      : "bg-amber-500/15 text-amber-600"
                  }`}
                >
                  {feedback.type === "ok" ? (
                    <CheckCircle2 className="h-4 w-4 shrink-0" />
                  ) : (
                    <AlertTriangle className="h-4 w-4 shrink-0" />
                  )}
                  <span>{feedback.text}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Custom Timeline Marker Summary */}
      {checkpoints.length > 0 && (
        <div className="rounded-mm border border-mm-divider bg-mm-surface-alt/30 px-3.5 py-2.5">
          <div className="mb-2 flex items-center justify-between text-xs">
            <span className="font-semibold text-mm-heading">
              Mốc kiểm tra trên Video ({checkpoints.filter((c) => c.is_passed).length}/{checkpoints.length} đã đạt)
            </span>
            <span className="text-mm-text-muted">
              {allBlockingPassed ? "Đã hoàn thành tất cả mốc bắt buộc" : "Chặn tua vượt qua mốc chưa đạt"}
            </span>
          </div>
          <div className="relative h-2.5 w-full rounded-full bg-mm-border/50">
            {duration > 0 &&
              checkpoints.map((chk) => {
                const pos = Math.min(98, Math.max(2, ((chk.stop_time_seconds ?? 0) / duration) * 100));
                return (
                  <div
                    key={chk.id}
                    style={{ left: `${pos}%` }}
                    title={`Mốc ${chk.stop_time_seconds ?? 0}s: ${chk.question_text}`}
                    className={`absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white shadow ${
                      chk.is_passed ? "bg-emerald-500" : "bg-amber-400"
                    }`}
                  />
                );
              })}
          </div>
        </div>
      )}
    </div>
  );
};
