/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { App } from "./App";
import { MainApp } from "./apps/main-app/MainApp";

export const RootRouter: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/admin/*" element={<App />} />
        <Route path="/*" element={<MainApp />} />
      </Routes>
    </BrowserRouter>
  );
};
