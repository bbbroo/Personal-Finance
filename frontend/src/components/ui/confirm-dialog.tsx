import { useState } from "react";

import { Button } from "@/components/ui/button";

type ConfirmDialogState = {
  title: string;
  description: string;
  confirmLabel?: string;
  variant?: "default" | "danger";
  onConfirm: () => void;
};

export function useConfirmDialog() {
  const [state, setState] = useState<ConfirmDialogState | null>(null);

  const confirm = (nextState: ConfirmDialogState) => setState(nextState);
  const close = () => setState(null);

  const dialog = state ? (
    <div role="dialog" aria-modal="true" aria-labelledby="confirm-dialog-title" className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-lg border bg-card p-5 shadow-lg">
        <div id="confirm-dialog-title" className="text-lg font-semibold">{state.title}</div>
        <p className="mt-2 text-sm text-muted-foreground">{state.description}</p>
        <div className="mt-5 flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={close}>Cancel</Button>
          <Button
            type="button"
            variant={state.variant === "danger" ? "danger" : "default"}
            onClick={() => {
              const action = state.onConfirm;
              close();
              action();
            }}
          >
            {state.confirmLabel ?? "Confirm"}
          </Button>
        </div>
      </div>
    </div>
  ) : null;

  return { confirm, dialog };
}
