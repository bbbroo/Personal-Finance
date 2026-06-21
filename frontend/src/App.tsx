import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { navItems, type PageId } from "@/components/layout/nav";
import { Accounts } from "@/pages/Accounts";
import { Allocation } from "@/pages/Allocation";
import { AuditLog } from "@/pages/AuditLog";
import { Backups } from "@/pages/Backups";
import { Budgets } from "@/pages/Budgets";
import { Dashboard } from "@/pages/Dashboard";
import { DataQuality } from "@/pages/DataQuality";
import { Goals } from "@/pages/Goals";
import { Holdings } from "@/pages/Holdings";
import { ImportCenter } from "@/pages/ImportCenter";
import { Liabilities } from "@/pages/Liabilities";
import { MonthlyReview } from "@/pages/MonthlyReview";
import { NetWorth } from "@/pages/NetWorth";
import { Reconciliation } from "@/pages/Reconciliation";
import { RecurringCalendar } from "@/pages/RecurringCalendar";
import { Settings } from "@/pages/Settings";
import { Status } from "@/pages/Status";
import { Transactions } from "@/pages/Transactions";

const pages: Record<PageId, React.ComponentType> = {
  dashboard: Dashboard,
  accounts: Accounts,
  transactions: Transactions,
  holdings: Holdings,
  "net-worth": NetWorth,
  allocation: Allocation,
  budgets: Budgets,
  recurring: RecurringCalendar,
  goals: Goals,
  liabilities: Liabilities,
  import: ImportCenter,
  reconciliation: Reconciliation,
  quality: DataQuality,
  "monthly-review": MonthlyReview,
  audit: AuditLog,
  settings: Settings,
  backups: Backups,
  status: Status
};

function currentPage(): PageId {
  const hash = window.location.hash.replace("#", "");
  return navItems.some((item) => item.id === hash) ? (hash as PageId) : "dashboard";
}

export function App() {
  const queryClient = useMemo(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 20_000,
            retry: 1
          }
        }
      }),
    []
  );
  const [page, setPage] = useState<PageId>(currentPage);

  useEffect(() => {
    const onHashChange = () => setPage(currentPage());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const Page = pages[page];
  return (
    <QueryClientProvider client={queryClient}>
      <AppShell
        active={page}
        onNavigate={(next) => {
          window.location.hash = next;
          setPage(next);
        }}
      >
        <Page />
      </AppShell>
    </QueryClientProvider>
  );
}
