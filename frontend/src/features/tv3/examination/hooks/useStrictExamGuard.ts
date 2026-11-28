// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import { useEffect, useRef, useState, useCallback } from "react";
import { indexedDbExamStore } from "../utils/indexedDbExamStore";
import { examinationService } from "../../../../services/examinationService";

export interface StrictViolationEvent {
  id: string;
  type: "TAB_BLUR" | "FULLSCREEN_EXIT" | "DEVTOOLS_KEY" | "CLIPBOARD_KEY";
  message: string;
  timestamp: string;
  strikeNumber: number;
}

interface UseStrictExamGuardParams {
  submissionId: string;
  isStrictMode: boolean;
  onMaxStrikesExceeded?: () => void;
}

export function useStrictExamGuard({
  submissionId,
  isStrictMode,
  onMaxStrikesExceeded,
}: UseStrictExamGuardParams) {
  const [strikes, setStrikes] = useState<number>(0);
  const [violations, setViolations] = useState<StrictViolationEvent[]>([]);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [isWarningActive, setIsWarningActive] = useState<boolean>(false);
  const [activeWarningText, setActiveWarningText] = useState<string>("");

  const strikesRef = useRef(0);
  const blurGraceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  strikesRef.current = strikes;

  const recordViolation = useCallback(
    async (type: StrictViolationEvent["type"], message: string) => {
      const nextStrikes = strikesRef.current + 1;
      setStrikes(nextStrikes);
      strikesRef.current = nextStrikes;

      const event: StrictViolationEvent = {
        id: `${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
        type,
        message,
        timestamp: new Date().toISOString(),
        strikeNumber: nextStrikes,
      };

      setViolations((prev) => [event, ...prev]);
      setActiveWarningText(`Cảnh báo vi phạm lần ${nextStrikes}/3: ${message}`);
      setIsWarningActive(true);

      // Lưu log vào IndexedDB
      await indexedDbExamStore.logViolation({
        submission_id: submissionId,
        event_type: type,
        timestamp: event.timestamp,
        details: { strike: nextStrikes, message },
      });

      // Nếu có API ghi nhận vi phạm trên backend
      try {
        if ((examinationService as any).recordViolation) {
          await (examinationService as any).recordViolation(submissionId, {
            violation_type: type,
            details: { message, strike: nextStrikes },
          });
        }
      } catch {
        // Non-blocking
      }

      if (nextStrikes >= 3 && onMaxStrikesExceeded) {
        onMaxStrikesExceeded();
      }
    },
    [submissionId, onMaxStrikesExceeded]
  );

  const requestFullscreen = useCallback(async () => {
    try {
      if (document.documentElement.requestFullscreen) {
        await document.documentElement.requestFullscreen();
        setIsFullscreen(true);
      }
    } catch {
      // User blocked fullscreen
    }
  }, []);

  useEffect(() => {
    if (!isStrictMode) return;

    // 1. Giám sát mất tiêu điểm cửa sổ (Tab switch / Blur) có Grace period 1000ms
    const handleVisibilityChange = () => {
      if (document.hidden) {
        blurGraceTimerRef.current = setTimeout(() => {
          recordViolation("TAB_BLUR", "Rời khỏi tab bài thi hoặc chuyển sang ứng dụng khác");
        }, 1000);
      } else {
        if (blurGraceTimerRef.current) {
          clearTimeout(blurGraceTimerRef.current);
          blurGraceTimerRef.current = null;
        }
      }
    };

    const handleWindowBlur = () => {
      blurGraceTimerRef.current = setTimeout(() => {
        recordViolation("TAB_BLUR", "Cửa sổ làm bài thi bị mất tiêu điểm");
      }, 1000);
    };

    const handleWindowFocus = () => {
      if (blurGraceTimerRef.current) {
        clearTimeout(blurGraceTimerRef.current);
        blurGraceTimerRef.current = null;
      }
    };

    // 2. Giám sát thoát chế độ toàn màn hình
    const handleFullscreenChange = () => {
      const active = !!document.fullscreenElement;
      setIsFullscreen(active);
      if (!active) {
        recordViolation("FULLSCREEN_EXIT", "Thoát khỏi chế độ toàn màn hình phòng thi");
      }
    };

    // 3. Khóa các phím tắt can thiệp DevTools & Clipboard
    const handleKeyDown = (e: KeyboardEvent) => {
      // F12
      if (e.key === "F12") {
        e.preventDefault();
        recordViolation("DEVTOOLS_KEY", "Cố gắng mở công cụ phát triển (F12)");
        return;
      }
      // Ctrl+Shift+I / Ctrl+Shift+J / Ctrl+Shift+C
      if (e.ctrlKey && e.shiftKey && ["I", "J", "C"].includes(e.key.toUpperCase())) {
        e.preventDefault();
        recordViolation("DEVTOOLS_KEY", "Cố gắng mở phím tắt kiểm tra mã nguồn (Ctrl+Shift+I)");
        return;
      }
      // Ctrl+C / Ctrl+V / Ctrl+P
      if (e.ctrlKey && ["C", "V", "P"].includes(e.key.toUpperCase())) {
        e.preventDefault();
        recordViolation("CLIPBOARD_KEY", `Cố gắng sử dụng phím tắt sao chép/in ấn (Ctrl+${e.key.toUpperCase()})`);
        return;
      }
    };

    // 4. Khóa chuột phải (Context menu)
    const handleContextMenu = (e: MouseEvent) => {
      e.preventDefault();
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("blur", handleWindowBlur);
    window.addEventListener("focus", handleWindowFocus);
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("contextmenu", handleContextMenu);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("blur", handleWindowBlur);
      window.removeEventListener("focus", handleWindowFocus);
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("contextmenu", handleContextMenu);
      if (blurGraceTimerRef.current) {
        clearTimeout(blurGraceTimerRef.current);
      }
    };
  }, [isStrictMode, recordViolation]);

  return {
    strikes,
    violations,
    isFullscreen,
    isWarningActive,
    activeWarningText,
    dismissWarning: () => setIsWarningActive(false),
    requestFullscreen,
  };
}
