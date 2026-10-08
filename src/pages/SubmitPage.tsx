import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { Audit } from '../api/types';
import { UploadDropzone } from '../components/submit/UploadDropzone';
import { SourceFileCard, UploadedSourceFile } from '../components/submit/SourceFileCard';
import { AuditProgressionModal } from '../components/submit/AuditProgressionModal';
import { Button } from '../components/ui/Button';
import { 
  ShieldCheck, 
  ArrowRight, 
  Sparkles,
  FileText
} from 'lucide-react';

export const SubmitPage: React.FC = () => {
  const navigate = useNavigate();

  // Stepper state
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3 | 4>(1);

  // Form State
  const [auditTitle, setAuditTitle] = useState('');
  const [documentType, setDocumentType] = useState<Audit['documentType']>('Procurement Contract');
  const [language, setLanguage] = useState('English (US / IN)');
  const [strictness, setStrictness] = useState<'STANDARD' | 'STRICT' | 'STATUTORY'>('STRICT');

  // Files
  const [aiDocument, setAiDocument] = useState<File | { name: string; size: string } | null>({
    name: 'AI_Procurement_Summary_v3.pdf',
    size: '2.4 MB',
  });
  const [sourceFiles, setSourceFiles] = useState<UploadedSourceFile[]>([
    {
      id: 'src-init-1',
      file: { name: 'Approved_Purchase_Order_PO_v2_Final.pdf', size: 1840000 },
      authority: 'LATEST_APPROVED',
    },
    {
      id: 'src-init-2',
      file: { name: 'Master_Execution_Schedule_Rev4.xlsx', size: 945000 },
      authority: 'SIGNED_EXECUTED',
    },
    {
      id: 'src-init-3',
      file: { name: 'Enterprise_Cloud_SLA_Terms_v1.2.pdf', size: 1200000 },
      authority: 'LATEST_APPROVED',
    },
  ]);

  // Loading & Execution
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [executingAuditId, setExecutingAuditId] = useState<string | null>(null);

  const handleAddSourceFiles = (newFiles: File[]) => {
    const formatted: UploadedSourceFile[] = newFiles.map((file, idx) => ({
      id: `src-${Date.now()}-${idx}`,
      file,
      authority: 'LATEST_APPROVED',
    }));
    setSourceFiles((prev) => [...prev, ...formatted]);
  };

  const handleRemoveSourceFile = (id: string) => {
    setSourceFiles((prev) => prev.filter((sf) => sf.id !== id));
  };

  const handleAuthorityChange = (id: string, authority: UploadedSourceFile['authority']) => {
    setSourceFiles((prev) =>
      prev.map((sf) => (sf.id === id ? { ...sf, authority } : sf))
    );
  };

  const handleStartAudit = async () => {
    if (!aiDocument) return;

    try {
      setIsSubmitting(true);
      const newAudit = await api.createAudit({
        title: auditTitle || aiDocument.name.replace(/\.[^/.]+$/, ''),
        documentType,
        language,
        aiFile: aiDocument,
        sourceFiles: sourceFiles.map((s) => ({
          name: s.file.name,
          size: typeof s.file.size === 'number' ? `${(s.file.size / (1024 * 1024)).toFixed(1)} MB` : s.file.size,
          authority: s.authority,
        })),
      });

      // Show progression modal
      setExecutingAuditId(newAudit.id);
    } catch (err) {
      console.error('Audit submission failed', err);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 sm:py-12">
      {/* 1. HERO SECTION */}
      <div className="text-center max-w-3xl mx-auto mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-950/70 border border-sky-800/60 text-xs text-tathya-accent font-medium mb-3">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Tathya Submit · Phase 1 Pipeline</span>
        </div>
        <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-white tracking-tight leading-tight">
          Verify AI-written business documents against the evidence that matters.
        </h1>
        <p className="mt-3 text-sm text-tathya-text-secondary max-w-2xl mx-auto leading-relaxed">
          Ground AI-generated contracts, procurement filings, and specifications against authoritative purchase orders, signed schedules, and corporate truth.
        </p>
      </div>

      {/* 2. PROGRESS STEPPER */}
      <div className="flex items-center justify-between max-w-2xl mx-auto mb-8 px-4">
        {[
          { step: 1, label: 'AI Document' },
          { step: 2, label: 'Source Truth' },
          { step: 3, label: 'Parameters' },
          { step: 4, label: 'Review & Run' },
        ].map((s) => (
          <div key={s.step} className="flex items-center gap-2">
            <button
              onClick={() => setCurrentStep(s.step as any)}
              className={`w-7 h-7 rounded-full text-xs font-bold flex items-center justify-center transition-all ${
                currentStep === s.step
                  ? 'bg-tathya-accent text-slate-950 ring-2 ring-tathya-accent/40'
                  : currentStep > s.step
                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-700'
                  : 'bg-slate-900 text-slate-500 border border-slate-800'
              }`}
            >
              {currentStep > s.step ? '✓' : s.step}
            </button>
            <span className={`text-xs hidden sm:inline font-medium ${currentStep === s.step ? 'text-white' : 'text-tathya-text-muted'}`}>
              {s.label}
            </span>
          </div>
        ))}
      </div>

      {/* 3. STEPPER FORM WORKFLOW */}
      <div className="bg-tathya-surface border border-tathya-surface-border rounded-2xl shadow-tathya-card p-6 sm:p-8">
        {/* STEP 1: Upload AI-Written Document */}
        {currentStep === 1 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="w-2 h-2 rounded-full bg-tathya-accent" />
                <h3 className="text-base font-bold text-white tracking-tight">
                  Step 1: Upload AI-Written Target Document
                </h3>
              </div>
              <p className="text-xs text-tathya-text-secondary">
                Select the AI synthesis, draft agreement, or summary to be audited for hallucinations and contradictions.
              </p>
            </div>

            <UploadDropzone
              label="Drop the AI-generated document here, or browse files"
              description="Upload the candidate document that requires fact grounding and verification."
              isAiDocument={true}
              selectedFile={aiDocument}
              onFileSelect={(file) => setAiDocument(file)}
              onFileRemove={() => setAiDocument(null)}
            />

            <div className="flex justify-end pt-4 border-t border-tathya-surface-border">
              <Button
                variant="primary"
                disabled={!aiDocument}
                rightIcon={<ArrowRight className="w-4 h-4" />}
                onClick={() => setCurrentStep(2)}
              >
                Continue to Ground Truth Sources
              </Button>
            </div>
          </div>
        )}

        {/* STEP 2: Add Source Documents (Ground Truth) */}
        {currentStep === 2 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <h3 className="text-base font-bold text-white tracking-tight">
                  Step 2: Add Ground-Truth Source Documents
                </h3>
              </div>
              <p className="text-xs text-tathya-text-secondary">
                Upload verified contracts, approved purchase orders, master schedules, or statutory standards to ground the audit.
              </p>
            </div>

            {/* List of active ground truth files */}
            {sourceFiles.length > 0 && (
              <div className="space-y-2.5">
                <div className="flex items-center justify-between text-xs text-tathya-text-muted px-1">
                  <span>Ground Truth Files ({sourceFiles.length})</span>
                  <span>Set Document Precedence / Authority</span>
                </div>
                {sourceFiles.map((sf) => (
                  <SourceFileCard
                    key={sf.id}
                    source={sf}
                    onRemove={handleRemoveSourceFile}
                    onAuthorityChange={handleAuthorityChange}
                  />
                ))}
              </div>
            )}

            {/* Dropzone for additional sources */}
            <UploadDropzone
              label="Add additional grounding source files"
              description="Drop approved purchase orders, SLA matrices, or signed schedules."
              multiple={true}
              onFileSelect={(file) => handleAddSourceFiles([file])}
              onMultipleFilesSelect={handleAddSourceFiles}
            />

            <div className="flex items-center justify-between pt-4 border-t border-tathya-surface-border">
              <Button variant="ghost" onClick={() => setCurrentStep(1)}>
                Back
              </Button>
              <Button
                variant="primary"
                disabled={sourceFiles.length === 0}
                rightIcon={<ArrowRight className="w-4 h-4" />}
                onClick={() => setCurrentStep(3)}
              >
                Set Audit Parameters
              </Button>
            </div>
          </div>
        )}

        {/* STEP 3: Form Parameters */}
        {currentStep === 3 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="w-2 h-2 rounded-full bg-amber-400" />
                <h3 className="text-base font-bold text-white tracking-tight">
                  Step 3: Audit Parameters & Policy Rules
                </h3>
              </div>
              <p className="text-xs text-tathya-text-secondary">
                Define the domain type and policy thresholds for materiality scoring.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-white mb-1.5">
                  Audit Title (Optional)
                </label>
                <input
                  type="text"
                  value={auditTitle}
                  onChange={(e) => setAuditTitle(e.target.value)}
                  placeholder="e.g. Enterprise Cloud Master Services Audit"
                  className="w-full bg-tathya-surface-elevated text-white text-xs px-3.5 py-2.5 rounded-lg border border-tathya-surface-border focus:ring-1 focus:ring-tathya-accent"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-white mb-1.5">
                  Document Domain / Type
                </label>
                <select
                  value={documentType}
                  onChange={(e) => setDocumentType(e.target.value as any)}
                  className="w-full bg-tathya-surface-elevated text-white text-xs px-3.5 py-2.5 rounded-lg border border-tathya-surface-border focus:ring-1 focus:ring-tathya-accent"
                >
                  <option value="Procurement Contract">Procurement Contract (Commercial & Milestones)</option>
                  <option value="Master Services Agreement">Master Services Agreement (Indemnity & SLAs)</option>
                  <option value="Financial Report">Financial Report (Ledgers & Disclosures)</option>
                  <option value="Technical Spec">Technical Spec (Architecture & Security)</option>
                  <option value="Compliance Filing">Compliance Filing (Statutory & Border Policy)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-white mb-1.5">
                  Primary Language & Locale
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full bg-tathya-surface-elevated text-white text-xs px-3.5 py-2.5 rounded-lg border border-tathya-surface-border focus:ring-1 focus:ring-tathya-accent"
                >
                  <option value="English (US / IN)">English (International / India Business)</option>
                  <option value="English (UK)">English (UK / Commonwealth Commercial)</option>
                  <option value="Hindi / English Bilingual">Hindi / English (Bilingual Compliance)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-white mb-1.5">
                  Verification Strictness
                </label>
                <select
                  value={strictness}
                  onChange={(e) => setStrictness(e.target.value as any)}
                  className="w-full bg-tathya-surface-elevated text-white text-xs px-3.5 py-2.5 rounded-lg border border-tathya-surface-border focus:ring-1 focus:ring-tathya-accent"
                >
                  <option value="STRICT">Strict (Zero-tolerance on commercial and date variance)</option>
                  <option value="STATUTORY">Statutory (Mandatory PII and legal compliance)</option>
                  <option value="STANDARD">Standard Enterprise (Tolerates minor label drift)</option>
                </select>
              </div>
            </div>

            <div className="flex items-center justify-between pt-4 border-t border-tathya-surface-border">
              <Button variant="ghost" onClick={() => setCurrentStep(2)}>
                Back
              </Button>
              <Button
                variant="primary"
                rightIcon={<ArrowRight className="w-4 h-4" />}
                onClick={() => setCurrentStep(4)}
              >
                Review Audit Inputs
              </Button>
            </div>
          </div>
        )}

        {/* STEP 4: Review Inputs & Start CTA */}
        {currentStep === 4 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <h3 className="text-base font-bold text-white tracking-tight">
                  Step 4: Confirm Inputs & Execute Audit
                </h3>
              </div>
              <p className="text-xs text-tathya-text-secondary">
                Verify the audit configuration before executing deterministic fact extraction.
              </p>
            </div>

            {/* Review Summary Card */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-tathya-surface-elevated border border-tathya-surface-border space-y-2">
                <span className="text-[10px] uppercase font-bold tracking-wider text-tathya-accent block">
                  Target AI Document
                </span>
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-tathya-accent" />
                  <span className="text-xs font-semibold text-white truncate">
                    {aiDocument?.name}
                  </span>
                </div>
                <div className="text-[11px] text-tathya-text-muted">
                  Domain: {documentType} · Locale: {language}
                </div>
              </div>

              <div className="p-4 rounded-xl bg-tathya-surface-elevated border border-tathya-surface-border space-y-2">
                <span className="text-[10px] uppercase font-bold tracking-wider text-emerald-400 block">
                  Ground Truth Anchors ({sourceFiles.length})
                </span>
                <div className="space-y-1">
                  {sourceFiles.map((sf) => (
                    <div key={sf.id} className="text-[11px] text-slate-300 truncate flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                      <span>{sf.file.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Execution CTA Banner */}
            <div className="p-4 rounded-xl bg-gradient-to-r from-sky-950/40 via-tathya-surface-elevated to-slate-900 border border-sky-800/40 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div>
                <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                  Ready to compute deterministic trust
                </h4>
                <p className="text-[11px] text-tathya-text-secondary mt-0.5">
                  Claims will be extracted and reconciled against ground truth evidence in seconds.
                </p>
              </div>

              <Button
                variant="primary"
                size="lg"
                isLoading={isSubmitting}
                rightIcon={<ShieldCheck className="w-5 h-5" />}
                onClick={handleStartAudit}
                className="w-full sm:w-auto"
              >
                Run Trust Audit
              </Button>
            </div>

            <div className="flex items-center justify-between pt-2">
              <Button variant="ghost" onClick={() => setCurrentStep(3)}>
                Back
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* 4. EXECUTION MODAL PROGRESSION */}
      {executingAuditId && (
        <AuditProgressionModal
          isOpen={true}
          auditId={executingAuditId}
          onComplete={() => {
            navigate(`/control/workspace/${executingAuditId}`);
          }}
        />
      )}
    </div>
  );
};
