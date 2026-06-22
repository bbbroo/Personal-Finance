import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef
} from "@tanstack/react-table";
import { useMemo } from "react";

import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatCents } from "@/lib/utils";
import type { Transaction } from "@/types";

function statusTone(status: string) {
  if (["reviewed", "unique", "confirmed_transfer", "income", "expense"].includes(status)) return "success";
  if (["confirmed_duplicate", "error"].includes(status)) return "danger";
  if (["needs_review", "possible_duplicate", "suggested_transfer"].includes(status)) return "warning";
  return "neutral";
}

export function TransactionTable({ data }: { data: Transaction[] }) {
  const columns = useMemo<ColumnDef<Transaction>[]>(
    () => [
      { accessorKey: "transaction_date", header: "Date" },
      {
        accessorKey: "merchant_name",
        header: "Merchant",
        cell: ({ row }) => row.original.merchant_name ?? row.original.original_description
      },
      {
        accessorKey: "category_name",
        header: "Category",
        cell: ({ row }) => <span className="text-sm text-muted-foreground">{String(row.original.category_name ?? row.original.category_id ?? "Uncategorized")}</span>
      },
      {
        accessorKey: "amount_cents",
        header: "Amount",
        cell: ({ row }) => (
          <span className={row.original.amount_cents < 0 ? "text-danger" : "text-emerald-700"}>
            {formatCents(row.original.amount_cents)}
          </span>
        )
      },
      { accessorKey: "transaction_type", header: "Type", cell: ({ row }) => <Badge tone={statusTone(row.original.transaction_type)}>{row.original.transaction_type}</Badge> },
      {
        accessorKey: "review_status",
        header: "Review",
        cell: ({ row }) => <Badge tone={statusTone(row.original.review_status)}>{row.original.review_status}</Badge>
      },
      {
        accessorKey: "transfer_status",
        header: "Transfer",
        cell: ({ row }) => <Badge tone={statusTone(row.original.transfer_status)}>{row.original.transfer_status}</Badge>
      },
      {
        accessorKey: "duplicate_status",
        header: "Duplicate",
        cell: ({ row }) => <Badge tone={statusTone(row.original.duplicate_status)}>{row.original.duplicate_status}</Badge>
      }
    ],
    []
  );
  const table = useReactTable({ data, columns, getCoreRowModel: getCoreRowModel() });

  return (
    <div className="overflow-auto rounded-lg border bg-card">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id}>{flexRender(header.column.columnDef.header, header.getContext())}</TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.map((row) => (
            <TableRow key={row.id}>
              {row.getVisibleCells().map((cell) => (
                <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
