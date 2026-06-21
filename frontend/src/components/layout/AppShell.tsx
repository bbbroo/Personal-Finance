import { Menu } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { navItems, type PageId } from "./nav";

export function AppShell({
  active,
  onNavigate,
  children
}: {
  active: PageId;
  onNavigate: (page: PageId) => void;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);

  useEffect(() => setOpen(false), [active]);

  return (
    <div className="min-h-screen bg-background">
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 w-72 border-r bg-card transition-transform lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-16 items-center border-b px-5">
          <div>
            <div className="text-base font-semibold">Local Finance</div>
            <div className="text-xs text-muted-foreground">Private Windows ledger</div>
          </div>
        </div>
        <nav className="h-[calc(100vh-4rem)] overflow-y-auto p-3">
          {navItems.map((item) => {
            const Icon = item.icon;
            const selected = active === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={cn(
                  "focus-ring mb-1 flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm",
                  selected ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <Icon className="h-4 w-4" aria-hidden />
                {item.label}
              </button>
            );
          })}
        </nav>
      </aside>
      {open ? <button className="fixed inset-0 z-30 bg-black/20 lg:hidden" onClick={() => setOpen(false)} /> : null}
      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b bg-background/95 px-4 backdrop-blur lg:px-8">
          <Button variant="outline" size="icon" className="lg:hidden" onClick={() => setOpen(true)} aria-label="Open navigation">
            <Menu className="h-4 w-4" />
          </Button>
          <div>
            <div className="text-sm font-semibold">{navItems.find((item) => item.id === active)?.label}</div>
            <div className="text-xs text-muted-foreground">Local data only. No cloud backend.</div>
          </div>
          <div className="hidden rounded-sm border bg-muted px-2 py-1 text-xs text-muted-foreground sm:block">
            USD cents + Decimal-safe quantities
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl px-4 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
