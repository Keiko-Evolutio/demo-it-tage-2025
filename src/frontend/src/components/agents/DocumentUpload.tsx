import { useState } from "react";
import {
  Card,
  CardHeader,
  Text,
  Spinner,
  makeStyles,
  tokens,
  Body1,
  Caption1,
} from "@fluentui/react-components";
import {
  ArrowUploadRegular,
  DocumentRegular,
  CheckmarkCircleRegular,
  DismissCircleRegular,
} from "@fluentui/react-icons";

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalM,
    padding: tokens.spacingVerticalL,
  },
  uploadArea: {
    border: `2px dashed ${tokens.colorNeutralStroke1}`,
    borderRadius: tokens.borderRadiusMedium,
    padding: tokens.spacingVerticalXXL,
    textAlign: "center" as const,
    cursor: "pointer",
    transition: "all 0.2s ease",
    "&:hover": {
      borderColor: tokens.colorBrandStroke1,
      backgroundColor: tokens.colorNeutralBackground1Hover,
    },
  },
  uploadAreaActive: {
    borderColor: tokens.colorBrandStroke1,
    backgroundColor: tokens.colorNeutralBackground1Selected,
  },
  fileInput: {
    display: "none",
  },
  uploadIcon: {
    fontSize: "48px",
    color: tokens.colorBrandForeground1,
    marginBottom: tokens.spacingVerticalM,
  },
  documentList: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
  },
  documentCard: {
    padding: tokens.spacingVerticalM,
  },
  documentInfo: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalM,
  },
  statusIcon: {
    fontSize: "20px",
  },
  successIcon: {
    color: tokens.colorPaletteGreenForeground1,
  },
  errorIcon: {
    color: tokens.colorPaletteRedForeground1,
  },
  uploadingIcon: {
    color: tokens.colorBrandForeground1,
  },
});

interface UploadedDocument {
  filename: string;
  status: "uploading" | "success" | "error";
  message?: string;
  chunksCount?: number;
}

interface DocumentUploadProps {
  onUploadComplete?: () => void;
}

export function DocumentUpload({ onUploadComplete }: DocumentUploadProps) {
  const styles = useStyles();
  const [isDragging, setIsDragging] = useState(false);
  const [documents, setDocuments] = useState<UploadedDocument[]>([]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      handleFiles(files);
    }
  };

  const handleFiles = async (files: File[]) => {
    for (const file of files) {
      await uploadFile(file);
    }
  };

  const uploadFile = async (file: File) => {
    // Add document to list with uploading status
    const newDoc: UploadedDocument = {
      filename: file.name,
      status: "uploading",
    };
    setDocuments((prev) => [...prev, newDoc]);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("/upload", {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (response.ok) {
        // Update document status to success
        setDocuments((prev) =>
          prev.map((doc) =>
            doc.filename === file.name
              ? {
                  ...doc,
                  status: "success",
                  message: result.message,
                  chunksCount: result.chunks_count,
                }
              : doc
          )
        );
        onUploadComplete?.();
      } else {
        // Update document status to error
        setDocuments((prev) =>
          prev.map((doc) =>
            doc.filename === file.name
              ? {
                  ...doc,
                  status: "error",
                  message: result.error || "Upload failed",
                }
              : doc
          )
        );
      }
    } catch (error) {
      // Update document status to error
      setDocuments((prev) =>
        prev.map((doc) =>
          doc.filename === file.name
            ? {
                ...doc,
                status: "error",
                message: "Network error",
              }
            : doc
        )
      );
    }
  };

  const getStatusIcon = (status: UploadedDocument["status"]) => {
    switch (status) {
      case "uploading":
        return <Spinner size="small" className={styles.uploadingIcon} />;
      case "success":
        return <CheckmarkCircleRegular className={`${styles.statusIcon} ${styles.successIcon}`} />;
      case "error":
        return <DismissCircleRegular className={`${styles.statusIcon} ${styles.errorIcon}`} />;
    }
  };

  return (
    <div className={styles.container}>
      <div
        className={`${styles.uploadArea} ${isDragging ? styles.uploadAreaActive : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => document.getElementById("fileInput")?.click()}
      >
        <ArrowUploadRegular className={styles.uploadIcon} />
        <Body1>
          <strong>Click to upload</strong> or drag and drop
        </Body1>
        <Caption1>Supported formats: PDF, DOCX, TXT, MD</Caption1>
        <input
          id="fileInput"
          type="file"
          className={styles.fileInput}
          onChange={handleFileSelect}
          accept=".pdf,.docx,.txt,.md"
          multiple
        />
      </div>

      {documents.length > 0 && (
        <div className={styles.documentList}>
          <Text weight="semibold">Uploaded Documents</Text>
          {documents.map((doc, index) => (
            <Card key={index} className={styles.documentCard}>
              <CardHeader
                image={<DocumentRegular />}
                header={<Text weight="semibold">{doc.filename}</Text>}
                description={
                  <div>
                    {doc.status === "success" && doc.chunksCount && (
                      <Caption1>
                        Successfully indexed {doc.chunksCount} chunks
                      </Caption1>
                    )}
                    {doc.status === "error" && (
                      <Caption1 style={{ color: tokens.colorPaletteRedForeground1 }}>
                        {doc.message}
                      </Caption1>
                    )}
                    {doc.status === "uploading" && (
                      <Caption1>Processing...</Caption1>
                    )}
                  </div>
                }
                action={getStatusIcon(doc.status)}
              />
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

