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
const accepted = ["pdf", "docx", "xlsx", "csv", "txt", "xlsm", "md", "markdown"]
function Submit() {
  const navigate = useNavigate()
  const input = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<File[]>([])
  const [title, setTitle] = useState("")
  const [error, setError] = useState("")
  const [dragging, setDragging] = useState(false)
  const create = useMutation({
    mutationFn: () =>
      auditApi.create(
        title.trim() || files[0]?.name || "Untitled audit",
        files,
      ),
    onSuccess: (audit) =>
      navigate({ to: "/submit/$auditId", params: { auditId: audit.id } }),
  })
  function addFiles(incoming: File[]) {
    const invalid = incoming.find(
      (file) =>
        !accepted.includes(file.name.split(".").pop()?.toLowerCase() ?? "") ||
        !file.size ||
        file.size > 50 * 1024 * 1024,
    )
    if (invalid) {
      setError(
        `${invalid.name}: choose a supported, non-empty file under 50 MB.`,
      )
      return
    }
    setError("")
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
              <strong>Drop files here, or browse</strong>
              <span>PDF, Word, Excel, CSV or text · up to 50 MB each</span>
            </button>
          </fieldset>
          {files.length > 0 && (
            <div className="file-blocks">
              {files.map((file, index) => (
                <div
                  className="file-block"
                  key={`${file.name}-${file.lastModified}`}
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
                      KB · Ready to upload
                    </span>
                  </div>
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
