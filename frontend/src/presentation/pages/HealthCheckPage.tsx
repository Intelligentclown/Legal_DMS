import { useEffect, useState } from "react";

import { useNotifications } from "@/app/providers/NotificationProvider";
import type { AppVersion, HealthStatus } from "@/domain/types/health";
import { httpClient, HttpError } from "@/infrastructure/api/httpClient";
import { ipcBridge, type ElectronAppInfo } from "@/infrastructure/ipc/ipcBridge";
import { LoadingSpinner } from "@/presentation/components/LoadingSpinner";
import { Button } from "@/presentation/components/ui/button";

interface HealthData {
  health: HealthStatus;
  version: AppVersion;
}

/**
 * Proves the full Stage 0 wiring end to end: frontend -> backend over HTTP,
 * and (when running inside Electron) renderer -> main process over IPC.
 */
export function HealthCheckPage() {
  const { notify } = useNotifications();
  const [data, setData] = useState<HealthData | null>(null);
  const [appInfo, setAppInfo] = useState<ElectronAppInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      httpClient.get<HealthStatus>("/api/v1/health"),
      httpClient.get<AppVersion>("/api/v1/version"),
    ])
      .then(([health, version]) => {
        if (cancelled) return;
        setData({ health, version });
        notify({
          title: "Backend reachable",
          description: `${health.service} is ${health.status}`,
          variant: "success",
        });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message = err instanceof HttpError ? err.message : "Could not reach the backend API.";
        setError(message);
        notify({ title: "Backend unreachable", description: message, variant: "error" });
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [refreshKey, notify]);

  useEffect(() => {
    if (!ipcBridge.isAvailable()) return;
    ipcBridge
      .getAppInfo()
      .then(setAppInfo)
      .catch(() => setAppInfo(null));
  }, []);

  return (
    <div className="mx-auto flex max-w-lg flex-col gap-4">
      <div>
        <h2 className="text-sm font-medium text-foreground">System status</h2>
        <p className="text-xs text-muted-foreground">
          Confirms the frontend, backend, and (when running inside Electron) IPC bridge are all
          wired together.
        </p>
      </div>

      {isLoading ? <LoadingSpinner label="Checking backend…" /> : null}

      {error && !isLoading ? (
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          <p className="font-medium">Backend unreachable</p>
          <p className="mt-1 opacity-80">{error}</p>
          <Button
            className="mt-3"
            size="sm"
            onClick={() => {
              setIsLoading(true);
              setError(null);
              setRefreshKey((key) => key + 1);
            }}
          >
            Retry
          </Button>
        </div>
      ) : null}

      {data && !isLoading && !error ? (
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 rounded-lg border border-border bg-card p-4 text-sm">
          <dt className="text-muted-foreground">Status</dt>
          <dd className="font-medium text-foreground">{data.health.status}</dd>
          <dt className="text-muted-foreground">Service</dt>
          <dd>{data.health.service}</dd>
          <dt className="text-muted-foreground">Environment</dt>
          <dd>{data.health.environment}</dd>
          <dt className="text-muted-foreground">Version</dt>
          <dd>{data.version.version}</dd>
          <dt className="text-muted-foreground">Checked at</dt>
          <dd>{new Date(data.health.timestamp).toLocaleString()}</dd>
        </dl>
      ) : null}

      {appInfo ? (
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 rounded-lg border border-border bg-card p-4 text-sm">
          <dt className="col-span-2 text-xs font-medium text-muted-foreground">
            Electron IPC bridge
          </dt>
          <dt className="text-muted-foreground">App</dt>
          <dd>{appInfo.name}</dd>
          <dt className="text-muted-foreground">Version</dt>
          <dd>{appInfo.version}</dd>
          <dt className="text-muted-foreground">Environment</dt>
          <dd>{appInfo.environment}</dd>
        </dl>
      ) : null}
    </div>
  );
}
