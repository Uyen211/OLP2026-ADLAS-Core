// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import type { LocalExamDraft } from "../../../../types/examination";

const DB_NAME = "adlas_exam_offline_db";
const DB_VERSION = 1;
const DRAFTS_STORE = "exam_drafts";
const VIOLATIONS_STORE = "violation_logs";

export interface StoredViolationLog {
  id?: number;
  submission_id: string;
  event_type: string;
  timestamp: string;
  details?: Record<string, unknown>;
}

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof window === "undefined" || !window.indexedDB) {
      reject(new Error("IndexedDB is not supported in this environment"));
      return;
    }

    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event: IDBVersionChangeEvent) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(DRAFTS_STORE)) {
        db.createObjectStore(DRAFTS_STORE, { keyPath: "submission_id" });
      }
      if (!db.objectStoreNames.contains(VIOLATIONS_STORE)) {
        const violationStore = db.createObjectStore(VIOLATIONS_STORE, {
          keyPath: "id",
          autoIncrement: true,
        });
        violationStore.createIndex("by_submission", "submission_id", { unique: false });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export const indexedDbExamStore = {
  async saveDraft(draft: LocalExamDraft): Promise<void> {
    try {
      const db = await openDB();
      return new Promise((resolve, reject) => {
        const tx = db.transaction(DRAFTS_STORE, "readwrite");
        const store = tx.objectStore(DRAFTS_STORE);
        const req = store.put(draft);
        req.onsuccess = () => resolve();
        req.onerror = () => reject(req.error);
      });
    } catch {
      // Fallback to localStorage if IndexedDB is unavailable
      try {
        localStorage.setItem(`exam_draft_${draft.submission_id}`, JSON.stringify(draft));
      } catch {
        // Ignored
      }
    }
  },

  async getDraft(submissionId: string): Promise<LocalExamDraft | null> {
    try {
      const db = await openDB();
      return new Promise((resolve, reject) => {
        const tx = db.transaction(DRAFTS_STORE, "readonly");
        const store = tx.objectStore(DRAFTS_STORE);
        const req = store.get(submissionId);
        req.onsuccess = () => resolve(req.result || null);
        req.onerror = () => reject(req.error);
      });
    } catch {
      try {
        const raw = localStorage.getItem(`exam_draft_${submissionId}`);
        return raw ? JSON.parse(raw) : null;
      } catch {
        return null;
      }
    }
  },

  async clearDraft(submissionId: string): Promise<void> {
    try {
      const db = await openDB();
      const tx = db.transaction(DRAFTS_STORE, "readwrite");
      tx.objectStore(DRAFTS_STORE).delete(submissionId);
    } catch {
      try {
        localStorage.removeItem(`exam_draft_${submissionId}`);
      } catch {
        // Ignored
      }
    }
  },

  async logViolation(log: StoredViolationLog): Promise<void> {
    try {
      const db = await openDB();
      const tx = db.transaction(VIOLATIONS_STORE, "readwrite");
      tx.objectStore(VIOLATIONS_STORE).add(log);
    } catch {
      // Non-blocking
    }
  },

  async getViolations(submissionId: string): Promise<StoredViolationLog[]> {
    try {
      const db = await openDB();
      return new Promise((resolve, reject) => {
        const tx = db.transaction(VIOLATIONS_STORE, "readonly");
        const index = tx.objectStore(VIOLATIONS_STORE).index("by_submission");
        const req = index.getAll(submissionId);
        req.onsuccess = () => resolve(req.result || []);
        req.onerror = () => reject(req.error);
      });
    } catch {
      return [];
    }
  },
};
