import { Outlet } from "react-router-dom";
import { AppNav } from "@/components/layout/AppNav";

export function AppShell() {
  return (
    <div className="flex min-h-dvh flex-1 flex-col bg-paper">
      <AppNav />
      <div className="flex flex-1 flex-col">
        <Outlet />
      </div>
    </div>
  );
}
