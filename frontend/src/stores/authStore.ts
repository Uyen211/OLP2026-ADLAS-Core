/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { registerAuthSessionBridge } from "../services/httpClient";
import type { MeResponse, TokenResponse } from "../types/auth";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  me: MeResponse | null;
  pendingMfaToken: string | null;
  setSession: (payload: TokenResponse) => void;
  setMe: (me: MeResponse) => void;
  setPendingMfaToken: (token: string | null) => void;
  clearSession: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      me: null,
      pendingMfaToken: null,
      setSession: (payload) =>
        set({
          accessToken: payload.access_token,
          refreshToken: payload.refresh_token,
          me: payload.user,
          pendingMfaToken: null,
        }),
      setMe: (me) => set({ me }),
      setPendingMfaToken: (token) => set({ pendingMfaToken: token }),
      clearSession: () =>
        set({
          accessToken: null,
          refreshToken: null,
          me: null,
          pendingMfaToken: null,
        }),
    }),
    {
      name: "adlas-auth-storage",
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        me: state.me,
      }),
    }
  )
);

registerAuthSessionBridge({
  getAccessToken: () => useAuthStore.getState().accessToken,
  getRefreshToken: () => useAuthStore.getState().refreshToken,
  onTokensRefreshed: (tokens) => useAuthStore.getState().setSession(tokens),
  onAuthFailure: () => useAuthStore.getState().clearSession(),
});
