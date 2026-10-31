import { Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import ReportPage from "@/pages/ReportPage";
import WarehouseSettingPage from "@/pages/WarehouseSettingPage";
import MainLayout from "@/components/layout/MainLayout";
import { PublicRoute } from "../components/auth/PublicRoute";
import { ProtectedRoute } from "../components/auth/ProtectedRoute";
import ItemPage from "@/pages/ItemPage";
import UserSettingPage from "@/pages/UserSettingPage";
import ItemDetailPage from "@/pages/ItemDetailPage";
import NotificationPage from "@/pages/NotificationPage";
import { RoleHomeRedirect } from "@/components/auth/RoleHomeRedirect";
import ProductionRoutePage from "@/pages/production/ProductionRoutePage";
import StationSettingPage from "@/pages/production/StationSettingPage";

// PDA 4.2" Caller Pages (Dedicated per Area)
import RawMaterialPdaPage from "@/pages/pda/RawMaterialPdaPage";
import CncPdaPage from "@/pages/pda/CncPdaPage";
import WashingPdaPage from "@/pages/pda/WashingPdaPage";

export default function AppRoutes() {
  return (
    <Routes>
      {/* ── PDA 4.2" Dedicated Routes (Full screen standalone, strictly isolated per area) ── */}
      <Route
        path="/pda/raw-material"
        element={
          <ProtectedRoute>
            <RawMaterialPdaPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/pda/cnc"
        element={
          <ProtectedRoute>
            <CncPdaPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/pda/washing"
        element={
          <ProtectedRoute>
            <WashingPdaPage />
          </ProtectedRoute>
        }
      />

      {/* Redirect /pda và /caller trực tiếp theo quyền của tài khoản */}
      <Route
        path="/pda"
        element={
          <ProtectedRoute>
            <RoleHomeRedirect />
          </ProtectedRoute>
        }
      />
      <Route path="/caller" element={<Navigate to="/pda" replace />} />
      <Route path="/caller/*" element={<Navigate to="/pda" replace />} />

      <Route
        path="/login"
        element={
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        }
      />

      {/* ── Main app with sidebar (Desktop Admin PC) ── */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<RoleHomeRedirect />} />
        <Route path="overview" element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="items" element={<ItemPage />} />
        <Route path="items/:id" element={<ItemDetailPage />} />
        <Route path="production/routes" element={<ProductionRoutePage />} />
        <Route path="routes" element={<Navigate to="/production/routes" replace />} />
        <Route path="production/stations" element={<StationSettingPage />} />
        <Route path="machines" element={<Navigate to="/production/stations" replace />} />
        <Route path="zones" element={<Navigate to="/production/stations" replace />} />
        <Route path="report" element={<ReportPage />} />
        <Route path="notification" element={<NotificationPage />} />
        <Route path="setting" element={<Navigate to="/setting/users" replace />} />
        <Route path="setting/users" element={<UserSettingPage />} />
        <Route path="setting/warehouse" element={<WarehouseSettingPage />} />
        <Route path="setting/zones" element={<Navigate to="/production/stations" replace />} />
      </Route>
    </Routes>
  );
}
