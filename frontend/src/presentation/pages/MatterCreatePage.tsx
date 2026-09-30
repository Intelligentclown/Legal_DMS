import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useNotifications } from "@/app/providers/NotificationProvider";
import { getParty } from "@/infrastructure/api/partiesApi";
import { listMatterStatuses, listMatterTypes } from "@/infrastructure/api/lookupsApi";
import { createMatter } from "@/infrastructure/api/mattersApi";
import type { MatterStatus, MatterType } from "@/domain/types/lookup";
import { Breadcrumbs } from "@/presentation/components/Breadcrumbs";
import { ErrorMessage } from "@/presentation/components/ErrorMessage";
import { LoadingSpinner } from "@/presentation/components/LoadingSpinner";
import { SelectField, TextAreaField, TextField } from "@/presentation/components/form/Fields";
import { cardClassName, formClassName } from "@/presentation/components/form/styles";
import { PageHeader } from "@/presentation/components/PageHeader";
import { Button } from "@/presentation/components/ui/button";
import { useAsyncResource } from "@/presentation/hooks/useAsyncResource";

const MAX_MATTER_NUMBER_LENGTH = 50;
const MAX_TITLE_LENGTH = 255;

interface MatterForm {
  matterNumber: string;
  matterTypeId: string;
  matterStatusId: string;
  title: string;
  description: string;
  openedAt: string;
}

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

/** `datetime-local` needs a wall-clock string in the viewer's own timezone. */
function toLocalInputValue(date: Date): string {
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  );
}

/**
 * The backend has no "allocate a matter number" route, so a human-readable
 * suggestion is generated once per form load and stays editable. The user may
 * replace it freely, and the backend still owns the record of what was saved.
 */
