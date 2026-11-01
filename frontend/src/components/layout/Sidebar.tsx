import { useEffect, useState } from "react";
import { matchPath, Navigate, NavLink, useLocation } from "react-router-dom";
import { useLogout } from "@/hooks/useAuth";
import { useAuthStore } from "@/store/useAuthStore";
import { useAppStore } from "@/store/useAppStore";
import {
  LogoutOutlined,
  ShopOutlined,
  AppstoreOutlined,
  BoxPlotOutlined,
  BellOutlined,
  SettingOutlined,
  ClusterOutlined,
  RightOutlined,
  UserOutlined,
  HomeOutlined,
  BranchesOutlined,
} from "@ant-design/icons";

interface SidebarLinkProps {
  to: string;
  icon: React.ReactNode;
  label: string;
  collapsed: boolean;
}

interface SubLinkProps {
  to: string;
  icon: React.ReactNode;
  label: string;
  collapsed: boolean;
}

interface SidebarGroupItem {
  to: string;
  icon: React.ReactNode;
  label: string;
}

interface SidebarGroupProps {
  label: string;
  icon: React.ReactNode;
  items: SidebarGroupItem[];
  defaultOpen?: boolean;
  collapsed: boolean;
}

function isGroupActive(items: SidebarGroupItem[], pathname: string) {
  return items.some((item) =>
    matchPath({ path: item.to, end: true }, pathname),
  );
}

function SidebarLink({ to, icon, label, collapsed }: SidebarLinkProps) {
  return (
    <NavLink
      to={to}
      className="group block"
      title={collapsed ? label : undefined}
    >
      {({ isActive }) => (
        <div
          className={`flex items-center rounded-xl transition-all duration-300 py-2 ${collapsed ? "justify-center px-1.5 gap-0" : "px-3 gap-3"} ${
            isActive
              ? "text-stripe-primary-soft font-semibold bg-slate-800/40"
              : "text-slate-400 hover:text-white hover:bg-slate-800/20"
          }`}
        >
          <div
            className={`w-9 h-9 flex items-center justify-center rounded-lg transition-all shrink-0 ${
              isActive
                ? "bg-brand-primary text-white shadow-lg shadow-brand-primary/20"
                : "bg-slate-800 text-slate-400 group-hover:bg-slate-700 group-hover:text-white"
            }`}
          >
            {icon}
          </div>
          <span
            className={`text-sm tracking-wide transition-all duration-300 overflow-hidden whitespace-nowrap ${collapsed ? "opacity-0 max-w-0" : "opacity-100 max-w-[150px]"}`}
          >
            {label}
          </span>
        </div>
      )}
    </NavLink>
  );
}

function SubLink({ to, icon, label, collapsed }: SubLinkProps) {
  return (
    <NavLink
      to={to}
      className="group block"
      title={collapsed ? label : undefined}
    >
      {({ isActive }) => (
        <div
          className={`flex items-center rounded-lg transition-all duration-300 py-1.5 ${collapsed ? "justify-center px-1.5 gap-0" : "px-3 gap-3"} ${
            isActive
              ? "text-stripe-primary-soft font-semibold bg-slate-800/30"
              : "text-slate-400 hover:text-white hover:bg-slate-800/10"
          }`}
        >
          <div
            className={`w-7 h-7 flex items-center justify-center rounded-md transition-all shrink-0 ${
              isActive
                ? "text-stripe-primary-soft"
                : "text-slate-500 group-hover:text-slate-300"
            }`}
          >
            {icon}
          </div>
          <span
            className={`text-xs tracking-wide transition-all duration-300 overflow-hidden whitespace-nowrap ${collapsed ? "opacity-0 max-w-0" : "opacity-100 max-w-[120px]"}`}
          >
            {label}
          </span>
        </div>
      )}
    </NavLink>
  );
}

