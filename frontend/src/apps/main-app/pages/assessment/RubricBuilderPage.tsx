/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { clsx } from "clsx";
import {
  AlertCircle,
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  CheckCircle2,
  ClipboardList,
  Lock,
  Plus,
  Save,
  Sparkles,
  Trash2,
} from "lucide-react";
import { assessmentService } from "../../../../services/assessmentService";
import { courseService } from "../../../../services/courseService";
import { ApiError } from "../../../../services/httpClient";
import type {
  AssignmentDetail,
  MasteryLevelCode,
  MasteryLevelItem,
  RubricCriterionPayload,
  RubricResponse,
} from "../../../../types/assessment";
import type { LOResponse } from "../../../../types/course";
import { FormField, mmInputClass } from "../../components/FormField";
import { MmButton } from "../../components/MmButton";
import { MmCard } from "../../components/MmCard";
import { showToast } from "../../components/Toast";
import { TeacherLayout } from "../../layouts/TeacherLayout";

const MASTERY_META: Array<{
  level: MasteryLevelCode;
  label: string;
  ratio: number;
  headerClass: string;
  placeholder: string;
}> = [
  {
    level: "EXCELLENT",
    label: "Xuất sắc",
    ratio: 1,
    headerClass: "bg-mm-success-bg/70 text-mm-success border-mm-success/20",
    placeholder: "Mô tả biểu hiện hoàn hảo, vượt chuẩn mong đợi...",
  },
  {
    level: "GOOD",
    label: "Khá / Giỏi",
    ratio: 0.8,
    headerClass: "bg-mm-blue-light/30 text-mm-blue-deep border-mm-blue-hover/20",
    placeholder: "Mô tả biểu hiện tốt, còn thiếu sót nhỏ không đáng kể...",
  },
  {
    level: "PROFICIENT",
    label: "Đạt chuẩn cơ bản",
    ratio: 0.6,
    headerClass: "bg-mm-warning-bg/70 text-mm-warning border-mm-warning/20",
    placeholder: "Mô tả mức đáp ứng yêu cầu tối thiểu của chuẩn đầu ra...",
  },
  {
    level: "INSUFFICIENT",
    label: "Chưa đạt",
    ratio: 0,
    headerClass: "bg-mm-danger-bg/70 text-mm-danger border-mm-danger/20",
    placeholder: "Mô tả trường hợp thiếu nội dung cốt lõi hoặc sai bản chất...",
  },
];

const EBAF_COMPETENCY_OPTIONS: Array<{ code: string; label: string }> = [
  { code: "C1", label: "C1 — Kiến thức nền tảng" },
  { code: "C2", label: "C2 — Phân tích & Thiết kế" },
  { code: "C3", label: "C3 — Kỹ năng thực hành & Triển khai" },
  { code: "C4", label: "C4 — Kiểm thử & Đảm bảo chất lượng" },
  { code: "C5", label: "C5 — Tư duy phản biện & Tự chủ" },
  { code: "C6", label: "C6 — Giao tiếp & Hợp tác nhóm" },
  { code: "C7", label: "C7 — Liêm chính học thuật & Đạo đức nghề nghiệp" },
];

interface EditableCriterion {
  _key: string;
  title: string;
  description: string;
  lo_id: string;
  competency_code: string;
  max_points: number;
  rating_levels: MasteryLevelItem[];
}

function roundTenth(value: number): number {
  return Math.round(value * 10) / 10;
}

function buildDefaultLevels(maxPoints: number): MasteryLevelItem[] {
  const safeMax = Math.max(0, roundTenth(maxPoints));
  return MASTERY_META.map((meta) => ({
    level: meta.level,
    label: meta.label,
    description: "",
    points: roundTenth(safeMax * meta.ratio),
  }));
}

