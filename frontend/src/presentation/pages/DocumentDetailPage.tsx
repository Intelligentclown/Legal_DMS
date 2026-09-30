import { useRef, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { useNotifications } from "@/app/providers/NotificationProvider";
import { getLegalDocument } from "@/infrastructure/api/documentsApi";
import {
  createDocumentVersion,
  downloadDocumentVersion,
  getLatestDocumentVersion,
  listDocumentVersions,
} from "@/infrastructure/api/documentVersionsApi";
import { getMatterFile } from "@/infrastructure/api/filesApi";
import { listDocumentTypes } from "@/infrastructure/api/lookupsApi";
import { getMatter } from "@/infrastructure/api/mattersApi";
import type { LegalDocument } from "@/domain/types/document";
import type { DocumentVersion } from "@/domain/types/documentVersion";
import type { Matter } from "@/domain/types/matter";
import type { MatterFile } from "@/domain/types/matterFile";
import type { DocumentType } from "@/domain/types/lookup";
import {
  parseContentDispositionFilename,
  sanitizeFilename,
} from "@/shared/utils/contentDisposition";
import { downloadBlob } from "@/shared/utils/download";
import { Breadcrumbs } from "@/presentation/components/Breadcrumbs";
import { DetailList } from "@/presentation/components/DetailList";
import { EmptyState } from "@/presentation/components/EmptyState";
import { ErrorMessage } from "@/presentation/components/ErrorMessage";
import { LoadingSpinner } from "@/presentation/components/LoadingSpinner";
import { PageHeader } from "@/presentation/components/PageHeader";
import { TextField } from "@/presentation/components/form/Fields";
import {
  cardClassName,
  cellClassName,
  formClassName,
  headerCellClassName,
  inputClassName,
  tableClassName,
} from "@/presentation/components/form/styles";
import { Button } from "@/presentation/components/ui/button";
import { useAsyncResource } from "@/presentation/hooks/useAsyncResource";

const MAX_CHANGE_SUMMARY_LENGTH = 500;
const FALLBACK_CONTENT_TYPE = "application/octet-stream";

interface DocumentContext {
  doc: LegalDocument;
  file: MatterFile;
  matter: Matter;
  documentTypes: DocumentType[];
}

interface VersionContext {
  list: DocumentVersion[];
  latest: DocumentVersion | null;
}

function formatDateTime(value: string | null): string | null {
  if (!value) {
    return null;
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function newIdempotencyKey(): string {
  return crypto.randomUUID();
}

/**
 * Document read surface plus its immutable version history.
 *
 * Uploads go through the backend's existing raw-body contract: the chosen bytes
 * are the request body, the file name travels in `X-Filename`, a fresh
 * `Idempotency-Key` is minted per chosen file so a retried attempt is replayed
 * rather than duplicated, and version numbers are only ever displayed as the
 * backend reports them.
 */
export function DocumentDetailPage() {
  const { matterId, fileId, documentId } = useParams<{
    matterId: string;
    fileId: string;
    documentId: string;
  }>();
  const { notify } = useNotifications();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [idempotencyKey, setIdempotencyKey] = useState(newIdempotencyKey);
  const [changeSummary, setChangeSummary] = useState("");
  const [fileError, setFileError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<unknown>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [downloadError, setDownloadError] = useState<unknown>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const context = useAsyncResource<DocumentContext>(
    `document:${matterId}:${fileId}:${documentId}`,
    async () => {
      if (!matterId || !fileId || !documentId) {
        throw new Error("No document was selected.");
      }

      const [doc, file, matter, documentTypes] = await Promise.all([
        getLegalDocument(matterId, fileId, documentId),
        getMatterFile(matterId, fileId),
        getMatter(matterId),
        listDocumentTypes(),
      ]);

      return { doc, file, matter, documentTypes };
    },
  );

  const versions = useAsyncResource<VersionContext>(
    `versions:${matterId}:${fileId}:${documentId}`,
    async () => {
      if (!matterId || !fileId || !documentId) {
        return { list: [], latest: null };
      }

      const [list, latest] = await Promise.all([
        listDocumentVersions(matterId, fileId, documentId),
        getLatestDocumentVersion(matterId, fileId, documentId),
      ]);

      return { list, latest };
    },
  );

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedFile) {
      setFileError("Choose a file to upload.");
      return;
    }
    if (!matterId || !fileId || !documentId) {
      return;
    }

    // The backend interpolates X-Filename into its download header verbatim, so
    // control characters and path separators are stripped before it is sent.
    const filename = sanitizeFilename(selectedFile.name) || "document";

    setFileError(null);
    setIsUploading(true);
    setUploadError(null);
    try {
      const version = await createDocumentVersion(matterId, fileId, documentId, {
        content: await selectedFile.arrayBuffer(),
        filename,
        mimeType: selectedFile.type || FALLBACK_CONTENT_TYPE,
        idempotencyKey,
        changeSummary: changeSummary.trim() || undefined,
      });

      notify({
        variant: "success",
        title: "Version uploaded",
        description: `The backend recorded version ${version.version_number}.`,
      });
      setSelectedFile(null);
      setChangeSummary("");
      setIdempotencyKey(newIdempotencyKey());
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      versions.reload();
    } catch (error) {
      setUploadError(error);
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDownload(version: DocumentVersion) {
    if (!matterId || !fileId || !documentId) {
      return;
    }

    setDownloadingId(version.id);
    setDownloadError(null);
    try {
      const response = await downloadDocumentVersion(matterId, fileId, documentId, version.id);
      const filename =
        parseContentDispositionFilename(response.contentDisposition) ??
        `document-version-${version.version_number}`;

      downloadBlob(response.blob, filename);
      notify({ variant: "success", title: "Download started", description: filename });
    } catch (error) {
      setDownloadError(error);
    } finally {
      setDownloadingId(null);
    }
  }

  if (context.isLoading) {
    return (
      <div className="mx-auto flex max-w-4xl items-center justify-center py-12">
        <LoadingSpinner label="Loading document…" />
      </div>
    );
  }

  if (context.error || !context.data) {
    return (
      <div className="mx-auto flex max-w-4xl flex-col gap-4">
        <ErrorMessage error={context.error} title="Could not load the document" />
        <Button asChild variant="outline" size="sm" className="self-start">
          <Link to={`/matters/${matterId}/files/${fileId}`}>Back to file</Link>
        </Button>
      </div>
    );
  }

  const { doc, file, matter, documentTypes } = context.data;
  const typeName =
    documentTypes.find((documentType) => documentType.id === doc.document_type_id)?.name ??
    "Unknown";
  const versionData = versions.data;

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <Breadcrumbs
        items={[
          { label: "Matters", to: "/matters" },
          { label: matter.matter_number, to: `/matters/${matterId}` },
          { label: `File ${file.file_number}`, to: `/matters/${matterId}/files/${fileId}` },
          { label: doc.title },
        ]}
      />
      <PageHeader title={doc.title} description={`${typeName} · ${matter.matter_number}`} />

      <div className={cardClassName}>
        <DetailList
          items={[
            { label: "Title", value: doc.title },
            { label: "Document type", value: typeName },
            { label: "Status", value: doc.status },
            { label: "Latest version", value: versionData?.latest?.version_number ?? null },
          ]}
        />
      </div>

      <section className="flex flex-col gap-3">
        <PageHeader
          title="Upload a version"
          description="Bytes are sent raw with the file name in the X-Filename header. A fresh idempotency key is used for each chosen file, so retrying a failed upload does not create a second version."
        />

        <form className={`${cardClassName} ${formClassName}`} onSubmit={handleUpload} noValidate>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="version-file" className="text-sm font-medium text-foreground">
              Choose a file
            </label>
            <input
              id="version-file"
              ref={fileInputRef}
              type="file"
              disabled={isUploading}
              aria-invalid={fileError ? true : undefined}
              aria-describedby={fileError ? "version-file-error" : undefined}
              onChange={(event) => {
                setSelectedFile(event.target.files?.[0] ?? null);
                setFileError(null);
                setIdempotencyKey(newIdempotencyKey());
              }}
              className={inputClassName}
            />
            {fileError ? (
              <p id="version-file-error" className="text-xs text-destructive">
                {fileError}
              </p>
            ) : null}
          </div>

          <TextField
            label="Change summary"
            value={changeSummary}
            onChange={setChangeSummary}
            hint="Optional note recorded with this version."
            maxLength={MAX_CHANGE_SUMMARY_LENGTH}
            disabled={isUploading}
          />

          <ErrorMessage error={uploadError} title="Could not upload the version" />

          <div>
            <Button type="submit" size="sm" disabled={isUploading || !selectedFile}>
              {isUploading ? "Uploading…" : "Upload version"}
            </Button>
          </div>
        </form>
      </section>

      <section className="flex flex-col gap-3">
        <PageHeader
          title="Version history"
          description="Version numbers are allocated by the backend under a document lock. Downloading replays the stored bytes and the file name recorded at upload."
        />

        <ErrorMessage error={versions.error} title="Could not load version history" />
        <ErrorMessage error={downloadError} title="Could not download the version" />

        {versions.isLoading ? <LoadingSpinner label="Loading versions…" /> : null}

        {versionData ? (
          versionData.list.length === 0 ? (
            <EmptyState
              title="No versions uploaded yet"
              description="Upload the first version to start this document's history."
            />
          ) : (
            <table className={tableClassName}>
              <thead>
                <tr>
                  <th className={headerCellClassName}>Version</th>
                  <th className={headerCellClassName}>Change summary</th>
                  <th className={headerCellClassName}>Created</th>
                  <th className={headerCellClassName}>Action</th>
                </tr>
              </thead>
              <tbody>
                {versionData.list.map((version) => (
                  <tr key={version.id}>
                    <td className={`${cellClassName} font-medium text-foreground`}>
                      {version.version_number}
                      {versionData.latest?.id === version.id ? (
                        <span className="ml-2 text-xs text-muted-foreground">latest</span>
                      ) : null}
                    </td>
                    <td className={cellClassName}>{version.change_summary ?? "—"}</td>
                    <td className={cellClassName}>{formatDateTime(version.created_at) ?? "—"}</td>
                    <td className={cellClassName}>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        disabled={downloadingId === version.id}
                        onClick={() => void handleDownload(version)}
                      >
                        {downloadingId === version.id ? "Downloading…" : "Download"}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        ) : null}
      </section>
    </div>
  );
}
