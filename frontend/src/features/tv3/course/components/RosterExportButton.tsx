// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React, { useState } from "react";
import { Download } from "lucide-react";
import { EduButton } from "../../../../design-system";
import { courseService } from "../../../../services/courseService";

export interface RosterExportButtonProps {
  courseId: string;
  courseCode?: string;
  className?: string;
}

export const RosterExportButton: React.FC<RosterExportButtonProps> = ({
  courseId,
  courseCode = "lop-hoc",
  className = "",
}) => {
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = async () => {
    setIsExporting(true);
    try {
      await courseService.exportRosterXlsx(courseId, `danh-sach-lop-${courseCode}.xlsx`);
    } catch (err: any) {
      alert("Xuất danh sách sinh viên không thành công. Vui lòng kiểm tra quyền giảng viên.");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <EduButton
      variant="secondary"
      size="sm"
      onClick={handleExport}
      isLoading={isExporting}
      leftIcon={<Download className="w-4 h-4" aria-hidden="true" />}
      className={className}
    >
      Xuất Excel (.xlsx)
    </EduButton>
  );
};
