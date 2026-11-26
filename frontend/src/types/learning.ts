/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

export type MaterialType = "SLIDE" | "PDF" | "VIDEO" | "DOCUMENT";

export interface LearningMaterial {
  id: string;
  module_id: string;
  lo_id?: string | null;
  lo_code?: string | null;
  title: string;
  material_type: MaterialType;
  file_url?: string | null;
  is_mandatory: boolean;
  est_duration_minutes: number;
  is_published: boolean;
  created_at: string;
}

export interface LearningModule {
  id: string;
  course_id: string;
  title: string;
  order_index: number;
  unlock_at?: string | null;
  prerequisite_module_id?: string | null;
  prerequisite_title?: string | null;
  is_published: boolean;
  is_locked: boolean;
  lock_reason?: string | null;
  created_at: string;
  materials: LearningMaterial[];
}

export interface ModuleCreatePayload {
  title: string;
  order_index?: number;
  unlock_at?: string | null;
  prerequisite_module_id?: string | null;
  is_published?: boolean;
}

export interface ModuleUpdatePayload {
  title?: string;
  order_index?: number;
  unlock_at?: string | null;
  prerequisite_module_id?: string | null;
  is_published?: boolean;
}

export interface MaterialCreatePayload {
  title: string;
  material_type: MaterialType;
  lo_id?: string | null;
  file_url?: string | null;
  is_mandatory?: boolean;
  est_duration_minutes?: number;
  is_published?: boolean;
}

export interface MaterialUpdatePayload {
  title?: string;
  material_type?: MaterialType;
  lo_id?: string | null;
  file_url?: string | null;
  is_mandatory?: boolean;
  est_duration_minutes?: number;
  is_published?: boolean;
}

export interface MaterialUploadResult {
  file_url: string;
  file_name: string;
  size_bytes: number;
  material_type: MaterialType;
}
