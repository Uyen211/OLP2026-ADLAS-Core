// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React from "react";
import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export interface PageHeaderProps {
  breadcrumbs?: BreadcrumbItem[];
  title: string;
  description?: string;
  actions?: React.ReactNode;
  badge?: React.ReactNode;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  breadcrumbs,
  title,
  description,
  actions,
  badge,
}) => {
  return (
    <div className="w-full mb-6 pb-5 border-b border-[rgba(15,34,54,0.08)]">
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs text-[#4a5f75] mb-2.5">
          {breadcrumbs.map((crumb, idx) => (
            <React.Fragment key={idx}>
              {idx > 0 && <ChevronRight className="w-3.5 h-3.5 text-[#94a3b8] shrink-0" aria-hidden="true" />}
              {crumb.href ? (
                <Link
                  to={crumb.href}
                  className="hover:text-[#0f2236] transition-colors font-medium truncate max-w-[200px]"
                >
                  {crumb.label}
                </Link>
              ) : (
                <span className="font-semibold text-[#0f2236] truncate max-w-[200px]" aria-current="page">
                  {crumb.label}
                </span>
              )}
            </React.Fragment>
          ))}
        </nav>
      )}

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#0f2236] font-['Space_Grotesk']">
              {title}
            </h1>
            {badge}
          </div>
          {description && (
            <p className="text-sm sm:text-base text-[#4a5f75] mt-1.5 max-w-3xl leading-relaxed">
              {description}
            </p>
          )}
        </div>

        {actions && <div className="flex items-center gap-3 shrink-0">{actions}</div>}
      </div>
    </div>
  );
};