function normalizeLevels(
  rawLevels: MasteryLevelItem[] | undefined,
  maxPoints: number
): MasteryLevelItem[] {
  const byCode = new Map<MasteryLevelCode, MasteryLevelItem>();
  for (const item of rawLevels ?? []) {
    byCode.set(item.level, item);
  }
  return MASTERY_META.map((meta) => {
    const existing = byCode.get(meta.level);
    return {
      level: meta.level,
      label: existing?.label || meta.label,
      description: existing?.description ?? "",
      points:
        existing !== undefined
          ? roundTenth(Number(existing.points) || 0)
          : roundTenth(maxPoints * meta.ratio),
    };
  });
}

function createEmptyCriterion(index: number, suggestedPoints: number): EditableCriterion {
  const pts = suggestedPoints > 0 ? roundTenth(suggestedPoints) : 2.5;
  return {
    _key: `criterion-${Date.now()}-${index}-${Math.random().toString(36).slice(2, 7)}`,
    title: "",
    description: "",
    lo_id: "",
    competency_code: "",
    max_points: pts,
    rating_levels: buildDefaultLevels(pts),
  };
}

export const RubricBuilderPage: React.FC = () => {
  const { courseId = "", assignmentId = "" } = useParams<{
    courseId: string;
    assignmentId: string;
  }>();

  const [assignment, setAssignment] = useState<AssignmentDetail | null>(null);
  const [rubricMeta, setRubricMeta] = useState<RubricResponse | null>(null);
  const [learningObjectives, setLearningObjectives] = useState<LOResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [rubricTitle, setRubricTitle] = useState("Bảng tiêu chí đánh giá (Rubric)");
  const [criteria, setCriteria] = useState<EditableCriterion[]>([]);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!courseId || !assignmentId) return;
    setLoading(true);
    setErrorBanner(null);
    try {
      const [detail, rubric, los] = await Promise.all([
        assessmentService.getAssignmentDetail(assignmentId),
        assessmentService.getRubric(assignmentId),
        courseService.listLearningObjectives(courseId).catch(() => [] as LOResponse[]),
      ]);
      setAssignment(detail);
      setRubricMeta(rubric);
      setLearningObjectives(los);

      if (rubric.exists && rubric.criteria.length > 0) {
        setRubricTitle(rubric.title || "Bảng tiêu chí đánh giá (Rubric)");
        setCriteria(
          rubric.criteria.map((c, idx) => ({
            _key: c.id || `loaded-${idx}`,
            title: c.title,
            description: c.description ?? "",
            lo_id: c.lo_id ?? "",
            competency_code: c.competency_code ?? "",
            max_points: roundTenth(Number(c.max_points) || 0),
            rating_levels: normalizeLevels(c.rating_levels, Number(c.max_points) || 0),
          }))
        );
      } else {
        setRubricTitle(`Rubric — ${detail.title}`);
        setCriteria([
          createEmptyCriterion(1, 4.0),
          createEmptyCriterion(2, 3.0),
          createEmptyCriterion(3, 3.0),
        ]);
      }
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : "Không thể tải dữ liệu bảng tiêu chí Rubric.";
      setErrorBanner(msg);
      showToast("error", msg);
    } finally {
      setLoading(false);
    }
  }, [courseId, assignmentId]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  // Tính tổng điểm bằng số nguyên phần mười để khớp tuyệt đối Decimal("10.0") ở Backend
  const totalTenths = useMemo(
    () =>
      criteria.reduce(
        (sum, item) => sum + Math.round((Number(item.max_points) || 0) * 10),
        0
      ),
    [criteria]
  );
  const totalPoints = totalTenths / 10;
  const isTotalExact = totalTenths === 100;
  const submissionCount = rubricMeta?.submission_count ?? 0;
  const isFrozen = Boolean(rubricMeta?.is_frozen) || submissionCount > 0;
  const progressPct = Math.min(100, Math.max(0, (totalPoints / 10) * 100));

  const updateCriterion = (
    key: string,
    updater: (prev: EditableCriterion) => EditableCriterion
  ) => {
    if (isFrozen) return;
    setCriteria((prev) =>
      prev.map((item) => (item._key === key ? updater(item) : item))
    );
  };

  const handleAddCriterion = () => {
    if (isFrozen) return;
    const remaining = roundTenth(Math.max(0.5, 10 - totalPoints));
    setCriteria((prev) => [...prev, createEmptyCriterion(prev.length + 1, remaining)]);
  };

  const handleRemoveCriterion = (key: string) => {
    if (isFrozen) return;
    setCriteria((prev) => prev.filter((item) => item._key !== key));
  };

  const handleMoveCriterion = (index: number, direction: -1 | 1) => {
    if (isFrozen) return;
    const targetIdx = index + direction;
    setCriteria((prev) => {
      if (targetIdx < 0 || targetIdx >= prev.length) return prev;
      const next = [...prev];
      const [moved] = next.splice(index, 1);
      next.splice(targetIdx, 0, moved);
      return next;
    });
  };

  const handleAutoDistributeLevels = (key: string) => {
    if (isFrozen) return;
    updateCriterion(key, (item) => ({
      ...item,
      rating_levels: item.rating_levels.map((lv) => {
        const meta = MASTERY_META.find((m) => m.level === lv.level);
        return {
          ...lv,
          points: roundTenth(item.max_points * (meta?.ratio ?? 0)),
        };
      }),
    }));
  };

  const handleSave = async () => {
    if (isFrozen) {
      showToast(
        "error",
        "E-RUB-02: Bảng Rubric đã bị đóng băng do đã có bài nộp của sinh viên."
      );
      return;
    }

    const cleanedTitle = rubricTitle.trim();
    if (!cleanedTitle) {
      setErrorBanner("Vui lòng nhập tên bảng Rubric.");
      return;
    }

    if (criteria.length === 0) {
      setErrorBanner("Bảng Rubric phải có ít nhất 1 tiêu chí đánh giá.");
      return;
    }

    if (!isTotalExact) {
      setErrorBanner(
        `E-RUB-01: Tổng điểm các tiêu chí phải đạt đúng 10.0 điểm (hiện tại ${totalPoints.toFixed(
          1
        )} điểm).`
      );
      return;
    }

    for (let i = 0; i < criteria.length; i += 1) {
      const c = criteria[i];
      if (!c.title.trim()) {
        setErrorBanner(`Vui lòng nhập tên cho Tiêu chí #${i + 1}.`);
        return;
      }
      if (!c.max_points || c.max_points <= 0) {
        setErrorBanner(`Điểm tối đa của Tiêu chí #${i + 1} phải lớn hơn 0.`);
        return;
      }
      for (const lv of c.rating_levels) {
        if (lv.points < 0 || lv.points > c.max_points) {
          setErrorBanner(
            `Điểm các mức độ của Tiêu chí #${i + 1} phải nằm trong khoảng từ 0 đến ${c.max_points.toFixed(
              1
            )}.`
          );
          return;
        }
      }
    }

    setErrorBanner(null);
    setSaving(true);

    try {
      const payloadCriteria: RubricCriterionPayload[] = criteria.map((c) => ({
        title: c.title.trim(),
        description: c.description.trim() || null,
        lo_id: c.lo_id || null,
        competency_code: c.competency_code || null,
        max_points: roundTenth(c.max_points),
        rating_levels: c.rating_levels.map((lv) => ({
          level: lv.level,
          label: lv.label || undefined,
          description: lv.description.trim(),
          points: roundTenth(lv.points),
        })),
      }));

      const saved = await assessmentService.saveRubric(assignmentId, {
        title: cleanedTitle,
        criteria: payloadCriteria,
      });
      setRubricMeta(saved);
      setCriteria(
        saved.criteria.map((c, idx) => ({
          _key: c.id || `saved-${idx}`,
          title: c.title,
          description: c.description ?? "",
          lo_id: c.lo_id ?? "",
          competency_code: c.competency_code ?? "",
          max_points: roundTenth(Number(c.max_points) || 0),
          rating_levels: normalizeLevels(c.rating_levels, Number(c.max_points) || 0),
        }))
      );
      showToast(
        "success",
        `Đã lưu bảng Rubric (Phiên bản v${saved.version}) thành công.`
      );
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : "Không thể lưu bảng Rubric. Vui lòng thử lại.";
      setErrorBanner(msg);
      showToast("error", msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <TeacherLayout>
      {loading ? (
        <div className="space-y-4">
          <div className="h-10 w-72 animate-pulse rounded-mm-btn bg-mm-divider" />
          <div className="h-28 animate-pulse rounded-mm-card bg-mm-divider/60" />
          <div className="h-80 animate-pulse rounded-mm-card bg-mm-divider/50" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Thanh điều hướng & Tiêu đề trang */}
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-1.5">
              <Link
                to={`/courses/${courseId}/assignments/${assignmentId}`}
                className="inline-flex items-center gap-1.5 font-mm-ui text-sm font-medium text-mm-text-secondary transition-colors hover:text-mm-heading"
              >
                <ArrowLeft className="h-4 w-4" />
                <span>Quay lại chi tiết bài tập</span>
              </Link>
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="font-mm-display text-2xl font-semibold text-mm-heading">
                  Thiết kế Bảng Tiêu chí Chấm Điểm (Rubric)
                </h1>
                {rubricMeta?.exists && (
                  <span className="rounded-full bg-mm-btn-secondary px-3 py-1 font-mm-data text-xs font-medium text-mm-text-secondary">
                    Phiên bản v{rubricMeta.version}
                  </span>
                )}
              </div>
              {assignment && (
                <p className="font-mm-ui text-sm text-mm-text-secondary">
                  Bài tập: <span className="font-medium text-mm-heading">{assignment.title}</span>
                </p>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2.5">
              {!isFrozen && (
                <MmButton variant="secondary" onClick={handleAddCriterion} disabled={saving}>
                  <Plus className="h-4 w-4" />
                  <span>Thêm tiêu chí</span>
                </MmButton>
              )}
              <MmButton
                variant="brand"
                loading={saving}
                disabled={isFrozen || !isTotalExact || criteria.length === 0}
                onClick={() => void handleSave()}
              >
                <Save className="h-4 w-4" />
                <span>Lưu bảng Rubric</span>
              </MmButton>
            </div>
          </div>

          {/* Cảnh báo đóng băng E-RUB-02 */}
          {isFrozen && (
            <div
              role="status"
              className="flex items-start gap-3 rounded-mm-card border border-mm-warning/40 bg-mm-warning-bg px-5 py-4 text-mm-warning"
            >
              <Lock className="mt-0.5 h-5 w-5 shrink-0" />
              <div className="space-y-1">
                <p className="font-mm-mid text-sm font-semibold">
                  Bảng Rubric đã khóa (Đang áp dụng chấm cho {submissionCount} bài nộp)
                </p>
                <p className="font-mm-ui text-xs">
                  Theo quy tắc nghiệp vụ BR-RUB-02 (E-RUB-02), bảng tiêu chí tự động chuyển sang chế độ chỉ đọc ngay khi có bài nộp đầu tiên nhằm đảm bảo công bằng đánh giá.
                </p>
              </div>
            </div>
          )}

          {/* Thanh tổng điểm thời gian thực BR-RUB-01 / E-RUB-01 */}
          <MmCard variant="standard" padding="md" className="sticky top-4 z-10 bg-mm-bg">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2.5">
                  <ClipboardList className="h-4 w-4 text-mm-blue-hover" />
                  <span className="font-mm-mid text-sm font-medium text-mm-heading">
                    Tổng điểm thời gian thực:
                  </span>
                  <span
                    className={clsx(
                      "font-mm-data text-lg font-semibold",
                      isTotalExact ? "text-mm-success" : "text-mm-danger"
                    )}
                  >
                    {totalPoints.toFixed(1)} / 10.0 điểm
                  </span>
                </div>
                <p className="font-mm-ui text-xs text-mm-text-secondary">
                  {criteria.length} tiêu chí đánh giá · Ma trận chuẩn 4 mức độ năng lực (Xuất sắc, Khá / Giỏi, Đạt chuẩn cơ bản, Chưa đạt)
                </p>
              </div>

              {isTotalExact ? (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-mm-success-bg px-3.5 py-1.5 font-mm-ui text-xs font-medium text-mm-success">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Hợp lệ — Tổng điểm đạt đúng 10.0</span>
                </span>
              ) : (
                <span
                  role="alert"
                  className="inline-flex items-center gap-1.5 rounded-full bg-mm-danger-bg px-3.5 py-1.5 font-mm-ui text-xs font-medium text-mm-danger"
                >
                  <AlertCircle className="h-4 w-4" />
                  <span>
                    E-RUB-01: Tổng điểm phải đúng 10.0 (
                    {totalPoints < 10
                      ? `còn thiếu ${(10 - totalPoints).toFixed(1)} điểm`
                      : `đang dư ${(totalPoints - 10).toFixed(1)} điểm`}
                    )
                  </span>
                </span>
              )}
            </div>

            <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-mm-divider">
              <div
                className={clsx(
                  "h-full rounded-full transition-all duration-200",
                  isTotalExact
                    ? "bg-mm-success"
                    : totalPoints > 10
                      ? "bg-mm-danger"
                      : "bg-mm-blue-hover"
                )}
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </MmCard>

          {errorBanner && (
            <div
              role="alert"
              className="flex items-start gap-2.5 rounded-mm-panel border border-mm-danger/30 bg-mm-danger-bg px-4 py-3 text-mm-danger"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span className="font-mm-ui text-sm">{errorBanner}</span>
            </div>
          )}

          {/* Tên bảng Rubric */}
          <MmCard variant="standard" padding="md">
            <FormField
              label="Tên bảng tiêu chí đánh giá (Rubric)"
              htmlFor="rubric-title-input"
              required
            >
              <input
                id="rubric-title-input"
                type="text"
                maxLength={200}
                value={rubricTitle}
                disabled={isFrozen}
                readOnly={isFrozen}
                onChange={(e) => setRubricTitle(e.target.value)}
                placeholder="Ví dụ: Bảng Rubric chấm Đồ án giữa kỳ"
                className={clsx(
                  mmInputClass(false),
                  isFrozen && "cursor-not-allowed bg-mm-divider/40 text-mm-text-secondary"
                )}
              />
            </FormField>
          </MmCard>

          {/* Danh sách tiêu chí */}
          <div className="space-y-4">
            {criteria.length === 0 ? (
              <MmCard variant="standard" className="py-12 text-center">
                <p className="font-mm-ui text-sm text-mm-text-secondary">
                  Chưa có tiêu chí đánh giá nào. Hãy thêm tiêu chí để xây dựng bảng Rubric tổng 10.0 điểm.
                </p>
                {!isFrozen && (
                  <MmButton
                    variant="secondary"
                    className="mt-4"
                    onClick={handleAddCriterion}
                  >
                    <Plus className="h-4 w-4" />
                    <span>Thêm tiêu chí đầu tiên</span>
                  </MmButton>
                )}
              </MmCard>
            ) : (
              criteria.map((criterion, index) => (
                <MmCard
                  key={criterion._key}
                  variant="standard"
                  padding="lg"
                  className="space-y-5"
                >
                  {/* Header của từng tiêu chí */}
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-mm-divider pb-3">
                    <div className="flex items-center gap-2.5">
                      <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-mm-btn-secondary font-mm-data text-xs font-semibold text-mm-heading">
                        {index + 1}
                      </span>
                      <h2 className="font-mm-display text-base font-semibold text-mm-heading">
                        Tiêu chí #{index + 1}
                      </h2>
                      <span className="rounded-full bg-mm-blue-light/30 px-2.5 py-0.5 font-mm-data text-xs font-medium text-mm-blue-deep">
                        Tối đa {criterion.max_points.toFixed(1)} điểm
                      </span>
                    </div>

                    {!isFrozen && (
                      <div className="flex flex-wrap items-center gap-1.5">
                        <MmButton
                          variant="ghost"
                          size="sm"
                          onClick={() => handleAutoDistributeLevels(criterion._key)}
                          title="Tự động phân bổ điểm 4 mức theo tỷ lệ 100% / 80% / 60% / 0%"
                        >
                          <Sparkles className="h-3.5 w-3.5" />
                          <span>Phân bổ điểm 4 mức</span>
                        </MmButton>
                        <button
                          type="button"
                          title="Di chuyển lên"
                          disabled={index === 0}
                          onClick={() => handleMoveCriterion(index, -1)}
                          className="rounded-mm-btn border border-mm-border p-1.5 text-mm-text-secondary transition-colors hover:bg-mm-divider disabled:opacity-35"
                        >
                          <ArrowUp className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          title="Di chuyển xuống"
                          disabled={index === criteria.length - 1}
                          onClick={() => handleMoveCriterion(index, 1)}
                          className="rounded-mm-btn border border-mm-border p-1.5 text-mm-text-secondary transition-colors hover:bg-mm-divider disabled:opacity-35"
                        >
                          <ArrowDown className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          title="Xóa tiêu chí"
                          disabled={criteria.length <= 1}
                          onClick={() => handleRemoveCriterion(criterion._key)}
                          className="rounded-mm-btn border border-mm-border p-1.5 text-mm-danger transition-colors hover:bg-mm-danger-bg disabled:opacity-35"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Thông tin tiêu chí: Tên, Điểm tối đa, LO, Mã năng lực */}
                  <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
                    <div className="lg:col-span-5">
                      <FormField
                        label="Tên tiêu chí đánh giá"
                        htmlFor={`criterion-title-${criterion._key}`}
                        required
                      >
                        <input
                          id={`criterion-title-${criterion._key}`}
                          type="text"
                          maxLength={200}
                          value={criterion.title}
                          disabled={isFrozen}
                          readOnly={isFrozen}
                          onChange={(e) =>
                            updateCriterion(criterion._key, (prev) => ({
                              ...prev,
                              title: e.target.value,
                            }))
                          }
                          placeholder="Ví dụ: Thiết kế kiến trúc hệ thống và cơ sở dữ liệu"
                          className={clsx(
                            mmInputClass(false),
                            isFrozen && "cursor-not-allowed bg-mm-divider/40"
                          )}
                        />
                      </FormField>
                    </div>

                    <div className="lg:col-span-3">
                      <FormField
                        label="Chuẩn đầu ra (LO) gắn kết"
                        htmlFor={`criterion-lo-${criterion._key}`}
                      >
                        <select
                          id={`criterion-lo-${criterion._key}`}
                          value={criterion.lo_id}
                          disabled={isFrozen}
                          onChange={(e) =>
                            updateCriterion(criterion._key, (prev) => ({
                              ...prev,
                              lo_id: e.target.value,
                            }))
                          }
                          className={clsx(
                            mmInputClass(false),
                            isFrozen && "cursor-not-allowed bg-mm-divider/40"
                          )}
                        >
                          <option value="">-- Chưa gắn LO --</option>
                          {learningObjectives.map((lo) => (
                            <option key={lo.id} value={lo.id}>
                              {lo.code} — {lo.description}
                            </option>
                          ))}
                        </select>
                      </FormField>
                    </div>

                    <div className="lg:col-span-2">
                      <FormField
                        label="Mã năng lực EBAF"
                        htmlFor={`criterion-comp-${criterion._key}`}
                      >
                        <select
                          id={`criterion-comp-${criterion._key}`}
                          value={criterion.competency_code}
                          disabled={isFrozen}
                          onChange={(e) =>
                            updateCriterion(criterion._key, (prev) => ({
                              ...prev,
                              competency_code: e.target.value,
                            }))
                          }
                          className={clsx(
                            mmInputClass(false),
                            isFrozen && "cursor-not-allowed bg-mm-divider/40"
                          )}
                        >
                          <option value="">-- Không chọn --</option>
                          {EBAF_COMPETENCY_OPTIONS.map((opt) => (
                            <option key={opt.code} value={opt.code}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      </FormField>
                    </div>

                    <div className="lg:col-span-2">
                      <FormField
                        label="Điểm tối đa"
                        htmlFor={`criterion-max-${criterion._key}`}
                        required
                      >
                        <input
                          id={`criterion-max-${criterion._key}`}
                          type="number"
                          min={0.5}
                          max={10}
                          step="0.5"
                          value={criterion.max_points}
                          disabled={isFrozen}
                          readOnly={isFrozen}
                          onChange={(e) => {
                            const nextMax = Math.max(
                              0,
                              roundTenth(Number(e.target.value) || 0)
                            );
                            updateCriterion(criterion._key, (prev) => ({
                              ...prev,
                              max_points: nextMax,
                            }));
                          }}
                          className={clsx(
                            mmInputClass(false),
                            "font-mm-data",
                            isFrozen && "cursor-not-allowed bg-mm-divider/40"
                          )}
                        />
                      </FormField>
                    </div>
                  </div>

                  {/* Ma trận 4 mức độ Mastery */}
                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
                    {MASTERY_META.map((meta) => {
                      const lv =
                        criterion.rating_levels.find(
                          (item) => item.level === meta.level
                        ) ?? {
                          level: meta.level,
                          label: meta.label,
                          description: "",
                          points: 0,
                        };
                      const levelInvalid =
                        lv.points < 0 || lv.points > criterion.max_points;

                      return (
                        <div
                          key={meta.level}
                          className="flex flex-col gap-2.5 rounded-mm-panel border border-mm-border bg-mm-bg p-3.5"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span
                              className={clsx(
                                "rounded-full border px-2.5 py-0.5 font-mm-ui text-xs font-medium",
                                meta.headerClass
                              )}
                            >
                              {meta.label}
                            </span>
                            <div className="flex items-center gap-1">
                              <input
                                type="number"
                                aria-label={`Điểm mức ${meta.label} của tiêu chí ${index + 1}`}
                                min={0}
                                max={criterion.max_points}
                                step="0.5"
                                value={lv.points}
                                disabled={isFrozen}
                                readOnly={isFrozen}
                                onChange={(e) => {
                                  const nextPts = roundTenth(
                                    Number(e.target.value) || 0
                                  );
                                  updateCriterion(criterion._key, (prev) => ({
                                    ...prev,
                                    rating_levels: prev.rating_levels.map((item) =>
                                      item.level === meta.level
                                        ? { ...item, points: nextPts }
                                        : item
                                    ),
                                  }));
                                }}
                                className={clsx(
                                  "w-16 rounded-mm-btn border px-2 py-1 text-right font-mm-data text-xs focus:outline-none focus:ring-2",
                                  levelInvalid
                                    ? "border-mm-danger text-mm-danger focus:ring-mm-danger/20"
                                    : "border-mm-border text-mm-heading focus:border-mm-blue-hover focus:ring-mm-blue-hover/20",
                                  isFrozen && "cursor-not-allowed bg-mm-divider/40"
                                )}
                              />
                              <span className="font-mm-ui text-xs text-mm-text-muted">
                                đ
                              </span>
                            </div>
                          </div>

                          <textarea
                            rows={3}
                            maxLength={1000}
                            value={lv.description}
                            disabled={isFrozen}
                            readOnly={isFrozen}
                            onChange={(e) => {
                              const nextDesc = e.target.value;
                              updateCriterion(criterion._key, (prev) => ({
                                ...prev,
                                rating_levels: prev.rating_levels.map((item) =>
                                  item.level === meta.level
                                    ? { ...item, description: nextDesc }
                                    : item
                                ),
                              }));
                            }}
                            placeholder={meta.placeholder}
                            className={clsx(
                              mmInputClass(false),
                              "resize-none text-xs leading-relaxed",
                              isFrozen && "cursor-not-allowed bg-mm-divider/40"
                            )}
                          />
                        </div>
                      );
                    })}
                  </div>
                </MmCard>
              ))
            )}
          </div>
        </div>
      )}
    </TeacherLayout>
  );
};
