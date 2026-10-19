import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { useNotifications } from "@/app/providers/NotificationProvider";
import { createMatterFile, listMatterFiles } from "@/infrastructure/api/filesApi";
import { listMatterStatuses, listMatterTypes } from "@/infrastructure/api/lookupsApi";
import {
  getMatter,
  linkMatterProperty,
  listMatterProperties,
  unlinkMatterProperty,
} from "@/infrastructure/api/mattersApi";
import { getParty } from "@/infrastructure/api/partiesApi";
import { listProperties } from "@/infrastructure/api/propertiesApi";
import type { Matter } from "@/domain/types/matter";
import type { Property } from "@/domain/types/property";
import type { MatterStatus, MatterType } from "@/domain/types/lookup";
import type { Party } from "@/domain/types/party";
import { Breadcrumbs } from "@/presentation/components/Breadcrumbs";
import { DetailList } from "@/presentation/components/DetailList";
import { EmptyState } from "@/presentation/components/EmptyState";
import { ErrorMessage } from "@/presentation/components/ErrorMessage";
import { LoadingSpinner } from "@/presentation/components/LoadingSpinner";
import { PageHeader } from "@/presentation/components/PageHeader";
import { PaginationControls } from "@/presentation/components/PaginationControls";
import { SelectField, TextField } from "@/presentation/components/form/Fields";
import {
  cardClassName,
  cellClassName,
  formClassName,
  headerCellClassName,
  tableClassName,
} from "@/presentation/components/form/styles";
import { Button } from "@/presentation/components/ui/button";
import { useAsyncResource } from "@/presentation/hooks/useAsyncResource";

const MAX_FILE_TITLE_LENGTH = 255;

interface MatterContext {
  matter: Matter;
  clientParty: Party | null;
  matterTypes: MatterType[];
  matterStatuses: MatterStatus[];
}

