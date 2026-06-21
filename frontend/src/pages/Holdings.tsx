import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { LoadingBlock } from "@/components/ui/loading";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatCents } from "@/lib/utils";
import type { Account, ApiRecord } from "@/types";
import { PageHeader } from "./PageHeader";

export function Holdings() {
  const client = useQueryClient();
  const [holding, setHolding] = useState({
    account_id: "",
    instrument_id: "",
    snapshot_date: new Date().toISOString().slice(0, 10),
    quantity_decimal: "",
    price_decimal: "",
    cost_basis_cents: "",
    cost_basis_quality: "user_entered",
    replace_existing: false
  });
  const [instrumentForm, setInstrumentForm] = useState({ symbol: "", name: "", instrument_type: "etf", default_asset_class: "us_stock" });
  const [price, setPrice] = useState({ instrument_id: "", price_date: new Date().toISOString().slice(0, 10), price_decimal: "", provider_symbol: "", confidence: "medium" });

  const holdings = useQuery({ queryKey: ["holdings"], queryFn: () => api.get<ApiRecord[]>("/holdings") });
  const accounts = useQuery({ queryKey: ["accounts"], queryFn: () => api.get<Account[]>("/accounts") });
  const instruments = useQuery({ queryKey: ["instruments"], queryFn: () => api.get<ApiRecord[]>("/instruments") });
  const prices = useQuery({ queryKey: ["prices"], queryFn: () => api.get<ApiRecord[]>("/prices") });
  const invalidate = () => {
    client.invalidateQueries({ queryKey: ["holdings"] });
    client.invalidateQueries({ queryKey: ["instruments"] });
    client.invalidateQueries({ queryKey: ["prices"] });
    client.invalidateQueries({ queryKey: ["dashboard"] });
    client.invalidateQueries({ queryKey: ["issues"] });
  };
  const createInstrument = useMutation({
    mutationFn: () => api.post<ApiRecord>("/instruments", instrumentForm),
    onSuccess: invalidate
  });
  const createHolding = useMutation({
    mutationFn: () =>
      api.post<ApiRecord>("/holdings/manual-snapshot", {
        ...holding,
        cost_basis_cents: holding.cost_basis_cents ? Math.round(Number(holding.cost_basis_cents) * 100) : null,
        price_decimal: holding.price_decimal || null
      }),
    onSuccess: invalidate
  });
  const createPrice = useMutation({
    mutationFn: () => api.post<ApiRecord>("/prices/manual", { ...price, provider: "manual", status: "manual_override", market_session: "manual" }),
    onSuccess: invalidate
  });
  const refreshPrices = useMutation({ mutationFn: () => api.post<ApiRecord>("/prices/refresh"), onSuccess: invalidate });

  if (holdings.isLoading) return <LoadingBlock label="Loading holdings" />;
  const rows = holdings.data ?? [];
  const accountOptions = accounts.data ?? [];
  const instrumentOptions = instruments.data ?? [];

  return (
    <>
      <PageHeader title="Holdings" detail="Cost basis, price freshness, and replacement behavior stay explicit. Same-day replacements require the checkbox." />
      <div className="mb-4 grid gap-4 xl:grid-cols-3">
        <Card>
          <CardHeader><CardTitle>Add Instrument</CardTitle></CardHeader>
          <CardContent className="grid gap-2">
            <Input placeholder="Symbol" value={instrumentForm.symbol} onChange={(event) => setInstrumentForm({ ...instrumentForm, symbol: event.target.value.toUpperCase() })} />
            <Input placeholder="Name" value={instrumentForm.name} onChange={(event) => setInstrumentForm({ ...instrumentForm, name: event.target.value })} />
            <Select value={instrumentForm.instrument_type} onChange={(event) => setInstrumentForm({ ...instrumentForm, instrument_type: event.target.value })}>
              <option value="etf">ETF</option>
              <option value="stock">Stock</option>
              <option value="crypto">Crypto</option>
              <option value="cash">Cash</option>
              <option value="other">Other</option>
            </Select>
            <Input placeholder="Asset class" value={instrumentForm.default_asset_class} onChange={(event) => setInstrumentForm({ ...instrumentForm, default_asset_class: event.target.value })} />
            <Button size="sm" onClick={() => createInstrument.mutate()} disabled={!instrumentForm.symbol || !instrumentForm.name}>Create Instrument</Button>
            {createInstrument.error ? <div className="text-sm text-danger">{createInstrument.error.message}</div> : null}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Add Holding Snapshot</CardTitle></CardHeader>
          <CardContent className="grid gap-2">
            <Select value={holding.account_id} onChange={(event) => setHolding({ ...holding, account_id: event.target.value })}>
              <option value="">Account</option>
              {accountOptions.map((account) => <option value={account.id} key={account.id}>{account.name}</option>)}
            </Select>
            <Select value={holding.instrument_id} onChange={(event) => setHolding({ ...holding, instrument_id: event.target.value })}>
              <option value="">Instrument</option>
              {instrumentOptions.map((instrument) => <option value={String(instrument.id)} key={String(instrument.id)}>{String(instrument.symbol)} - {String(instrument.name)}</option>)}
            </Select>
            <Input type="date" value={holding.snapshot_date} onChange={(event) => setHolding({ ...holding, snapshot_date: event.target.value })} />
            <Input placeholder="Quantity" value={holding.quantity_decimal} onChange={(event) => setHolding({ ...holding, quantity_decimal: event.target.value })} />
            <Input placeholder="Price" value={holding.price_decimal} onChange={(event) => setHolding({ ...holding, price_decimal: event.target.value })} />
            <Input placeholder="Cost basis dollars" value={holding.cost_basis_cents} onChange={(event) => setHolding({ ...holding, cost_basis_cents: event.target.value })} />
            <Select value={holding.cost_basis_quality} onChange={(event) => setHolding({ ...holding, cost_basis_quality: event.target.value })}>
              <option value="verified">Verified</option>
              <option value="user_entered">User entered</option>
              <option value="estimated">Estimated</option>
              <option value="incomplete">Incomplete</option>
              <option value="missing">Missing</option>
            </Select>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={holding.replace_existing} onChange={(event) => setHolding({ ...holding, replace_existing: event.target.checked })} />
              Replace same-date current snapshot
            </label>
            <Button size="sm" onClick={() => createHolding.mutate()} disabled={!holding.account_id || !holding.instrument_id || !holding.quantity_decimal}>Add Snapshot</Button>
            {createHolding.error ? <div className="text-sm text-danger">{createHolding.error.message}</div> : null}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Manual Price</CardTitle></CardHeader>
          <CardContent className="grid gap-2">
            <Select value={price.instrument_id} onChange={(event) => setPrice({ ...price, instrument_id: event.target.value })}>
              <option value="">Instrument</option>
              {instrumentOptions.map((instrument) => <option value={String(instrument.id)} key={String(instrument.id)}>{String(instrument.symbol)}</option>)}
            </Select>
            <Input type="date" value={price.price_date} onChange={(event) => setPrice({ ...price, price_date: event.target.value })} />
            <Input placeholder="Price" value={price.price_decimal} onChange={(event) => setPrice({ ...price, price_decimal: event.target.value })} />
            <Input placeholder="Provider symbol" value={price.provider_symbol} onChange={(event) => setPrice({ ...price, provider_symbol: event.target.value })} />
            <Select value={price.confidence} onChange={(event) => setPrice({ ...price, confidence: event.target.value })}>
              <option value="verified">Verified</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </Select>
            <div className="flex gap-2">
              <Button size="sm" onClick={() => createPrice.mutate()} disabled={!price.instrument_id || !price.price_decimal}>Save Price</Button>
              <Button size="sm" variant="outline" onClick={() => refreshPrices.mutate()}>Mark Stale</Button>
            </div>
            {refreshPrices.data?.warnings ? <div className="text-xs text-muted-foreground">{String(refreshPrices.data.warnings)}</div> : null}
            {createPrice.error ? <div className="text-sm text-danger">{createPrice.error.message}</div> : null}
          </CardContent>
        </Card>
      </div>
      {!rows.length ? <EmptyState title="No holdings" detail="Add manual holdings or import a brokerage holdings CSV." /> : (
        <div className="overflow-hidden rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Quantity</TableHead>
                <TableHead>Market value</TableHead>
                <TableHead>Cost basis</TableHead>
                <TableHead>Gain/Loss</TableHead>
                <TableHead>Basis quality</TableHead>
                <TableHead>Valuation</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={String(row.id)}>
                  <TableCell>{String(row.snapshot_date)}</TableCell>
                  <TableCell>{String(row.quantity_decimal)}</TableCell>
                  <TableCell>{formatCents(row.market_value_cents as number | null)}</TableCell>
                  <TableCell>{formatCents(row.cost_basis_cents as number | null)}</TableCell>
                  <TableCell>{formatCents(row.unrealized_gain_loss_cents as number | null)}</TableCell>
                  <TableCell><Badge tone={row.cost_basis_quality === "verified" || row.cost_basis_quality === "user_entered" ? "success" : "warning"}>{String(row.cost_basis_quality)}</Badge></TableCell>
                  <TableCell><Badge tone={row.valuation_quality === "current" ? "success" : "warning"}>{String(row.valuation_quality)}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      {prices.data?.some((row) => row.status === "stale" || row.status === "failed" || row.status === "missing") ? (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">One or more prices are stale or unavailable. Update manual prices before trusting allocation or net worth.</div>
      ) : null}
    </>
  );
}
