import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useNotifications } from "@/app/providers/NotificationProvider";
import { createParty } from "@/infrastructure/api/partiesApi";
import type { PartyType } from "@/domain/types/party";
import { Breadcrumbs } from "@/presentation/components/Breadcrumbs";
import { ErrorMessage } from "@/presentation/components/ErrorMessage";
import { SelectField, TextAreaField, TextField } from "@/presentation/components/form/Fields";
import { cardClassName, formClassName } from "@/presentation/components/form/styles";
import { PageHeader } from "@/presentation/components/PageHeader";
import { Button } from "@/presentation/components/ui/button";

/**
 * The backend's own `party_type` literal. Offered as a plain two-value choice
 * because the backend exposes no lookup route for it.
 */
const PARTY_TYPE_OPTIONS: { value: PartyType; label: string }[] = [
  { value: "individual", label: "Individual" },
  { value: "organization", label: "Organization" },
];

const MIN_PHONE_LENGTH = 7;

interface PartyForm {
  partyType: PartyType | "";
  displayName: string;
  primaryPhone: string;
  primaryEmail: string;
  notes: string;
}

const INITIAL_FORM: PartyForm = {
  partyType: "",
  displayName: "",
  primaryPhone: "",
  primaryEmail: "",
  notes: "",
};

function validate(form: PartyForm): Record<string, string> {
  const errors: Record<string, string> = {};

  if (!form.partyType) {
    errors.partyType = "Choose whether this is an individual or an organization.";
  }
  if (!form.displayName.trim()) {
    errors.displayName = "Display name is required.";
  }
  if (form.primaryPhone.trim().length < MIN_PHONE_LENGTH) {
    errors.primaryPhone = `Primary phone must be at least ${MIN_PHONE_LENGTH} characters.`;
  }
  if (form.primaryEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.primaryEmail.trim())) {
    errors.primaryEmail = "Enter a valid email address or leave it blank.";
  }

  return errors;
}

/** Collects a new Party, which later becomes the canonical client on a Matter. */
export function PartyCreatePage() {
  const navigate = useNavigate();
  const { notify } = useNotifications();

  const [form, setForm] = useState<PartyForm>(INITIAL_FORM);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<unknown>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function update<K extends keyof PartyForm>(field: K, value: PartyForm[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const validationErrors = validate(form);
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) {
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const party = await createParty({
        party_type: form.partyType as PartyType,
        display_name: form.displayName.trim(),
        primary_phone: form.primaryPhone.trim(),
        primary_email: form.primaryEmail.trim() || null,
        notes: form.notes.trim() || null,
      });

      notify({
        variant: "success",
        title: "Party created",
        description: `${party.display_name} can now be selected as the client on a matter.`,
      });
      void navigate("/parties");
    } catch (error) {
      setSubmitError(error);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4">
      <Breadcrumbs items={[{ label: "Parties", to: "/parties" }, { label: "New party" }]} />
      <PageHeader
        title="New party"
        description="A party is the reusable identity this practice acts for. A matter records exactly one of them as its client."
      />

      <form className={`${cardClassName} ${formClassName}`} onSubmit={handleSubmit} noValidate>
        <SelectField
          label="Party type"
          value={form.partyType}
          onChange={(value) => update("partyType", value as PartyType | "")}
          options={PARTY_TYPE_OPTIONS}
          placeholder="Choose a type…"
          error={errors.partyType}
          disabled={isSubmitting}
        />
        <TextField
          label="Display name"
          value={form.displayName}
          onChange={(value) => update("displayName", value)}
          error={errors.displayName}
          maxLength={255}
          disabled={isSubmitting}
        />
        <TextField
          label="Primary phone"
          type="tel"
          value={form.primaryPhone}
          onChange={(value) => update("primaryPhone", value)}
          error={errors.primaryPhone}
          maxLength={50}
          disabled={isSubmitting}
        />
        <TextField
          label="Primary email"
          type="email"
          value={form.primaryEmail}
          onChange={(value) => update("primaryEmail", value)}
          hint="Optional."
          error={errors.primaryEmail}
          maxLength={255}
          disabled={isSubmitting}
        />
        <TextAreaField
          label="Notes"
          value={form.notes}
          onChange={(value) => update("notes", value)}
          hint="Optional. Only free text the practice already keeps alongside a party."
          disabled={isSubmitting}
        />

        <ErrorMessage error={submitError} title="Could not create the party" />

        <div className="flex items-center gap-2">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Creating…" : "Create party"}
          </Button>
          <Button asChild type="button" variant="outline" disabled={isSubmitting}>
            <Link to="/parties">Cancel</Link>
          </Button>
        </div>
      </form>
    </div>
  );
}
