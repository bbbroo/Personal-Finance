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
        accessorKey: "amount_cents",
        header: "Amount",
        cell: ({ row }) => (
          <span className={row.original.amount_cents < 0 ? "text-danger" : "text-emerald-700"}>
            {formatCents(row.original.amount_cents)}
          </span>
        )
      },
      { accessorKey: "transaction_type", header: "Type" },
      {
        accessorKey: "transfer_status",
        header: "Transfer",
        cell: ({ row }) => <Badge tone={row.original.transfer_status === "confirmed_transfer" ? "success" : "neutral"}>{row.original.transfer_status}</Badge>
      },
      {
        accessorKey: "duplicate_status",
        header: "Duplicate",
        cell: ({ row }) => <Badge tone={row.original.duplicate_status === "unique" ? "success" : "warning"}>{row.original.duplicate_status}</Badge>
      }
    ],
    []
  );
  const table = useReactTable({ data, columns, getCoreRowModel: getCoreRowModel() });

  return (
    <div className="overflow-hidden rounded-lg border bg-card">
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
