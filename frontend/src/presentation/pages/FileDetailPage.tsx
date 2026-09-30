import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { useNotifications } from "@/app/providers/NotificationProvider";
import { createLegalDocument, listLegalDocuments } from "@/infrastructure/api/documentsApi";
import { getMatterFile } from "@/infrastructure/api/filesApi";
import { listDocumentTypes } from "@/infrastructure/api/lookupsApi";
import { getMatter } from "@/infrastructure/api/mattersApi";
import type { Matter } from "@/domain/types/matter";
import type { MatterFile } from "@/domain/types/matterFile";
import type { DocumentType } from "@/domain/types/lookup";
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

const MAX_DOCUMENT_TITLE_LENGTH = 255;

interface FileContext {
  file: MatterFile;
  matter: Matter;
  documentTypes: DocumentType[];
}

interface DocumentForm {
  title: string;
  documentTypeId: string;
}

const INITIAL_FORM: DocumentForm = { title: "", documentTypeId: "" };

/**
 * File read surface: the file's own record plus the documents it groups. Only
 * documents reachable through this file appear; the backend does not expose an
 * unfiled-document route, so none are listed or invented here.
 */
export function FileDetailPage() {
  const { matterId, fileId } = useParams<{ matterId: string; fileId: string }>();
  const { notify } = useNotifications();

  const [documentsPage, setDocumentsPage] = useState(1);
  const [form, setForm] = useState<DocumentForm>(INITIAL_FORM);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [createError, setCreateError] = useState<unknown>(null);
  const [isCreating, setIsCreating] = useState(false);

  const context = useAsyncResource<FileContext>(`file:${matterId}:${fileId}`, async () => {
    if (!matterId || !fileId) {
      throw new Error("No file was selected.");
    }

    const [file, matter, documentTypes] = await Promise.all([
      getMatterFile(matterId, fileId),
      getMatter(matterId),
      listDocumentTypes(),
    ]);

    return { file, matter, documentTypes };
  });

  const documents = useAsyncResource(`documents:${matterId}:${fileId}:${documentsPage}`, () => {
    if (!matterId || !fileId) {
      return Promise.resolve({ items: [], pagination: null });
    }
    return listLegalDocuments(matterId, fileId, { page: documentsPage });
  });

  async function handleCreateDocument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const validationErrors: Record<string, string> = {};
    if (!form.title.trim()) {
      validationErrors.title = "Document title is required.";
    }
    if (!form.documentTypeId) {
      validationErrors.documentTypeId = "Choose a document type.";
    }
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0 || !matterId || !fileId) {
      return;
    }

    setIsCreating(true);
    setCreateError(null);
    try {
      const created = await createLegalDocument(matterId, fileId, {
        title: form.title.trim(),
        document_type_id: form.documentTypeId,
      });
      notify({
        variant: "success",
        title: "Document created",
        description: `“${created.title}” is ready for its first version.`,
      });
      setForm(INITIAL_FORM);
      setDocumentsPage(1);
      documents.reload();
    } catch (error) {
      setCreateError(error);
    } finally {
      setIsCreating(false);
    }
  }

  if (context.isLoading) {
    return (
      <div className="mx-auto flex max-w-4xl items-center justify-center py-12">
        <LoadingSpinner label="Loading file…" />
      </div>
    );
  }

  if (context.error || !context.data) {
    return (
      <div className="mx-auto flex max-w-4xl flex-col gap-4">
        <ErrorMessage error={context.error} title="Could not load the file" />
        <Button asChild variant="outline" size="sm" className="self-start">
          <Link to={`/matters/${matterId}`}>Back to matter</Link>
        </Button>
      </div>
    );
  }

  const { file, matter, documentTypes } = context.data;
  const typeOptions = documentTypes
    .filter((documentType) => documentType.is_active)
    .map((documentType) => ({
      value: documentType.id,
      label: `${documentType.name} (${documentType.code})`,
    }));

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <Breadcrumbs
        items={[
          { label: "Matters", to: "/matters" },
          { label: matter.matter_number, to: `/matters/${matterId}` },
          { label: `File ${file.file_number}` },
        ]}
      />
      <PageHeader title={file.title} description={`File number ${file.file_number}`} />

      <div className={cardClassName}>
        <DetailList
          items={[
            { label: "File number", value: file.file_number },
            { label: "Title", value: file.title },
            { label: "Matter", value: matter.matter_number },
          ]}
        />
      </div>

      <section className="flex flex-col gap-3">
        <PageHeader
          title="Documents"
          description="Documents are always created inside a file. A new document starts with the backend's default status."
        />

        <form
          className={`${cardClassName} ${formClassName}`}
          onSubmit={handleCreateDocument}
          noValidate
        >
          <TextField
            label="New document title"
            value={form.title}
            onChange={(value) => setForm((current) => ({ ...current, title: value }))}
            error={errors.title}
            maxLength={MAX_DOCUMENT_TITLE_LENGTH}
            disabled={isCreating}
          />
          <SelectField
            label="Document type"
            value={form.documentTypeId}
            onChange={(value) => setForm((current) => ({ ...current, documentTypeId: value }))}
            options={typeOptions}
            placeholder="Choose a type…"
            error={errors.documentTypeId}
            disabled={isCreating}
          />
          <ErrorMessage error={createError} title="Could not create the document" />
          <div>
            <Button type="submit" size="sm" disabled={isCreating}>
              {isCreating ? "Creating…" : "Create document"}
            </Button>
          </div>
        </form>

        <ErrorMessage error={documents.error} title="Could not load documents" />

        {documents.isLoading ? <LoadingSpinner label="Loading documents…" /> : null}

        {documents.data ? (
          documents.data.items.length === 0 ? (
            <EmptyState
              title="No documents in this file yet"
              description="Create the first document, then upload its first version."
            />
          ) : (
            <>
              <table className={tableClassName}>
                <thead>
                  <tr>
                    <th className={headerCellClassName}>Title</th>
                    <th className={headerCellClassName}>Status</th>
                    <th className={headerCellClassName}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.data.items.map((doc) => (
                    <tr key={doc.id}>
                      <td className={`${cellClassName} font-medium text-foreground`}>
                        {doc.title}
                      </td>
                      <td className={cellClassName}>{doc.status}</td>
                      <td className={cellClassName}>
                        <Button asChild size="sm" variant="outline">
                          <Link to={`/matters/${matterId}/files/${fileId}/documents/${doc.id}`}>
                            Open
                          </Link>
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {documents.data.pagination ? (
                <PaginationControls
                  page={documents.data.pagination.page}
                  totalPages={documents.data.pagination.total_pages}
                  total={documents.data.pagination.total}
                  onPageChange={setDocumentsPage}
                  isLoading={documents.isLoading}
                />
              ) : null}
            </>
          )
        ) : null}
      </section>
    </div>
  );
}
