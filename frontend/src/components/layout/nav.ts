import {
  Activity,
  Archive,
  Banknote,
  BarChart3,
  CalendarDays,
  ClipboardCheck,
  Coins,
  FileClock,
  Flag,
  Gauge,
  Landmark,
  LineChart,
  PieChart,
  ReceiptText,
  Settings,
  ShieldAlert,
  Upload,
  WalletCards
} from "lucide-react";

export const navItems = [
  { id: "dashboard", label: "Dashboard", icon: Gauge },
  { id: "accounts", label: "Accounts", icon: Landmark },
  { id: "transactions", label: "Transactions", icon: ReceiptText },
  { id: "holdings", label: "Holdings", icon: Coins },
  { id: "net-worth", label: "Net Worth", icon: LineChart },
  { id: "allocation", label: "Allocation", icon: PieChart },
  { id: "budgets", label: "Budget", icon: WalletCards },
  { id: "recurring", label: "Recurring", icon: CalendarDays },
  { id: "goals", label: "Goals", icon: Flag },
  { id: "liabilities", label: "Liabilities", icon: Banknote },
  { id: "import", label: "Import Center", icon: Upload },
  { id: "reconciliation", label: "Reconciliation", icon: ClipboardCheck },
  { id: "quality", label: "Data Quality", icon: ShieldAlert },
  { id: "monthly-review", label: "Monthly Review", icon: BarChart3 },
  { id: "audit", label: "Audit Log", icon: FileClock },
  { id: "settings", label: "Settings", icon: Settings },
  { id: "backups", label: "Backups", icon: Archive },
  { id: "status", label: "Local Status", icon: Activity }
] as const;

export type PageId = (typeof navItems)[number]["id"];