function formatDate(value: string | null): string | null {
  if (!value) {
    return null;
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString();
}

function nameOf<T extends { id: string; name: string }>(collection: T[], id: string): string {
  return collection.find((entry) => entry.id === id)?.name ?? "Unknown";
}

function propertyLabel(property: Property): string {
  const subdivision = property.sub_division_number ? `/${property.sub_division_number}` : "";
  return `Survey ${property.survey_number}${subdivision} (${property.property_type})`;
}

/**
 * Matter read surface: the matter's own record with its client resolved to a
 * Party's display name, plus the File collection that hangs off it. File numbers
 * are shown exactly as the backend allocated them.
 */
export function MatterDetailPage() {
  const { matterId } = useParams<{ matterId: string }>();
  const { notify } = useNotifications();

  const [filesPage, setFilesPage] = useState(1);
  const [fileTitle, setFileTitle] = useState("");
  const [fileTitleError, setFileTitleError] = useState<string | null>(null);
  const [fileError, setFileError] = useState<unknown>(null);
  const [isCreatingFile, setIsCreatingFile] = useState(false);
  const [propertiesPage, setPropertiesPage] = useState(1);
  const [selectedPropertyId, setSelectedPropertyId] = useState("");
  const [associationError, setAssociationError] = useState<unknown>(null);
  const [unlinkError, setUnlinkError] = useState<unknown>(null);
  const [isLinkingProperty, setIsLinkingProperty] = useState(false);
  const [unlinkingPropertyId, setUnlinkingPropertyId] = useState<string | null>(null);

  const context = useAsyncResource<MatterContext>(`matter:${matterId}`, async () => {
    if (!matterId) {
      throw new Error("No matter was selected.");
    }

    const [matter, matterTypes, matterStatuses] = await Promise.all([
      getMatter(matterId),
      listMatterTypes(),
      listMatterStatuses(),
    ]);

    const clientParticipant = matter.participants.find(
      (participant) => participant.role === "client",
    );
    const clientParty = clientParticipant ? await getParty(clientParticipant.party_id) : null;

    return { matter, clientParty, matterTypes, matterStatuses };
  });

  const files = useAsyncResource(`files:${matterId}:${filesPage}`, () => {
    if (!matterId) {
      return Promise.resolve({ items: [], pagination: null });
    }
    return listMatterFiles(matterId, { page: filesPage });
  });

  const associatedProperties = useAsyncResource(`matter-properties:${matterId}`, () => {
    if (!matterId) {
      return Promise.resolve([]);
    }
    return listMatterProperties(matterId);
  });

  const availableProperties = useAsyncResource(`properties:${propertiesPage}`, () =>
    listProperties({ page: propertiesPage }),
  );

  async function handleCreateFile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!fileTitle.trim()) {
      setFileTitleError("File title is required.");
      return;
    }
    if (!matterId) {
      return;
    }

    setFileTitleError(null);
    setIsCreatingFile(true);
    setFileError(null);
    try {
      const created = await createMatterFile(matterId, { title: fileTitle.trim() });
      notify({
        variant: "success",
        title: "File created",
        description: `File number ${created.file_number} was assigned by the backend.`,
      });
      setFileTitle("");
      setFilesPage(1);
      files.reload();
    } catch (error) {
      setFileError(error);
    } finally {
      setIsCreatingFile(false);
    }
  }

  async function handleLinkProperty(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!matterId || !selectedPropertyId) {
      return;
    }

    setAssociationError(null);
    setIsLinkingProperty(true);
    try {
      const result = await linkMatterProperty(matterId, selectedPropertyId);
      notify({
        variant: "success",
        title: result.created ? "Property linked" : "Property already linked",
        description: result.created
          ? `${propertyLabel(result.property)} is now associated with this matter.`
          : `${propertyLabel(result.property)} was already associated; no duplicate was created.`,
      });
      setSelectedPropertyId("");
      associatedProperties.reload();
    } catch (error) {
      setAssociationError(error);
    } finally {
      setIsLinkingProperty(false);
    }
  }

  async function handleUnlinkProperty(property: Property) {
    if (!matterId) {
      return;
    }

    setUnlinkError(null);
    setUnlinkingPropertyId(property.id);
    try {
      await unlinkMatterProperty(matterId, property.id);
      notify({
        variant: "success",
        title: "Property unlinked",
        description: `${propertyLabel(property)} is no longer associated with this matter.`,
      });
      associatedProperties.reload();
    } catch (error) {
      setUnlinkError(error);
    } finally {
      setUnlinkingPropertyId(null);
    }
  }

  if (context.isLoading) {
    return (
      <div className="mx-auto flex max-w-4xl items-center justify-center py-12">
        <LoadingSpinner label="Loading matter…" />
      </div>
    );
  }

  if (context.error || !context.data) {
    return (
      <div className="mx-auto flex max-w-4xl flex-col gap-4">
        <ErrorMessage error={context.error} title="Could not load the matter" />
        <Button asChild variant="outline" size="sm" className="self-start">
          <Link to="/matters">Back to matters</Link>
        </Button>
      </div>
    );
  }

  const { matter, clientParty, matterTypes, matterStatuses } = context.data;

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <Breadcrumbs
        items={[{ label: "Matters", to: "/matters" }, { label: matter.matter_number }]}
      />
      <PageHeader title={matter.title} description={matter.matter_number} />

      <div className={cardClassName}>
        <DetailList
          items={[
            { label: "Matter number", value: matter.matter_number },
            { label: "Client", value: clientParty?.display_name ?? "Not recorded" },
            { label: "Matter type", value: nameOf(matterTypes, matter.matter_type_id) },
            { label: "Matter status", value: nameOf(matterStatuses, matter.matter_status_id) },
            { label: "Opened", value: formatDate(matter.opened_at) },
            { label: "Closed", value: formatDate(matter.closed_at) },
            { label: "Description", value: matter.description },
          ]}
        />
      </div>

      <section className="flex flex-col gap-3">
        <PageHeader
          title="Associated properties"
          description="Link an existing tenant-visible property to this matter."
        />

        <form className={`${cardClassName} ${formClassName}`} onSubmit={handleLinkProperty}>
          <SelectField
            label="Property"
            value={selectedPropertyId}
            onChange={setSelectedPropertyId}
            options={
              availableProperties.data?.items.map((property) => ({
                value: property.id,
                label: propertyLabel(property),
              })) ?? []
            }
            placeholder={
              availableProperties.isLoading ? "Loading properties…" : "Select a property…"
            }
            disabled={availableProperties.isLoading || isLinkingProperty}
            required
            hint="Only properties visible in your organization are available."
          />
          <ErrorMessage error={availableProperties.error} title="Could not load properties" />
          <ErrorMessage error={associationError} title="Could not link property" />
          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="submit"
              size="sm"
              disabled={
                !selectedPropertyId || isLinkingProperty || Boolean(availableProperties.error)
              }
            >
              {isLinkingProperty ? "Linking…" : "Link property"}
            </Button>
            {availableProperties.data?.pagination ? (
              <PaginationControls
                page={availableProperties.data.pagination.page}
                totalPages={availableProperties.data.pagination.total_pages}
                total={availableProperties.data.pagination.total}
                onPageChange={setPropertiesPage}
                isLoading={availableProperties.isLoading}
              />
            ) : null}
          </div>
        </form>

        <ErrorMessage
          error={associatedProperties.error}
          title="Could not load associated properties"
        />
        <ErrorMessage error={unlinkError} title="Could not unlink property" />
        {associatedProperties.isLoading ? (
          <LoadingSpinner label="Loading associated properties…" />
        ) : null}
        {associatedProperties.data ? (
          associatedProperties.data.length === 0 ? (
            <EmptyState
              title="No properties associated with this matter"
              description="Select an existing property above to create an association."
            />
          ) : (
            <table className={tableClassName}>
              <thead>
                <tr>
                  <th className={headerCellClassName}>Property</th>
                  <th className={headerCellClassName}>Registration number</th>
                  <th className={headerCellClassName}>Action</th>
                </tr>
              </thead>
              <tbody>
                {associatedProperties.data.map((property) => (
                  <tr key={property.id}>
                    <td className={`${cellClassName} font-medium text-foreground`}>
                      {propertyLabel(property)}
                    </td>
                    <td className={cellClassName}>
                      {property.registration_number ?? "Not recorded"}
                    </td>
                    <td className={cellClassName}>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        disabled={unlinkingPropertyId !== null}
                        onClick={() => void handleUnlinkProperty(property)}
                      >
                        {unlinkingPropertyId === property.id ? "Unlinking…" : "Unlink"}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        ) : null}
      </section>

      <section className="flex flex-col gap-3">
        <PageHeader
          title="Files"
          description="A file groups the documents of this matter. File numbers come from the backend."
        />

        <form
          className={`${cardClassName} ${formClassName}`}
          onSubmit={handleCreateFile}
          noValidate
        >
          <TextField
            label="New file title"
            value={fileTitle}
            onChange={(value) => {
              setFileTitle(value);
              setFileTitleError(null);
            }}
            hint="The backend assigns the file number when the file is created."
            error={fileTitleError}
            maxLength={MAX_FILE_TITLE_LENGTH}
            disabled={isCreatingFile}
          />
          <ErrorMessage error={fileError} title="Could not create the file" />
          <div>
            <Button type="submit" size="sm" disabled={isCreatingFile}>
              {isCreatingFile ? "Creating…" : "Create file"}
            </Button>
          </div>
        </form>

        <ErrorMessage error={files.error} title="Could not load files" />

        {files.isLoading ? <LoadingSpinner label="Loading files…" /> : null}

        {files.data ? (
          files.data.items.length === 0 ? (
            <EmptyState
              title="No files on this matter yet"
              description="Create the first file to start adding documents."
            />
          ) : (
            <>
              <table className={tableClassName}>
                <thead>
                  <tr>
                    <th className={headerCellClassName}>File number</th>
                    <th className={headerCellClassName}>Title</th>
                    <th className={headerCellClassName}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {files.data.items.map((file) => (
                    <tr key={file.id}>
                      <td className={`${cellClassName} font-medium text-foreground`}>
                        {file.file_number}
                      </td>
                      <td className={cellClassName}>{file.title}</td>
                      <td className={cellClassName}>
                        <Button asChild size="sm" variant="outline">
                          <Link to={`/matters/${matterId}/files/${file.id}`}>Open</Link>
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {files.data.pagination ? (
                <PaginationControls
                  page={files.data.pagination.page}
                  totalPages={files.data.pagination.total_pages}
                  total={files.data.pagination.total}
                  onPageChange={setFilesPage}
                  isLoading={files.isLoading}
                />
              ) : null}
            </>
          )
        ) : null}
      </section>
    </div>
  );
}
