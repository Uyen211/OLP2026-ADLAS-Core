/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useState } from "react";
import { AlertCircle } from "lucide-react";
import { courseService } from "../../../../services/courseService";
import { ApiError } from "../../../../services/httpClient";
import type { BloomLevel, LOResponse } from "../../../../types/course";
import { FormField, mmInputClass } from "../../components/FormField";
import { MmButton } from "../../components/MmButton";
import { MmModal } from "../../components/MmModal";
import { showToast } from "../../components/Toast";

const BLOOM_OPTIONS: Array<{ value: BloomLevel; label: string }> = [
  { value: "REMEMBER", label: "Nhận biết (Remember)" },
  { value: "UNDERSTAND", label: "Thông hiểu (Understand)" },
  { value: "APPLY", label: "Vận dụng (Apply)" },
  { value: "ANALYZE", label: "Phân tích (Analyze)" },
  { value: "EVALUATE", label: "Đánh giá (Evaluate)" },
  { value: "CREATE", label: "Sáng tạo (Create)" },
];

export interface LoFormModalProps {
  open: boolean;
  courseId: string;
  editingLo?: LOResponse | null;
  onClose: () => void;
  onSaved: (lo: LOResponse) => void;
}

export const LoFormModal: React.FC<LoFormModalProps> = ({
  open,
  courseId,
  editingLo,
  onClose,
  onSaved,
}) => {
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [detailDescription, setDetailDescription] = useState("");
  const [weightPercent, setWeightPercent] = useState("");
  const [bloomLevel, setBloomLevel] = useState<BloomLevel>("UNDERSTAND");
  const [loading, setLoading] = useState(false);
  const [codeError, setCodeError] = useState<string | null>(null);
  const [descError, setDescError] = useState<string | null>(null);
  const [weightError, setWeightError] = useState<string | null>(null);
  const [bannerError, setBannerError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    if (editingLo) {
      setCode(editingLo.code);
      setDescription(editingLo.description);
      setDetailDescription(editingLo.detail_description ?? "");
      setWeightPercent(
        editingLo.weight_percent !== null && editingLo.weight_percent !== undefined
          ? String(editingLo.weight_percent)
          : ""
      );
      setBloomLevel(editingLo.bloom_level);
    } else {
      setCode("");
      setDescription("");
      setDetailDescription("");
      setWeightPercent("");
      setBloomLevel("UNDERSTAND");
    }
    setCodeError(null);
    setDescError(null);
    setWeightError(null);
    setBannerError(null);
  }, [open, editingLo]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const cleanedCode = code.trim().toUpperCase();
    const cleanedDesc = description.trim();
    const cleanedDetail = detailDescription.trim();

    let hasErr = false;
    if (!/^[A-Za-z0-9-]{2,30}$/.test(cleanedCode)) {
      setCodeError("Mã chuẩn đầu ra gồm 2-30 ký tự chữ, số hoặc dấu gạch ngang (vd: LO-01).");
      hasErr = true;
    } else {
      setCodeError(null);
    }

    if (cleanedDesc.length < 10 || cleanedDesc.length > 150) {
      setDescError("Tên chuẩn đầu ra phải có độ dài từ 10 đến 150 ký tự.");
      hasErr = true;
    } else {
      setDescError(null);
    }

    let parsedWeight: number | null = null;
    if (weightPercent.trim() !== "") {
      const numeric = Number(weightPercent);
      if (Number.isNaN(numeric) || numeric < 0 || numeric > 100) {
        setWeightError("Trọng số đóng góp phải nằm trong khoảng 0 đến 100%.");
        hasErr = true;
      } else {
        parsedWeight = numeric;
        setWeightError(null);
      }
    } else {
      setWeightError(null);
    }

    if (hasErr) return;

    setBannerError(null);
    setLoading(true);

    try {
      const saved = editingLo
        ? await courseService.updateLearningObjective(courseId, editingLo.id, {
            code: cleanedCode,
            description: cleanedDesc,
            detail_description: cleanedDetail || null,
            weight_percent: parsedWeight,
            bloom_level: bloomLevel,
          })
        : await courseService.createLearningObjective(courseId, {
            code: cleanedCode,
            description: cleanedDesc,
            detail_description: cleanedDetail || null,
            weight_percent: parsedWeight,
            bloom_level: bloomLevel,
          });
      showToast(
        "success",
        editingLo
          ? `Đã cập nhật chuẩn đầu ra ${saved.code}.`
          : `Đã thêm chuẩn đầu ra ${saved.code} thành công!`
      );
      onSaved(saved);
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === "E-4" || err.field === "code") {
          setCodeError(`Mã chuẩn đầu ra "${cleanedCode}" đã tồn tại trong môn học này.`);
        } else {
          setBannerError(err.message);
        }
      } else {
        setBannerError("Không thể lưu chuẩn đầu ra. Vui lòng thử lại.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <MmModal
      open={open}
      title={editingLo ? "Chỉnh sửa Chuẩn đầu ra (LO)" : "Thêm Chuẩn đầu ra (LO) mới"}
      subtitle="Định nghĩa chuẩn đầu ra theo thang nhận thức Bloom"
      onClose={onClose}
      footer={
        <>
          <MmButton variant="secondary" onClick={onClose} disabled={loading}>
            Hủy bỏ
          </MmButton>
          <MmButton type="submit" form="lo-form" variant="brand" loading={loading}>
            {editingLo ? "Lưu thay đổi" : "Thêm chuẩn đầu ra"}
          </MmButton>
        </>
      }
    >
      {bannerError && (
        <div
          role="alert"
          className="mb-4 flex items-start gap-2 rounded-mm-panel border border-mm-danger/30 bg-mm-danger-bg px-3.5 py-2.5 text-mm-danger"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span className="font-mm-ui text-sm">{bannerError}</span>
        </div>
      )}

      <form id="lo-form" onSubmit={handleSubmit} noValidate className="space-y-4">
        <FormField
          label="Mã chuẩn đầu ra"
          htmlFor="lo-code"
          required
          error={codeError}
          helper="Ví dụ: LO-01, CLO-2"
        >
          <input
            id="lo-code"
            type="text"
            value={code}
            onChange={(e) => {
              setCode(e.target.value.toUpperCase());
              if (codeError) setCodeError(null);
            }}
            placeholder="LO-01"
            className={mmInputClass(Boolean(codeError))}
          />
        </FormField>

        <FormField
          label="Tên chuẩn đầu ra (10 - 150 ký tự)"
          htmlFor="lo-description"
          required
          error={descError}
          helper={`Độ dài hiện tại: ${description.trim().length}/150 ký tự`}
        >
          <textarea
            id="lo-description"
            rows={3}
            maxLength={150}
            value={description}
            onChange={(e) => {
              setDescription(e.target.value);
              if (descError) setDescError(null);
            }}
            placeholder="vd: Vận dụng được thuật toán tìm đường đi ngắn nhất trên đồ thị có trọng số"
            className={mmInputClass(Boolean(descError))}
          />
        </FormField>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField label="Mức độ nhận thức Bloom" htmlFor="lo-bloom" required>
            <select
              id="lo-bloom"
              value={bloomLevel}
              onChange={(e) => setBloomLevel(e.target.value as BloomLevel)}
              className={mmInputClass(false)}
            >
              {BLOOM_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </FormField>

          <FormField
            label="Trọng số đóng góp (%)"
            htmlFor="lo-weight"
            error={weightError}
            helper="Tùy chọn, từ 0 đến 100%"
          >
            <input
              id="lo-weight"
              type="number"
              min={0}
              max={100}
              step="0.5"
              value={weightPercent}
              onChange={(e) => {
                setWeightPercent(e.target.value);
                if (weightError) setWeightError(null);
              }}
              placeholder="vd: 25"
              className={mmInputClass(Boolean(weightError))}
            />
          </FormField>
        </div>

        <FormField
          label="Mô tả chi tiết (tùy chọn)"
          htmlFor="lo-detail-description"
          helper="Nhập yêu cầu cụ thể đối với sinh viên khi đánh giá chuẩn đầu ra này"
        >
          <textarea
            id="lo-detail-description"
            rows={2}
            maxLength={1000}
            value={detailDescription}
            onChange={(e) => setDetailDescription(e.target.value)}
            placeholder="vd: Sinh viên triển khai được API có xác thực JWT và kiểm thử tự động đạt 80% coverage"
            className={mmInputClass(false)}
          />
        </FormField>
      </form>
    </MmModal>
  );
};
