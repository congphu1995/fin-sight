"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, FileText, MessageSquare, CalendarClock } from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarFooter,
} from "@/components/ui/sidebar";
import { ThemeToggle } from "./theme-toggle";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/analyses", label: "Analyses", icon: CalendarClock },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <Sidebar>
      <SidebarHeader>
        <div className="px-2 py-1.5">
          <div className="text-base font-semibold tracking-tight">Fin Sight</div>
          <div className="text-xs text-muted-foreground">Research workbench</div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigate</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV.map(({ href, label, icon: Icon }) => {
                const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
                return (
                  <SidebarMenuItem key={href}>
                    <SidebarMenuButton render={<Link href={href} />} isActive={active}>
                      <Icon className="h-4 w-4" />
                      <span>{label}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <div className="flex items-center justify-between px-2 py-1">
          <span className="text-xs text-muted-foreground">Theme</span>
          <ThemeToggle />
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