function SidebarGroup({
  label,
  icon,
  items,
  defaultOpen = true,
  collapsed,
}: SidebarGroupProps) {
  const { pathname } = useLocation();
  const [open, setOpen] = useState(defaultOpen);
  const isActive = isGroupActive(items, pathname);

  useEffect(() => {
    if (isActive) {
      setOpen(true);
    }
  }, [isActive]);

  return (
    <div className="flex flex-col">
      <button
        type="button"
        title={collapsed ? label : undefined}
        onClick={() => setOpen(!open)}
        className={`group flex w-full items-center rounded-xl cursor-pointer transition-all duration-300 ${collapsed ? "justify-center px-1.5 gap-0" : "justify-between px-3 gap-3"} ${
          isActive
            ? "text-stripe-primary-soft font-semibold bg-slate-800/40"
            : "text-slate-400 hover:text-white hover:bg-slate-800/20"
        }`}
      >
        <div
          className={`flex items-center transition-all duration-300 ${collapsed ? "gap-0" : "gap-3"}`}
        >
          <div
            className={`w-9 h-9 flex items-center justify-center rounded-lg transition-all shrink-0 ${
              isActive
                ? "bg-brand-primary text-white shadow-lg shadow-brand-primary/20"
                : "bg-slate-800 text-slate-400 group-hover:bg-slate-700 group-hover:text-white"
            }`}
          >
            {icon}
          </div>
          <span
            className={`text-sm tracking-wide transition-all duration-300 overflow-hidden whitespace-nowrap ${collapsed ? "opacity-0 max-w-0" : "opacity-100 max-w-[150px]"}`}
          >
            {label}
          </span>
        </div>
        <div
          className={`transition-all duration-300 overflow-hidden ${collapsed ? "opacity-0 max-w-0" : "opacity-100 max-w-[20px] mr-1"}`}
        >
          <RightOutlined
            className={`inline-block text-xs text-slate-500 transition-transform duration-200 ${open ? "rotate-90" : "rotate-0"}`}
          />
        </div>
      </button>

      {open && (
        <div
          className={`flex flex-col gap-1 mt-1 transition-all duration-300 ${collapsed ? "w-full items-center gap-0.5" : "pl-4 ml-7 border-l border-slate-800"}`}
        >
          {items.map((item) => (
            <SubLink key={item.to} {...item} collapsed={collapsed} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function Sidebar() {
  const { user, isAuthenticated } = useAuthStore();
  const username = user?.username;
  const role = user?.roles?.[0]?.name;
  const selectedWarehouseId = useAppStore((state) => state.selectedWarehouseId);
  const warehouseId = selectedWarehouseId || 0;
  const logout = useLogout();
  const [collapsed, setCollapsed] = useState(false);
  const isAdmin = !!user?.access?.is_admin;

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const handleSidebarClick = (e: React.MouseEvent<HTMLElement>) => {
    const target = e.target as HTMLElement;
    if (target.closest("a, button, [data-no-collapse]")) {
      return;
    }
    setCollapsed((prev) => !prev);
  };

  return (
    <aside
      data-warehouse-id={warehouseId}
      className={`relative h-screen bg-slate-900 text-white flex flex-col border-r border-slate-800 transition-all duration-300 cursor-pointer ${collapsed ? "w-[72px]" : "w-64"}`}
      onClick={handleSidebarClick}
    >
      <div
        className={`flex h-16 shrink-0 items-center border-b border-slate-800 font-bold transition-all duration-300 ${collapsed ? "justify-center px-2" : "px-6"}`}
      >
        <div
          className="flex items-center gap-2 select-none"
          data-no-collapse
        >
          <span
            className="text-brand-primary font-black text-xl tracking-wider transition-all duration-300 overflow-hidden whitespace-nowrap"
          >
            {collapsed ? "K" : "KUKA"}
          </span>
          {!collapsed && (
            <span className="text-[11px] font-bold text-slate-400 bg-slate-800/80 px-1.5 py-0.5 rounded tracking-wider border border-slate-700/60">
              WMS
            </span>
          )}
        </div>
      </div>

      <nav className="flex flex-col gap-1 flex-1 overflow-y-auto mt-6 px-3 overflow-x-hidden">
        <SidebarGroup
          label="Sản xuất & Điều phối"
          icon={<ShopOutlined className="text-lg" />}
          items={[
            {
              to: "/dashboard",
              icon: <AppstoreOutlined />,
              label: "Tổng quan xưởng",
            },
            { to: "/items", icon: <BoxPlotOutlined />, label: "Model Sản phẩm" },
            {
              to: "/production/routes",
              icon: <BranchesOutlined />,
              label: "Quy trình Route",
            },
            { to: "/production/stations", icon: <ClusterOutlined />, label: "Cấu hình Trạm" },
          ]}
          collapsed={collapsed}
        />
        <SidebarLink
          to="/notification"
          icon={<BellOutlined className="text-lg" />}
          label="Thông báo"
          collapsed={collapsed}
        />
        <SidebarGroup
          label="Cài đặt hệ thống"
          icon={<SettingOutlined className="text-lg" />}
          items={[
            {
              to: "/setting/users",
              icon: <UserOutlined />,
              label: "Tài khoản & Trạm",
            },
            { to: "/setting/warehouse", icon: <HomeOutlined />, label: "Phân xưởng" },
          ]}
          collapsed={collapsed}
        />
      </nav>

      <div
        className={`border-t border-slate-800 bg-slate-950/20 p-4 flex transition-all duration-300 ${collapsed ? "flex-col gap-3 items-center justify-center" : "items-center justify-between"}`}
      >
        <div
          className={`flex items-center transition-all duration-300 ${collapsed ? "justify-center gap-0" : "gap-3"}`}
        >
          <button
            type="button"
            data-no-collapse
            className="w-9 h-9 rounded-full bg-slate-800 flex items-center justify-center text-slate-200 font-bold border border-slate-700 text-sm uppercase shrink-0"
          >
            {username ? username[0] : "U"}
          </button>
          <div
            className={`transition-all duration-300 overflow-hidden whitespace-nowrap ${collapsed ? "opacity-0 max-w-0" : "opacity-100 max-w-[120px]"}`}
          >
            <div className="text-sm font-medium text-slate-300 tracking-wide">
              {username || "User"}
            </div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">
              {role || (isAdmin ? "Admin" : "Operator")}
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={logout}
          className="text-slate-400 hover:text-red-400 p-1.5 rounded-lg hover:bg-slate-800 transition-colors cursor-pointer flex items-center justify-center shrink-0"
          title="Đăng xuất"
        >
          <LogoutOutlined className="text-base" />
        </button>
      </div>

      <div
        className={`border-t border-slate-800/80 bg-slate-950/40 transition-all duration-300 text-center select-none ${collapsed ? "py-2 px-1 text-[9px]" : "py-2.5 px-3 text-[11px]"}`}
      >
        <a
          href="http://thadorobot.com"
          target="_blank"
          rel="noreferrer"
          data-no-collapse
          className="text-slate-500 hover:text-brand-primary transition-colors block overflow-hidden text-ellipsis whitespace-nowrap"
          title="Thado Robot Solution"
        >
          {collapsed ? "© TR" : "© 2026 THADOROBOT"}
        </a>
      </div>
    </aside>
  );
}
