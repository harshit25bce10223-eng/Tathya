import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, AlertCircle, X } from 'lucide-react';

interface UploadDropzoneProps {
  label: string;
  description: string;
  acceptText?: string;
  isAiDocument?: boolean;
  selectedFile?: File | { name: string; size: string | number } | null;
  onFileSelect: (file: File) => void;
  onFileRemove?: () => void;
  multiple?: boolean;
  onMultipleFilesSelect?: (files: File[]) => void;
}

export const UploadDropzone: React.FC<UploadDropzoneProps> = ({
  label,
  description,
  acceptText = 'Supports PDF, DOCX, XLSX, TXT up to 50MB',
  isAiDocument = false,
  selectedFile,
  onFileSelect,
  onFileRemove,
  multiple = false,
  onMultipleFilesSelect,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    setErrorMessage(null);

    const files = Array.from(e.dataTransfer.files);
    if (!files.length) return;

    if (multiple && onMultipleFilesSelect) {
      onMultipleFilesSelect(files);
    } else {
      const file = files[0];
      if (validateFile(file)) {
        onFileSelect(file);
      }
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setErrorMessage(null);
    if (!e.target.files || e.target.files.length === 0) return;

    const files = Array.from(e.target.files);
    if (multiple && onMultipleFilesSelect) {
      onMultipleFilesSelect(files);
    } else {
      const file = files[0];
      if (validateFile(file)) {
        onFileSelect(file);
      }
    }
  };

  const validateFile = (file: File) => {
    const validExtensions = ['.pdf', '.docx', '.xlsx', '.xls', '.txt'];
    const name = file.name.toLowerCase();
    const isValidExt = validExtensions.some((ext) => name.endsWith(ext));

    if (!isValidExt) {
      setErrorMessage('Unsupported file format. Please upload PDF, DOCX, XLSX, or TXT.');
      return false;
    }
    if (file.size > 50 * 1024 * 1024) {
      setErrorMessage('File size exceeds the 50MB limit.');
      return false;
    }
    return true;
  };

  const formatFileSize = (size: string | number) => {
    if (typeof size === 'string') return size;
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  };

  // If a single file is already selected for AI Document, show a clean, compact document card
  if (selectedFile && !multiple) {
    return (
      <div className={`p-4 rounded-xl border transition-all ${
        isAiDocument 
          ? 'bg-tathya-surface-elevated border-tathya-accent/50 shadow-tathya-card' 
          : 'bg-tathya-surface border-tathya-surface-border'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded-lg border ${
              isAiDocument 
                ? 'bg-amber-950/70 border-amber-600/60 text-tathya-accent' 
                : 'bg-slate-900 border-slate-700 text-slate-300'
            }`}>
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-white tracking-tight">
                  {selectedFile.name}
                </span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
                  Ready
                </span>
              </div>
              <p className="text-xs text-tathya-text-muted mt-0.5">
                {formatFileSize(selectedFile.size)} · SHA-256 Calculated · Verification Target
              </p>
            </div>
          </div>

          {onFileRemove && (
            <button
              onClick={onFileRemove}
              className="p-1.5 rounded-md text-tathya-text-muted hover:text-white hover:bg-tathya-surface-hover transition-colors"
              title="Change document"
              aria-label="Remove document"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="w-full">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`relative flex flex-col items-center justify-center p-6 sm:p-8 rounded-xl border-2 border-dashed cursor-pointer transition-all duration-150 text-center ${
          isDragging
            ? 'border-tathya-accent bg-tathya-accent/5 ring-4 ring-tathya-accent/10'
            : isAiDocument
            ? 'border-tathya-accent/40 bg-tathya-surface-elevated/70 hover:border-tathya-accent hover:bg-tathya-surface-elevated'
            : 'border-tathya-surface-border bg-tathya-surface/60 hover:border-slate-500 hover:bg-tathya-surface'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          multiple={multiple}
          onChange={handleInputChange}
          className="hidden"
          accept=".pdf,.docx,.xlsx,.xls,.txt"
        />

        <div className={`p-3 rounded-full mb-3 border ${
          isAiDocument 
            ? 'bg-amber-950/80 border-amber-800/60 text-tathya-accent' 
            : 'bg-slate-900 border-slate-700 text-slate-400'
        }`}>
          <UploadCloud className="w-6 h-6" />
        </div>

        <h4 className="text-sm font-semibold text-white mb-1">
          {label}
        </h4>
        <p className="text-xs text-tathya-text-secondary max-w-sm mb-2">
          {description}
        </p>
        <span className="text-[11px] font-mono text-tathya-text-muted">
          {acceptText}
        </span>
      </div>

      {errorMessage && (
        <div className="mt-2.5 flex items-center gap-2 p-2.5 rounded-md bg-red-950/60 border border-red-800/60 text-xs text-red-300">
          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}
    </div>
  );
};
