import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { createEnquiry } from "@/infrastructure/api/enquiriesApi";
import { Button } from "@/presentation/components/ui/button";
import { ErrorMessage } from "@/presentation/components/ErrorMessage";
import { TextAreaField, TextField } from "@/presentation/components/form/Fields";
import { cardClassName, formClassName } from "@/presentation/components/form/styles";
import { PageHeader } from "@/presentation/components/PageHeader";

interface Form {
  name: string;
  phone: string;
  email: string;
  description: string;
  source: string;
}
const EMPTY: Form = { name: "", phone: "", email: "", description: "", source: "" };

/** Creates prospect-only intake. A canonical Party is deliberately linked later and explicitly. */
export function EnquiryCreatePage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<Form>(EMPTY);
  const [error, setError] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);
  const set = <K extends keyof Form>(key: K, value: Form[K]) =>
    setForm((current) => ({ ...current, [key]: value }));
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!form.name.trim()) {
      setError(new Error("A prospect name is required until a Party is linked."));
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const enquiry = await createEnquiry({
        prospect_display_name: form.name.trim(),
        prospect_phone: form.phone.trim() || null,
        prospect_email: form.email.trim() || null,
        prospect_description: form.description.trim() || null,
        prospect_source: form.source.trim() || null,
      });
      void navigate(`/enquiries/${enquiry.id}`);
    } catch (cause) {
      setError(cause);
    } finally {
      setSaving(false);
    }
  }
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4">
      <PageHeader
        title="New enquiry"
        description="Record the prospective engagement; select a Party later when one is known."
      />
      <form className={`${cardClassName} ${formClassName}`} onSubmit={submit} noValidate>
        <TextField
          label="Prospect name"
          value={form.name}
          onChange={(value) => set("name", value)}
          required
          disabled={saving}
          maxLength={255}
        />
        <TextField
          label="Phone"
          type="tel"
          value={form.phone}
          onChange={(value) => set("phone", value)}
          disabled={saving}
          maxLength={20}
        />
        <TextField
          label="Email"
          type="email"
          value={form.email}
          onChange={(value) => set("email", value)}
          disabled={saving}
          maxLength={255}
        />
        <TextField
          label="Source"
          value={form.source}
          onChange={(value) => set("source", value)}
          disabled={saving}
          maxLength={255}
        />
        <TextAreaField
          label="Description"
          value={form.description}
          onChange={(value) => set("description", value)}
          disabled={saving}
          maxLength={2000}
        />
        <ErrorMessage error={error} title="Could not create enquiry" />
        <div className="flex gap-2">
          <Button type="submit" disabled={saving}>
            {saving ? "Creating…" : "Create enquiry"}
          </Button>
          <Button asChild variant="outline" type="button">
            <Link to="/enquiries">Cancel</Link>
          </Button>
        </div>
      </form>
    </div>
  );
}
