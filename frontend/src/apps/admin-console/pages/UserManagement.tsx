/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Lock,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  Unlock,
  UserPlus,
  Users,
} from "lucide-react";
import { Badge } from "../../../components/ui/Badge";
import { SystemAuthService } from "../../../services/systemAuthService";
import { PaginatedUsersResponse, User, UserSession } from "../../../types/system";
import { CreateUserModal } from "../components/CreateUserModal";
import { RevokeSessionModal } from "../components/RevokeSessionModal";

export const UserManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"users" | "sessions">("users");

  // Users State
  const [usersData, setUsersData] = useState<PaginatedUsersResponse>({
    items: [],
    total: 0,
    page: 1,
    page_size: 20,
    total_pages: 1,
  });
  const [searchQuery, setSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoadingUsers, setIsLoadingUsers] = useState(false);

  // Sessions State
  const [sessions, setSessions] = useState<UserSession[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [selectedSessionForRevoke, setSelectedSessionForRevoke] = useState<UserSession | null>(null);

  // Modals & Feedback
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [notification, setNotification] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  const showNotification = (type: "success" | "error", message: string) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 5000);
  };

  const loadUsers = useCallback(async () => {
    setIsLoadingUsers(true);
    try {
      const data = await SystemAuthService.listUsers({
        query: searchQuery || undefined,
        role: roleFilter || undefined,
        isActive: statusFilter === "" ? undefined : statusFilter === "true",
        page: currentPage,
        pageSize: 20,
      });
      setUsersData(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        showNotification("error", err.message);
      }
    } finally {
      setIsLoadingUsers(false);
    }
  }, [searchQuery, roleFilter, statusFilter, currentPage]);

  const loadSessions = useCallback(async () => {
    setIsLoadingSessions(true);
    try {
      const data = await SystemAuthService.listActiveSessions();
      setSessions(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        showNotification("error", err.message);
      }
    } finally {
      setIsLoadingSessions(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === "users") {
      loadUsers();
    } else {
      loadSessions();
    }
  }, [activeTab, loadUsers, loadSessions]);

  const handleToggleUserStatus = async (user: User) => {
    const action = user.is_active ? "deactivate" : "activate";
    const confirmMessage = user.is_active
      ? `Are you sure you want to deactivate account '${user.full_name}'?`
      : `Activate account '${user.full_name}'?`;

    if (!window.confirm(confirmMessage)) return;

    try {
      await SystemAuthService.updateUserStatus(user.id, {
        is_active: !user.is_active,
        reason: `Administrator status toggle to ${action}`,
      });
      showNotification("success", `User ${user.user_code} has been successfully ${action}d.`);
      loadUsers();
    } catch (err: unknown) {
      if (err instanceof Error) {
        showNotification("error", err.message);
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-blue-600" />
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Identity & Session Admin
            </h1>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Platform-level identity provisioning, role governance, and real-time session revocation (Use Case T1-A-M0-01).
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => (activeTab === "users" ? loadUsers() : loadSessions())}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-pill shadow-sm transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${isLoadingUsers || isLoadingSessions ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            type="button"
            onClick={() => setIsCreateModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-pill shadow-brand transition-all"
          >
            <UserPlus className="w-4 h-4" />
            Create Identity
          </button>
        </div>
      </div>

      {/* Alert / Notification Banner */}
      {notification && (
        <div
          className={`flex items-center gap-3 p-4 rounded-xl border text-sm transition-all ${
            notification.type === "success"
              ? "bg-emerald-50 border-emerald-200 text-emerald-800"
              : "bg-rose-50 border-rose-200 text-rose-800"
          }`}
        >
          {notification.type === "success" ? (
            <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-600" />
          ) : (
            <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-600" />
          )}
          <span className="font-medium">{notification.message}</span>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200">
        <button
          type="button"
          onClick={() => setActiveTab("users")}
          className={`inline-flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "users"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300"
          }`}
        >
          <Users className="w-4 h-4" />
          User Accounts & RBAC
          <span className="ml-1.5 px-2 py-0.5 text-xs bg-slate-100 rounded-full font-semibold">
            {usersData.total}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("sessions")}
          className={`inline-flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "sessions"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300"
          }`}
        >
          <ShieldAlert className="w-4 h-4" />
          Active Sessions & Threat Monitor
          <span className="ml-1.5 px-2 py-0.5 text-xs bg-slate-100 rounded-full font-semibold">
            {sessions.length}
          </span>
        </button>
      </div>

      {/* Tab 1: Users Table */}
      {activeTab === "users" && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-card overflow-hidden">
          {/* Filters Bar */}
          <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex flex-col md:flex-row items-center justify-between gap-3">
            <div className="relative w-full md:w-80">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
                placeholder="Tìm kiếm mã, tên, email..."
                className="w-full pl-10 pr-4 py-2 text-sm bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              />
            </div>

            <div className="flex items-center gap-3 w-full md:w-auto">
              <select
                value={roleFilter}
                onChange={(e) => {
                  setRoleFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="px-3 py-2 text-sm bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all text-slate-700"
              >
                <option value="">Tất cả Vai trò</option>
                <option value="ADMIN">Chỉ Quản trị viên</option>
                <option value="USER">Chỉ Người dùng</option>
              </select>

              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="px-3 py-2 text-sm bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all text-slate-700"
              >
                <option value="">Tất cả Trạng thái</option>
                <option value="true">Chỉ Hoạt động</option>
                <option value="false">Locked Only</option>
              </select>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600 text-xs uppercase tracking-wider font-semibold border-b border-slate-100">
                <tr>
                  <th className="px-6 py-3.5">Thông tin Người dùng</th>
                  <th className="px-6 py-3.5">System Role</th>
                  <th className="px-6 py-3.5">Trạng thái</th>
                  <th className="px-6 py-3.5">Created At</th>
                  <th className="px-6 py-3.5 text-right">Hành động</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {isLoadingUsers ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-12 text-center text-slate-400">
                      Loading user records...
                    </td>
                  </tr>
                ) : usersData.items.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-12 text-center text-slate-400">
                      No user accounts found matching current criteria.
                    </td>
                  </tr>
                ) : (
                  usersData.items.map((user) => (
                    <tr key={user.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex flex-col">
                          <span className="font-semibold text-slate-900">{user.full_name}</span>
                          <span className="text-xs text-slate-500">{user.email}</span>
                          <span className="font-mono text-xs text-slate-400 mt-0.5">{user.user_code}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <Badge variant={user.system_role === "ADMIN" ? "primary" : "neutral"}>
                          {user.system_role}
                        </Badge>
                      </td>
                      <td className="px-6 py-4">
                        <Badge variant={user.is_active ? "success" : "danger"}>
                          {user.is_active ? "ACTIVE" : "LOCKED"}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 text-xs text-slate-500 font-mono">
                        {new Date(user.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          type="button"
                          onClick={() => handleToggleUserStatus(user)}
                          title={user.is_active ? "Lock user" : "Unlock user"}
                          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-pill text-xs font-medium border transition-colors ${
                            user.is_active
                              ? "text-rose-700 bg-rose-50 border-rose-200 hover:bg-rose-100"
                              : "text-emerald-700 bg-emerald-50 border-emerald-200 hover:bg-emerald-100"
                          }`}
                        >
                          {user.is_active ? (
                            <>
                              <Lock className="w-3.5 h-3.5" />
                              Lock
                            </>
                          ) : (
                            <>
                              <Unlock className="w-3.5 h-3.5" />
                              Unlock
                            </>
                          )}
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          <div className="px-6 py-3.5 bg-slate-50 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
            <span>
              Showing {usersData.items.length} of {usersData.total} records (Page {usersData.page} of {usersData.total_pages})
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={currentPage <= 1 || isLoadingUsers}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg hover:bg-slate-100 disabled:opacity-40 transition-colors"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={currentPage >= usersData.total_pages || isLoadingUsers}
                onClick={() => setCurrentPage((p) => p + 1)}
                className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg hover:bg-slate-100 disabled:opacity-40 transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Sessions Table */}
      {activeTab === "sessions" && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-card overflow-hidden">
          <div className="p-4 border-b border-slate-100 bg-slate-50/50">
            <p className="text-xs text-slate-500">
              Live token sessions issued by Auth Engine. Forced revocation sends instant invalidation signal to Gateway edge proxies (Rule BR-SYS-02).
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600 text-xs uppercase tracking-wider font-semibold border-b border-slate-100">
                <tr>
                  <th className="px-6 py-3.5">Session / User</th>
                  <th className="px-6 py-3.5">Client IP</th>
                  <th className="px-6 py-3.5">User Agent</th>
                  <th className="px-6 py-3.5">Issued At</th>
                  <th className="px-6 py-3.5">Trạng thái</th>
                  <th className="px-6 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {isLoadingSessions ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-slate-400">
                      Scanning active session table...
                    </td>
                  </tr>
                ) : sessions.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-slate-400">
                      No active sessions recorded or system operating in mock development mode.
                    </td>
                  </tr>
                ) : (
                  sessions.map((sess) => (
                    <tr key={sess.session_id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex flex-col">
                          <span className="font-semibold text-slate-900">{sess.full_name}</span>
                          <span className="text-xs text-slate-500">{sess.email}</span>
                          <span className="font-mono text-xs text-slate-400 mt-0.5">
                            {sess.session_id.slice(0, 16)}...
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 font-mono text-xs text-slate-700">
                        {sess.ip_address}
                      </td>
                      <td className="px-6 py-4 text-xs text-slate-500 max-w-xs truncate">
                        {sess.user_agent}
                      </td>
                      <td className="px-6 py-4 text-xs text-slate-500 font-mono">
                        {new Date(sess.issued_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4">
                        <Badge variant={sess.status === "ACTIVE" ? "success" : "danger"}>
                          {sess.status}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 text-right">
                        {sess.status === "ACTIVE" && (
                          <button
                            type="button"
                            onClick={() => setSelectedSessionForRevoke(sess)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-pill text-xs font-medium text-rose-700 bg-rose-50 border border-rose-200 hover:bg-rose-100 transition-colors"
                          >
                            <ShieldAlert className="w-3.5 h-3.5" />
                            Revoke
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modals */}
      <CreateUserModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={() => {
          showNotification("success", "New user identity created successfully.");
          loadUsers();
        }}
      />

      <RevokeSessionModal
        session={selectedSessionForRevoke}
        isOpen={Boolean(selectedSessionForRevoke)}
        onClose={() => setSelectedSessionForRevoke(null)}
        onSuccess={() => {
          showNotification("success", "Session revoked successfully and blacklisted.");
          loadSessions();
        }}
      />
    </div>
  );
};
