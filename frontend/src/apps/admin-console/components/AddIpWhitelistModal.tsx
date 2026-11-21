/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useState } from "react";
import { AlertCircle, Network, ShieldPlus } from "lucide-react";
import { Modal } from "../../../components/ui/Modal";
import { GatewayService } from "../../../services/gatewayService";
import { AddIpWhitelistPayload } from "../../../types/gateway";

interface AddIpWhitelistModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const AddIpWhitelistModal: React.FC<AddIpWhitelistModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [cidr, setCidr] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const cleanCidr = cidr.trim();
    const cleanDesc = description.trim();

    if (!cleanCidr || !cleanDesc) {
      setErrorMessage("Please fill in both CIDR subnet and description.");
      return;
    }

    // Basic client validation (full validation on backend via ipaddress)
    if (!cleanCidr.includes("/")) {
      setErrorMessage("Network block must include CIDR prefix length, e.g. 192.168.10.0/24 (Rule E-SYS-02).");
      return;
    }

    const payload: AddIpWhitelistPayload = {
      cidr: cleanCidr,
      description: cleanDesc,
    };

    setIsSubmitting(true);
    try {
      await GatewayService.addIpWhitelist(payload);
      setCidr("");
      setDescription("");
      onSuccess();
      onClose();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Failed to add CIDR whitelist.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setCidr("");
    setDescription("");
    setErrorMessage(null);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Authorize Exam Room Subnet (CIDR Whitelist)" maxWidth="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        {errorMessage && (
          <div className="flex items-start gap-2.5 p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-sm">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        <div>
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
            CIDR Network Block <span className="text-rose-500">*</span>
          </label>
          <div className="relative">
            <input
              type="text"
              required
              value={cidr}
              onChange={(e) => setCidr(e.target.value)}
              placeholder="e.g. 192.168.10.0/24 or 10.0.50.0/22"
              className="w-full pl-9 pr-3.5 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all font-mono"
            />
            <Network className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            Exam candidates will only be permitted to submit attempts from these verified hardware subnets (Rule BR-SYS-04).
          </p>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
            Hall / Location Description <span className="text-rose-500">*</span>
          </label>
          <input
            type="text"
            required
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="e.g. Computer Science Lab Hall B3-201"
            className="w-full px-3.5 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          />
        </div>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
          <button
            type="button"
            onClick={handleClose}
            className="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 rounded-pill transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="inline-flex items-center gap-2 px-5 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-pill shadow-brand transition-all"
          >
            <ShieldPlus className="w-4 h-4" />
            {isSubmitting ? "Registering..." : "Register CIDR"}
          </button>
        </div>
      </form>
    </Modal>
  );
};
