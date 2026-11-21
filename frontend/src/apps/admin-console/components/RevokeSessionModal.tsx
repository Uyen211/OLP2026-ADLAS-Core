/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useState } from "react";
import { AlertCircle, AlertTriangle, ShieldAlert } from "lucide-react";
import { Modal } from "../../../components/ui/Modal";
import { SystemAuthService } from "../../../services/systemAuthService";
import { UserSession } from "../../../types/system";

interface RevokeSessionModalProps {
  session: UserSession | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const RevokeSessionModal: React.FC<RevokeSessionModalProps> = ({
  session,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!session) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!reason.trim()) {
      setErrorMessage("Audit reason is required for security tracking (Rule BR-SYS-03).");
      return;
    }

    setIsSubmitting(true);
    try {
      await SystemAuthService.revokeSession({
        session_id: session.session_id,
        user_id: session.user_id,
        reason: reason.trim(),
      });
      setReason("");
      onClose();
      onSuccess();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Failed to revoke session.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Force Session Revocation" maxWidth="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="flex items-start gap-3 p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-sm">
          <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5 text-amber-600" />
          <div>
            <p className="font-semibold">Security Action Warning</p>
            <p className="text-xs text-amber-700 mt-1">
              Revoking this session will invalidate the associated JWT token across all Kong Gateway edge proxies within 50ms (Rule BR-SYS-02). The user will be immediately logged out.
            </p>
          </div>
        </div>

        {errorMessage && (
          <div className="flex items-start gap-2.5 p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-sm">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-2 text-xs">
          <div className="flex justify-between">
            <span className="text-slate-500">Session ID:</span>
            <span className="font-mono font-medium text-slate-800">{session.session_id}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Target User:</span>
            <span className="font-medium text-slate-800">{session.full_name} ({session.email})</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Source IP:</span>
            <span className="font-mono text-slate-800">{session.ip_address}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Client Agent:</span>
            <span className="text-slate-800 truncate max-w-xs">{session.user_agent}</span>
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
            Audit Reason <span className="text-rose-500">*</span>
          </label>
          <textarea
            required
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g., Suspicious IP anomaly detected or user security incident..."
            className="w-full px-3.5 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-rose-500 focus:border-transparent transition-all"
          />
        </div>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 rounded-pill transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="inline-flex items-center gap-2 px-5 py-2 text-sm font-medium text-white bg-rose-600 hover:bg-rose-700 disabled:opacity-50 rounded-pill transition-all"
          >
            <ShieldAlert className="w-4 h-4" />
            {isSubmitting ? "Revoking..." : "Confirm Revocation"}
          </button>
        </div>
      </form>
    </Modal>
  );
};
