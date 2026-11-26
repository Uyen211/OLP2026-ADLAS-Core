/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import type {
  LearningMaterial,
  LearningModule,
  MaterialCreatePayload,
  MaterialUpdatePayload,
  MaterialUploadResult,
  ModuleCreatePayload,
  ModuleUpdatePayload,
} from "../types/learning";
import { httpDownloadBlob, httpFetchBlob, httpRequest } from "./httpClient";

export const learningService = {
  listModules(courseId: string): Promise<LearningModule[]> {
    return httpRequest<LearningModule[]>(`/courses/${courseId}/learning/modules`);
  },

  getModule(courseId: string, moduleId: string): Promise<LearningModule> {
    return httpRequest<LearningModule>(`/courses/${courseId}/learning/modules/${moduleId}`);
  },

  createModule(courseId: string, payload: ModuleCreatePayload): Promise<LearningModule> {
    return httpRequest<LearningModule>(`/courses/${courseId}/learning/modules`, {
      method: "POST",
      body: payload,
    });
  },

  updateModule(
    courseId: string,
    moduleId: string,
    payload: ModuleUpdatePayload
  ): Promise<LearningModule> {
    return httpRequest<LearningModule>(`/courses/${courseId}/learning/modules/${moduleId}`, {
      method: "PUT",
      body: payload,
    });
  },

  deleteModule(courseId: string, moduleId: string): Promise<void> {
    return httpRequest<void>(`/courses/${courseId}/learning/modules/${moduleId}`, {
      method: "DELETE",
    });
  },

  toggleModulePublish(
    courseId: string,
    moduleId: string,
    isPublished: boolean
  ): Promise<LearningModule> {
    return httpRequest<LearningModule>(`/courses/${courseId}/learning/modules/${moduleId}/publish`, {
      method: "PATCH",
      body: { is_published: isPublished },
    });
  },

  reorderModules(courseId: string, moduleIds: string[]): Promise<LearningModule[]> {
    return httpRequest<LearningModule[]>(`/courses/${courseId}/learning/modules/reorder`, {
      method: "PUT",
      body: { module_ids: moduleIds },
    });
  },

  createMaterial(
    courseId: string,
    moduleId: string,
    payload: MaterialCreatePayload
  ): Promise<LearningMaterial> {
    return httpRequest<LearningMaterial>(`/courses/${courseId}/learning/modules/${moduleId}/materials`, {
      method: "POST",
      body: payload,
    });
  },

  updateMaterial(
    courseId: string,
    materialId: string,
    payload: MaterialUpdatePayload
  ): Promise<LearningMaterial> {
    return httpRequest<LearningMaterial>(`/courses/${courseId}/learning/materials/${materialId}`, {
      method: "PUT",
      body: payload,
    });
  },

  deleteMaterial(courseId: string, materialId: string): Promise<void> {
    return httpRequest<void>(`/courses/${courseId}/learning/materials/${materialId}`, {
      method: "DELETE",
    });
  },

  toggleMaterialPublish(
    courseId: string,
    materialId: string,
    isPublished: boolean
  ): Promise<LearningMaterial> {
    return httpRequest<LearningMaterial>(
      `/courses/${courseId}/learning/materials/${materialId}/publish`,
      {
        method: "PATCH",
        body: { is_published: isPublished },
      }
    );
  },

  uploadMaterialFile(
    courseId: string,
    moduleId: string,
    file: File
  ): Promise<MaterialUploadResult> {
    const formData = new FormData();
    formData.append("file", file);
    return httpRequest<MaterialUploadResult>(
      `/courses/${courseId}/learning/modules/${moduleId}/materials/upload`,
      {
        method: "POST",
        formData,
      }
    );
  },

  downloadMaterialFile(courseId: string, materialId: string, filename: string): Promise<void> {
    return httpDownloadBlob(
      `/courses/${courseId}/learning/materials/${materialId}/download`,
      filename
    );
  },

  fetchMaterialPreviewBlob(
    courseId: string,
    materialId: string
  ): Promise<{ blob: Blob; contentType: string }> {
    return httpFetchBlob(`/courses/${courseId}/learning/materials/${materialId}/preview`);
  },

  completeMaterial(courseId: string, materialId: string): Promise<{ status: string; material_id: string }> {
    return httpRequest<{ status: string; material_id: string }>(
      `/courses/${courseId}/learning/materials/${materialId}/complete`,
      { method: "POST" }
    );
  },
};
