import { useRef, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useNotifications } from "@/app/providers/NotificationProvider";
import type { AcceptanceMatterCreate } from "@/domain/types/enquiry";
import {
  acceptQuotationRevision,
  createQuotationRevision,
  getEnquiry,
  getQuotation,
  issueQuotationRevision,
  listQuotationRevisions,
} from "@/infrastructure/api/enquiriesApi";
import { listMatterStatuses, listMatterTypes } from "@/infrastructure/api/lookupsApi";
import { Button } from "@/presentation/components/ui/button";
import { ErrorMessage } from "@/presentation/components/ErrorMessage";
import { LoadingSpinner } from "@/presentation/components/LoadingSpinner";
import { PageHeader } from "@/presentation/components/PageHeader";
import { SelectField, TextAreaField, TextField } from "@/presentation/components/form/Fields";
import {
  cardClassName,
  cellClassName,
  formClassName,
  headerCellClassName,
  tableClassName,
} from "@/presentation/components/form/styles";
import { useAsyncResource } from "@/presentation/hooks/useAsyncResource";

function initialMatter(): AcceptanceMatterCreate {
  return {
    matter_number: "",
    matter_type_id: "",
    matter_status_id: "",
    title: "",
    description: null,
    opened_at: "",
  };
}
function fingerprint(revisionId: string, payload: AcceptanceMatterCreate): string {
  return JSON.stringify({ revisionId, ...payload });
}
function keyFor(map: Map<string, string>, value: string): string {
  const existing = map.get(value);
  if (existing) return existing;
  const key =
    globalThis.crypto?.randomUUID?.() ??
    `accept-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  map.set(value, key);
  return key;
}
function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Revision evidence, one-time issuance, and exact-revision acceptance in one hierarchy-bound view. */
export function QuotationDetailPage() {
  const { enquiryId, quotationId } = useParams<{ enquiryId: string; quotationId: string }>();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const resource = useAsyncResource(`quotation:${enquiryId}:${quotationId}`, async () => {
    if (!enquiryId || !quotationId) throw new Error("No quotation was selected.");
    const [enquiry, quotation, revisions, types, statuses] = await Promise.all([
      getEnquiry(enquiryId),
      getQuotation(enquiryId, quotationId),
      listQuotationRevisions(enquiryId, quotationId),
      listMatterTypes(),
      listMatterStatuses(),
    ]);
    return { enquiry, quotation, revisions, types, statuses };
  });
  const [snapshot, setSnapshot] = useState("{\n  \n}");
  const [selected, setSelected] = useState("");
  const [matter, setMatterForm] = useState(initialMatter);
  const [error, setError] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);
  const keys = useRef(new Map<string, string>());
  async function createRevision(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!enquiryId || !quotationId) return;
    let parsed: unknown;
    try {
      parsed = JSON.parse(snapshot);
    } catch {
      setError(new Error("Proposal snapshot must be valid JSON."));
      return;
    }
    if (!isObject(parsed) || Object.keys(parsed).length === 0) {
      setError(new Error("Proposal snapshot must be a non-empty JSON object."));
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await createQuotationRevision(enquiryId, quotationId, parsed);
      void navigate(0);
    } catch (cause) {
      setError(cause);
    } finally {
      setSaving(false);
    }
  }
  async function issue(revisionId: string) {
    if (!enquiryId || !quotationId) return;
    setSaving(true);
    setError(null);
    try {
      await issueQuotationRevision(enquiryId, quotationId, revisionId);
      void navigate(0);
    } catch (cause) {
      setError(cause);
    } finally {
      setSaving(false);
    }
  }
  async function accept(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!enquiryId || !quotationId || !selected) return;
    if (
      !matter.matter_number.trim() ||
      !matter.matter_type_id ||
      !matter.matter_status_id ||
      !matter.title.trim() ||
      !matter.opened_at
    ) {
      setError(new Error("Complete every required Matter field before acceptance."));
      return;
    }
    const payload = {
      ...matter,
      matter_number: matter.matter_number.trim(),
      title: matter.title.trim(),
      description: matter.description?.trim() || null,
      opened_at: new Date(matter.opened_at).toISOString(),
    };
    setSaving(true);
    setError(null);
    try {
      const result = await acceptQuotationRevision(
        enquiryId,
        quotationId,
        selected,
        payload,
        keyFor(keys.current, fingerprint(selected, payload)),
      );
      if (result.status === 201) {
        notify({
          variant: "success",
          title: "Acceptance recorded",
          description: "A new Matter was created.",
        });
      } else if (result.status === 200) {
        notify({
          variant: "success",
          title: "Acceptance replayed",
          description: "The existing Matter is being opened.",
        });
      } else {
        throw new Error(`Unexpected acceptance response status ${result.status}.`);
      }
      void navigate(`/matters/${result.acceptance.matter_id}`);
    } catch (cause) {
      setError(cause);
    } finally {
      setSaving(false);
    }
  }
  if (resource.isLoading)
    return (
      <div className="py-12">
        <LoadingSpinner label="Loading quotation…" />
      </div>
    );
  if (resource.error || !resource.data)
    return <ErrorMessage error={resource.error} title="Could not load quotation" />;
  const eligible = resource.data.revisions.filter(
    (revision) => revision.issued_at !== null && revision.issued_by !== null,
  );
  const updateMatter = <K extends keyof AcceptanceMatterCreate>(
    key: K,
    value: AcceptanceMatterCreate[K],
  ) => setMatterForm((current) => ({ ...current, [key]: value }));
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-4">
      <PageHeader
        title="Quotation"
        description="Each revision is immutable evidence. Issue exactly once before it can be accepted."
      />
      <form className={`${cardClassName} ${formClassName}`} onSubmit={createRevision} noValidate>
        <TextAreaField
          label="Proposal snapshot (JSON)"
          value={snapshot}
          onChange={setSnapshot}
          disabled={saving}
          hint="Provide the exact offered proposal as a non-empty JSON object. This screen does not invent financial fields."
        />
        <Button type="submit" disabled={saving}>
          Create revision
        </Button>
      </form>
      <section>
        <h2 className="mb-3 text-lg font-semibold">Revision history</h2>
        {resource.data.revisions.length ? (
          <table className={tableClassName}>
            <thead>
              <tr>
                <th className={headerCellClassName}>Revision</th>
                <th className={headerCellClassName}>Issued</th>
                <th className={headerCellClassName}>Proposal evidence</th>
                <th className={headerCellClassName}>Action</th>
              </tr>
            </thead>
            <tbody>
              {resource.data.revisions.map((revision) => (
                <tr key={revision.id}>
                  <td className={cellClassName}>#{revision.ordinal}</td>
                  <td className={cellClassName}>{revision.issued_at ?? "Not issued"}</td>
                  <td className={cellClassName}>
                    <details>
                      <summary>View snapshot</summary>
                      <pre className="mt-2 max-w-md overflow-auto whitespace-pre-wrap text-xs">
                        {JSON.stringify(revision.proposal_snapshot, null, 2)}
                      </pre>
                    </details>
                  </td>
                  <td className={cellClassName}>
                    {revision.issued_at || revision.issued_by ? (
                      "Issued"
                    ) : (
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        disabled={saving}
                        onClick={() => void issue(revision.id)}
                      >
                        Issue revision
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-sm text-muted-foreground">No revisions yet.</p>
        )}
      </section>
      <form className={`${cardClassName} ${formClassName}`} onSubmit={accept} noValidate>
        <h2 className="text-lg font-semibold">Accept an issued revision</h2>
        {resource.data.enquiry.party_id ? null : (
          <p className="text-sm text-destructive">
            Acceptance is unavailable until an existing Party is linked to the enquiry.
          </p>
        )}
        <SelectField
          label="Exact issued revision"
          value={selected}
          onChange={setSelected}
          options={eligible.map((revision) => ({
            value: revision.id,
            label: `Revision #${revision.ordinal}`,
          }))}
          placeholder="Choose an issued revision…"
          disabled={saving || !resource.data.enquiry.party_id}
        />
        <TextField
          label="Matter number"
          value={matter.matter_number}
          onChange={(value) => updateMatter("matter_number", value)}
          disabled={saving}
          required
          maxLength={50}
        />
        <SelectField
          label="Matter type"
          value={matter.matter_type_id}
          onChange={(value) => updateMatter("matter_type_id", value)}
          options={resource.data.types
            .filter((item) => item.is_active)
            .map((item) => ({ value: item.id, label: `${item.name} (${item.code})` }))}
          disabled={saving}
        />
        <SelectField
          label="Matter status"
          value={matter.matter_status_id}
          onChange={(value) => updateMatter("matter_status_id", value)}
          options={resource.data.statuses.map((item) => ({
            value: item.id,
            label: `${item.name} (${item.code})`,
          }))}
          disabled={saving}
        />
        <TextField
          label="Matter title"
          value={matter.title}
          onChange={(value) => updateMatter("title", value)}
          disabled={saving}
          required
          maxLength={255}
        />
        <TextField
          label="Opened at"
          type="datetime-local"
          value={matter.opened_at}
          onChange={(value) => updateMatter("opened_at", value)}
          disabled={saving}
          required
        />
        <TextAreaField
          label="Matter description"
          value={matter.description ?? ""}
          onChange={(value) => updateMatter("description", value)}
          disabled={saving}
        />
        <Button type="submit" disabled={saving || !selected || !resource.data.enquiry.party_id}>
          {saving ? "Accepting…" : "Confirm acceptance and create Matter"}
        </Button>
      </form>
      <ErrorMessage error={error} title="Could not complete quotation workflow" />
      <Button asChild variant="outline" size="sm" className="self-start">
        <Link to={`/enquiries/${enquiryId}`}>Back to enquiry</Link>
      </Button>
    </div>
  );
}
