import { useCallback, useRef, useState } from "react";

interface Props {
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
}

const ALLOWED_EXTENSIONS = [".pdf", ".eml"];

function isAcceptedFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext));
}

export default function UploadDropzone({ onFilesSelected, disabled }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (disabled) return;
      const acceptedFiles = Array.from(e.dataTransfer.files).filter(isAcceptedFile);
      if (acceptedFiles.length > 0) {
        onFilesSelected(acceptedFiles);
      }
    },
    [onFilesSelected, disabled],
  );

  const handleClick = () => {
    if (!disabled) inputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const acceptedFiles = Array.from(files).filter(isAcceptedFile);
      onFilesSelected(acceptedFiles);
    }
    e.target.value = "";
  };

  return (
    <div
      className={`dropzone ${dragOver ? "drag-over" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={handleClick}
      style={disabled ? { opacity: 0.5, cursor: "not-allowed" } : {}}
    >
      <h3>Drag and drop PDF/EML files here</h3>
      <p>or click to browse (multiple files supported)</p>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.eml"
        multiple
        onChange={handleFileChange}
        style={{ display: "none" }}
      />
    </div>
  );
}
