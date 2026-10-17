import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import type { Enquiry } from "@/domain/types/enquiry";
import {
  createQuotation,
  getEnquiry,
  linkEnquiryParty,
  listQuotations,
  updateEnquiry,
} from "@/infrastructure/api/enquiriesApi";
import { listParties } from "@/infrastructure/api/partiesApi";
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

interface Form {
  name: string;
  phone: string;
  email: string;
  description: string;
  source: string;
}
function toForm(enquiry: Enquiry): Form {
  return {
    name: enquiry.prospect_display_name ?? "",
    phone: enquiry.prospect_phone ?? "",
    email: enquiry.prospect_email ?? "",
    description: enquiry.prospect_description ?? "",
    source: enquiry.prospect_source ?? "",
  };
}

export function EnquiryDetailPage() {
  const { enquiryId } = useParams<{ enquiryId: string }>();
  const navigate = useNavigate();
  const resource = useAsyncResource(`enquiry:${enquiryId}`, async () => {
    if (!enquiryId) throw new Error("No enquiry was selected.");
    const [enquiry, quotations, parties] = await Promise.all([
      getEnquiry(enquiryId),
      listQuotations(enquiryId),
      listParties({ pageSize: 100 }),
    ]);
    return { enquiry, quotations: quotations.items, parties: parties.items };
  });
  const [form, setForm] = useState<Form | null>(null);
  const [partyId, setPartyId] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);
  const visibleForm = form ?? (resource.data ? toForm(resource.data.enquiry) : null);
  const set = <K extends keyof Form>(key: K, value: Form[K]) =>
    setForm((current) => ({
      ...(current ?? (resource.data ? toForm(resource.data.enquiry) : toForm({} as Enquiry))),
      [key]: value,
    }));
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!enquiryId || !visibleForm) return;
    setSaving(true);
    setError(null);
    try {
      await updateEnquiry(enquiryId, {
        prospect_display_name: visibleForm.name.trim() || null,
        prospect_phone: visibleForm.phone.trim() || null,
        prospect_email: visibleForm.email.trim() || null,
        prospect_description: visibleForm.description.trim() || null,
        prospect_source: visibleForm.source.trim() || null,
      });
      setForm(null);
    } catch (cause) {
      setError(cause);
    } finally {
      setSaving(false);
    }
  }
  async function linkParty() {
    if (!enquiryId || !partyId) return;
    setSaving(true);
    setError(null);
    try {
      await linkEnquiryParty(enquiryId, partyId);
      void navigate(0);
    } catch (cause) {
      setError(cause);
    } finally {
      setSaving(false);
    }
  }
  async function newQuotation() {
    if (!enquiryId) return;
    setSaving(true);
    setError(null);
    try {
      const quotation = await createQuotation(enquiryId);
      void navigate(`/enquiries/${enquiryId}/quotations/${quotation.id}`);
    } catch (cause) {
      setError(cause);
    } finally {
      setSaving(false);
    }
  }
  if (resource.isLoading)
    return (
      <div className="py-12">
        <LoadingSpinner label="Loading enquiry…" />
      </div>
    );
  if (resource.error || !resource.data || !visibleForm)
    return <ErrorMessage error={resource.error} title="Could not load enquiry" />;
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-4">
      <PageHeader
        title="Enquiry"
        description="Keep prospect evidence current; Party linking is explicit and uses an existing Party."
      />
      <form className={`${cardClassName} ${formClassName}`} onSubmit={save} noValidate>
        <TextField
          label="Prospect name"
          value={visibleForm.name}
          onChange={(value) => set("name", value)}
          disabled={saving}
          maxLength={255}
        />
        <TextField
          label="Phone"
          type="tel"
          value={visibleForm.phone}
          onChange={(value) => set("phone", value)}
          disabled={saving}
          maxLength={20}
        />
        <TextField
          label="Email"
          type="email"
          value={visibleForm.email}
          onChange={(value) => set("email", value)}
          disabled={saving}
          maxLength={255}
        />
        <TextField
          label="Source"
          value={visibleForm.source}
          onChange={(value) => set("source", value)}
          disabled={saving}
          maxLength={255}
        />
        <TextAreaField
          label="Description"
          value={visibleForm.description}
          onChange={(value) => set("description", value)}
          disabled={saving}
          maxLength={2000}
        />
        <Button type="submit" disabled={saving}>
          Save enquiry
        </Button>
      </form>
      <section className={`${cardClassName} flex flex-col gap-3`}>
        <h2 className="font-semibold">Canonical Party</h2>
        <p className="text-sm text-muted-foreground">
          {resource.data.enquiry.party_id
            ? "A Party is linked. Acceptance can proceed only with this same-organization Party."
            : "No Party is linked. Select an existing Party before acceptance; this workflow never creates one automatically."}
        </p>
        <SelectField
          label="Existing Party"
          value={partyId}
          onChange={setPartyId}
          options={resource.data.parties.map((party) => ({
            value: party.id,
            label: party.display_name,
          }))}
          placeholder="Select a Party…"
          disabled={saving}
        />
        <Button type="button" onClick={() => void linkParty()} disabled={saving || !partyId}>
          Link Party
        </Button>
      </section>
      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Quotations</h2>
          <Button type="button" size="sm" onClick={() => void newQuotation()} disabled={saving}>
            New quotation
          </Button>
        </div>
        {resource.data.quotations.length ? (
          <table className={tableClassName}>
            <thead>
              <tr>
                <th className={headerCellClassName}>Created</th>
                <th className={headerCellClassName}>Action</th>
              </tr>
            </thead>
            <tbody>
              {resource.data.quotations.map((quotation) => (
                <tr key={quotation.id}>
                  <td className={cellClassName}>{quotation.created_at ?? "—"}</td>
                  <td className={cellClassName}>
                    <Button asChild size="sm" variant="outline">
                      <Link to={`/enquiries/${enquiryId}/quotations/${quotation.id}`}>Open</Link>
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-sm text-muted-foreground">No quotations yet.</p>
        )}
      </section>
      <ErrorMessage error={error} title="Could not update enquiry workflow" />
    </div>
  );
}
