import { useMutation } from "@tanstack/react-query"
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import {
  ArrowRight,
  FileText,
  Plus,
  ShieldCheck,
  Upload,
  X,
} from "lucide-react"
import { useRef, useState } from "react"
import { auditApi } from "@/api/audits"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"

export const Route = createFileRoute("/_layout/submit")({
  component: Submit,
  head: () => ({ meta: [{ title: "New audit - Tathya" }] }),
})
const accepted = ["pdf", "docx", "xlsx", "csv", "txt", "xlsm", "md", "markdown", "png", "jpg", "jpeg", "tiff", "bmp", "webp"]
function Submit() {
  const navigate = useNavigate()
  const input = useRef<HTMLInputElement>(null)
  const uploadController = useRef<AbortController | null>(null)
  const [progress, setProgress] = useState(0)
  const [files, setFiles] = useState<File[]>([])
  const [title, setTitle] = useState("")
  const [error, setError] = useState("")
  const [dragging, setDragging] = useState(false)
  const create = useMutation({
    mutationFn: () => {
      uploadController.current = new AbortController()
      setProgress(0)
      return auditApi.create(
        title.trim() || files[0]?.name || "Untitled audit",
        files,
        uploadController.current.signal,
        setProgress,
      )
    },
    onSuccess: (audit) =>
      navigate({ to: "/submit/$auditId", params: { auditId: audit.id } }),
  })
  function addFiles(incoming: File[]) {
    create.reset()
    const valid = incoming.filter(file => accepted.includes(file.name.split(".").pop()?.toLowerCase() ?? "") && file.size > 0 && file.size <= 50 * 1024 * 1024)
    const rejected = incoming.filter(file => !valid.includes(file))
    setError(rejected.length ? `${rejected.map(f => f.name).join(", ")}: choose a supported, non-empty file at most 50 MB.` : "")
    incoming = valid
    setFiles((previous) => {
      const next = [...previous]
      for (const file of incoming) {
        if (
          !next.some(
            (existing) =>
              existing.name === file.name &&
              existing.size === file.size &&
              existing.lastModified === file.lastModified,
          )
        )
          next.push(file)
      }
      if (next.length > 20 || next.reduce((total, file) => total + file.size, 0) > 100 * 1024 * 1024) {
        setError("Use at most 20 files and 100 MB per audit.")
        return previous
      }
      return next
    })
  }
  return (
    <div className="product-page submit-page">
      <div className="product-heading">
        <div>
          <span className="eyebrow">TATHYA SUBMIT</span>
          <h1>Start with your documents.</h1>
          <p>A considered check, before the next important decision.</p>
        </div>
        <span className="quiet-label">
          <ShieldCheck size={14} /> Evidence-led verification
        </span>
      </div>
      <div className="submit-layout">
        <form
          className="product-panel submit-form"
          onSubmit={(event) => {
            event.preventDefault()
            if (files.length && !create.isPending) create.mutate()
          }}
        >
          <div className="panel-heading">
            <span className="step-number">01</span>
            <div>
              <h2>Prepare your audit</h2>
              <p>Give this document set a name you’ll recognise.</p>
            </div>
          </div>
          <label htmlFor="audit-title" className="field-label">
            Audit name{" "}
            <span className="text-muted-foreground font-normal">
              · optional
            </span>
          </label>
          <Input
            id="audit-title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="e.g. Cloud services agreement · FY 2026–27"
            maxLength={250}
          />
          <div className="panel-heading mt-8">
            <span className="step-number">02</span>
            <div>
              <h2>Add documents</h2>
              <p>Bring the draft and supporting material together.</p>
            </div>
            <button
              type="button"
              className="upload-add"
              aria-label="Add files"
              onClick={() => input.current?.click()}
              disabled={create.isPending}
            >
              <Plus size={17} />
            </button>
          </div>
          <input
            ref={input}
            type="file"
            aria-label="Upload documents"
            className="sr-only"
            accept={accepted.map((ext) => `.${ext}`).join(",")}
            multiple
            disabled={create.isPending}
            onChange={(event) => {
              addFiles(Array.from(event.target.files ?? []))
              event.target.value = ""
            }}
          />
          <fieldset
            aria-label="Document upload area"
            className={`file-drop ${dragging ? "dragging" : ""}`}
            onDragOver={(event) => {
              event.preventDefault()
              if (!create.isPending) setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault()
              setDragging(false)
              if (!create.isPending)
                addFiles(Array.from(event.dataTransfer.files))
            }}
          >
            <button
              type="button"
              className="file-drop-button"
              onClick={() => input.current?.click()}
              disabled={create.isPending}
            >
              <span className="upload-symbol">
                <Upload size={21} />
              </span>
              <strong>Add the AI document and its source files</strong>
              <span>PDF, Word, Excel, CSV, text or images · up to 50 MB each</span>
            </button>
          </fieldset>
          {files.length === 1 && <p role="status">Add separate source files to verify factual claims. With only the AI document, no trust rating can be established.</p>}
          {files.length > 0 && (
            <div className="file-blocks">
              {files.map((file, index) => (
                <div
                  className="file-block"
                  key={`${file.name}-${file.size}-${file.lastModified}`}
                >
                  <FileText size={18} />
                  <div>
                    <strong>{file.name}</strong>
                    <span>
                      {file.size < 1024
                        ? "<1"
                        : new Intl.NumberFormat("en-IN", {
                            maximumFractionDigits: 1,
                          }).format(file.size / 1024)}{" "}
                      KB · {index === 0 ? "AI document to check" : "Source evidence"}
                    </span>
                  </div>
                  {index > 0 && <button type="button" disabled={create.isPending} onClick={() => setFiles([file, ...files.filter((_, i) => i !== index)])}>Use as AI document</button>}
                  <button
                    type="button"
                    aria-label={`Remove ${file.name}`}
                    disabled={create.isPending}
                    onClick={() =>
                      setFiles(files.filter((_, i) => i !== index))
                    }
                  >
                    <X size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}
          {(error || create.error) && (
            <p className="form-error" role="alert">
              {error || create.error?.message}
            </p>
          )}
          {create.isPending && <div role="status" aria-live="polite"><progress max={100} value={progress} aria-label="Upload progress" /><p>{progress < 100 ? `Uploading documents: ${progress}%` : "Upload received. Reading your documents…"}</p><button type="button" className="back-link" onClick={() => uploadController.current?.abort()}>Cancel upload</button></div>}
          <div className="submit-footer">
            <p>
              {files.length
                ? `${files.length} document${files.length === 1 ? "" : "s"} selected`
                : "Add at least one document to continue."}
            </p>
            <LoadingButton
              type="submit"
              disabled={!files.length}
              loading={create.isPending}
            >
              Start verification <ArrowRight size={15} />
            </LoadingButton>
          </div>
        </form>
        <aside className="submit-guide">
          <span className="eyebrow">A LITTLE PREPARATION HELPS</span>
          <h2>
            Better evidence.
            <br />
            Clearer answers.
          </h2>
          <p>
            Add the latest approved versions of the documents you want reviewed.
          </p>
          <div className="guide-line">
            <span>1</span>
            <div>
              <strong>Bring the source material</strong>
              <p>Contracts, schedules and supporting records.</p>
            </div>
          </div>
          <div className="guide-line">
            <span>2</span>
            <div>
              <strong>Let the check run</strong>
              <p>We’ll keep you updated as your audit processes.</p>
            </div>
          </div>
          <div className="guide-line">
            <span>3</span>
            <div>
              <strong>Get one clear result</strong>
              <p>Score, findings and next steps in a single view.</p>
            </div>
          </div>
          <Link
            to="/control"
            className="text-sm text-primary inline-flex gap-2 items-center"
          >
            View existing audits <ArrowRight size={14} />
          </Link>
        </aside>
      </div>
    </div>
  )
}