function suggestMatterNumber(now: Date): string {
  const stamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}`;
  const suffix = Math.random().toString(36).slice(2, 8).toUpperCase();
  return `MAT-${stamp}-${suffix}`;
}

function validate(form: MatterForm): Record<string, string> {
  const errors: Record<string, string> = {};

  if (!form.matterNumber.trim()) {
    errors.matterNumber = "Matter number is required.";
  }
  if (!form.matterTypeId) {
    errors.matterTypeId = "Choose a matter type.";
  }
  if (!form.matterStatusId) {
    errors.matterStatusId = "Choose a matter status.";
  }
  if (!form.title.trim()) {
    errors.title = "Title is required.";
  }
  if (!form.openedAt) {
    errors.openedAt = "Opened date is required.";
  }

  return errors;
}

interface MatterContext {
  partyName: string;
  matterTypes: MatterType[];
  matterStatuses: MatterStatus[];
}

/**
 * Opens a new Matter with the Party reached through the route as its canonical
 * client. The client is never chosen by typing an identifier: the route already
 * carries the Party this form was opened from.
 */
export function MatterCreatePage() {
  const { partyId } = useParams<{ partyId: string }>();
  const navigate = useNavigate();
  const { notify } = useNotifications();

  const [form, setForm] = useState<MatterForm>(() => ({
    matterNumber: suggestMatterNumber(new Date()),
    matterTypeId: "",
    matterStatusId: "",
    title: "",
    description: "",
    openedAt: toLocalInputValue(new Date()),
  }));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<unknown>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const context = useAsyncResource<MatterContext>(`matter-create:${partyId}`, async () => {
    if (!partyId) {
      throw new Error("No party was selected for this matter.");
    }

    const [party, matterTypes, matterStatuses] = await Promise.all([
      getParty(partyId),
      listMatterTypes(),
      listMatterStatuses(),
    ]);

    return { partyName: party.display_name, matterTypes, matterStatuses };
  });

  function update<K extends keyof MatterForm>(field: K, value: MatterForm[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const validationErrors = validate(form);
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0 || !partyId) {
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const matter = await createMatter({
        matter_number: form.matterNumber.trim(),
        matter_type_id: form.matterTypeId,
        matter_status_id: form.matterStatusId,
        title: form.title.trim(),
        description: form.description.trim() || null,
        opened_at: new Date(form.openedAt).toISOString(),
        client_party_id: partyId,
      });

      notify({
        variant: "success",
        title: "Matter created",
        description: `${matter.matter_number} is ready for files.`,
      });
      void navigate(`/matters/${matter.id}`);
    } catch (error) {
      setSubmitError(error);
    } finally {
      setIsSubmitting(false);
    }
  }

  if (context.isLoading) {
    return (
      <div className="mx-auto flex max-w-2xl items-center justify-center py-12">
        <LoadingSpinner label="Loading matter types and statuses…" />
      </div>
    );
  }

  if (context.error || !context.data) {
    return (
      <div className="mx-auto flex max-w-2xl flex-col gap-4">
        <Breadcrumbs items={[{ label: "Parties", to: "/parties" }, { label: "New matter" }]} />
        <ErrorMessage error={context.error} title="Could not start a new matter" />
        <Button asChild variant="outline" size="sm" className="self-start">
          <Link to="/parties">Back to parties</Link>
        </Button>
      </div>
    );
  }

  const { partyName, matterTypes, matterStatuses } = context.data;
  const typeOptions = matterTypes
    .filter((matterType) => matterType.is_active)
    .map((matterType) => ({
      value: matterType.id,
      label: `${matterType.name} (${matterType.code})`,
    }));
  const statusOptions = matterStatuses.map((matterStatus) => ({
    value: matterStatus.id,
    label: matterStatus.is_terminal
      ? `${matterStatus.name} (${matterStatus.code}) — terminal`
      : `${matterStatus.name} (${matterStatus.code})`,
  }));

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4">
      <Breadcrumbs
        items={[
          { label: "Parties", to: "/parties" },
          { label: partyName },
          { label: "New matter" },
        ]}
      />
      <PageHeader
        title="New matter"
        description={`${partyName} will be recorded as the client on this matter.`}
      />

      <form className={`${cardClassName} ${formClassName}`} onSubmit={handleSubmit} noValidate>
        <TextField
          label="Matter number"
          value={form.matterNumber}
          onChange={(value) => update("matterNumber", value)}
          hint="Pre-filled as a suggestion. Edit it if your practice numbers matters differently."
          error={errors.matterNumber}
          maxLength={MAX_MATTER_NUMBER_LENGTH}
          disabled={isSubmitting}
        />
        <SelectField
          label="Matter type"
          value={form.matterTypeId}
          onChange={(value) => update("matterTypeId", value)}
          options={typeOptions}
          placeholder="Choose a type…"
          error={errors.matterTypeId}
          disabled={isSubmitting}
        />
        <SelectField
          label="Matter status"
          value={form.matterStatusId}
          onChange={(value) => update("matterStatusId", value)}
          options={statusOptions}
          placeholder="Choose a status…"
          error={errors.matterStatusId}
          disabled={isSubmitting}
        />
        <TextField
          label="Title"
          value={form.title}
          onChange={(value) => update("title", value)}
          error={errors.title}
          maxLength={MAX_TITLE_LENGTH}
          disabled={isSubmitting}
        />
        <TextField
          label="Opened at"
          type="datetime-local"
          value={form.openedAt}
          onChange={(value) => update("openedAt", value)}
          error={errors.openedAt}
          disabled={isSubmitting}
        />
        <TextAreaField
          label="Description"
          value={form.description}
          onChange={(value) => update("description", value)}
          hint="Optional."
          disabled={isSubmitting}
        />

        <ErrorMessage error={submitError} title="Could not create the matter" />

        <div className="flex items-center gap-2">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Creating…" : "Create matter"}
          </Button>
          <Button asChild type="button" variant="outline" disabled={isSubmitting}>
            <Link to="/parties">Cancel</Link>
          </Button>
        </div>
      </form>
    </div>
  );
}
