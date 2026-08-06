"use client";

import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Badge, Card } from "@/components/ui/card";
import { ScoreRing, StatCard, StepPanel } from "@/components/wizard/step-panel";
import { WIZARD_STEPS, getStepIndex, type WizardStepId } from "@/config/wizard-steps";
import { api } from "@/lib/api";

type Stack = Record<string, unknown> | null;

const DEPLOY_STAGES = [
  "Building",
  "Installing dependencies",
  "Uploading artifacts",
  "Creating runtime",
  "Provisioning database",
  "Running readiness check",
  "Deployment complete",
];

export default function HomePage() {
  const [step, setStep] = useState<WizardStepId>("connect");
  const [demoMode, setDemoMode] = useState(true);
  const [repoUrl, setRepoUrl] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [deploymentId, setDeploymentId] = useState<string | null>(null);
  const [stack, setStack] = useState<Stack>(null);
  const [yaml, setYaml] = useState<{ zerops: string; import: string } | null>(null);
  const [plan, setPlan] = useState<Record<string, unknown> | null>(null);
  const [incidents, setIncidents] = useState<Record<string, unknown>[]>([]);
  const [score, setScore] = useState<Record<string, number> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deployStage, setDeployStage] = useState(0);
  const [maxReachedIndex, setMaxReachedIndex] = useState(0);

  useEffect(() => {
    setMaxReachedIndex((prev) => Math.max(prev, getStepIndex(step)));
  }, [step]);

  const goToStep = useCallback(
    (id: WizardStepId) => {
      if (getStepIndex(id) <= maxReachedIndex) setStep(id);
    },
    [maxReachedIndex],
  );

  const runAnalyze = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.analyze(demoMode ? null : repoUrl || null, demoMode);
      setSessionId(res.session_id);
      setStack(res.stack);
      setStep("analyze");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analyze failed");
    } finally {
      setLoading(false);
    }
  }, [demoMode, repoUrl]);

  const loadPlan = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      setPlan(await api.getPlan(sessionId));
      setStep("plan");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Plan failed");
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const loadYaml = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const data = await api.generateYaml(sessionId);
      setYaml({ zerops: data.zerops_yaml, import: data.import_yaml });
      setStep("configure");
    } catch (e) {
      setError(e instanceof Error ? e.message : "YAML generation failed");
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const runDeploy = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    setDeployStage(0);
    try {
      for (let i = 0; i < DEPLOY_STAGES.length - 1; i++) {
        setDeployStage(i);
        await new Promise((r) => setTimeout(r, 600));
      }
      const res = await api.deploy(sessionId, demoMode);
      setDeploymentId(res.deployment_id);
      setDeployStage(DEPLOY_STAGES.length - 1);
      setStep("deploy");
      if (demoMode) {
        setIncidents((await api.listIncidents(res.deployment_id)) as Record<string, unknown>[]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Deploy failed");
    } finally {
      setLoading(false);
    }
  }, [sessionId, demoMode]);

  const loadScore = useCallback(async () => {
    if (!deploymentId) return;
    setLoading(true);
    try {
      setScore(await api.getScore(deploymentId));
      setStep("score");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Score failed");
    } finally {
      setLoading(false);
    }
  }, [deploymentId]);

  const stackFields = stack
    ? [
        { label: "Framework", value: String(stack.framework ?? "—"), icon: "⚡" },
        { label: "Runtime", value: String(stack.runtime ?? "—"), icon: "🟢" },
        { label: "Database", value: String(stack.database ?? "—"), icon: "🗄️" },
        { label: "Cache", value: String(stack.cache ?? "None"), icon: "⚡" },
      ]
    : [];

  return (
    <AppShell
      view="wizard"
      step={step}
      maxReachedIndex={maxReachedIndex}
      demoMode={demoMode}
      onStepChange={goToStep}
      onDemoToggle={setDemoMode}
    >
      <div className="pointer-events-none absolute inset-0 grid-bg opacity-30" />
      <header className="relative border-b border-white/[0.06] bg-black/10 px-8 py-4 backdrop-blur-md">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-widest text-zinc-500">
                {WIZARD_STEPS.find((s) => s.id === step)?.description}
              </p>
            </div>
            <Badge tone={demoMode ? "accent" : "default"}>
              {demoMode ? "Demo active" : "Live repo"}
            </Badge>
          </div>
        </header>

        <div className="relative flex-1 overflow-y-auto p-8">
          <AnimatePresence mode="wait">
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="mb-6 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300"
              >
                {error}
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence mode="wait">
            {step === "connect" && (
              <StepPanel
                title="Connect your repository"
                subtitle="Paste a GitHub URL or use Demo Mode to explore the full platform engineering flow."
                badge="Platform Engineering"
              >
                <Card className="gradient-border max-w-2xl">
                  <div className="flex flex-col gap-4 sm:flex-row">
                    <input
                      className="flex-1 rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white placeholder:text-zinc-600 focus:border-indigo-500/50 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 disabled:opacity-40"
                      placeholder="https://github.com/org/repo"
                      value={repoUrl}
                      onChange={(e) => setRepoUrl(e.target.value)}
                      disabled={demoMode}
                    />
                    <Button onClick={runAnalyze} loading={loading} className="shrink-0">
                      Analyze Repository
                    </Button>
                  </div>
                  {demoMode && (
                    <p className="mt-4 text-xs text-zinc-500">
                      Demo Mode uses a sample Next.js + Prisma stack — no GitHub required.
                    </p>
                  )}
                </Card>
              </StepPanel>
            )}

            {step === "analyze" && stack && (
              <StepPanel
                title="Stack detected"
                subtitle="AI identified your application stack and infrastructure requirements."
                badge="Repository Intelligence"
              >
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  {stackFields.map((f, i) => (
                    <StatCard key={f.label} {...f} delay={i * 0.08} />
                  ))}
                </div>
                <div className="mt-6 flex gap-3">
                  <Button onClick={() => setStep("architecture")}>View Architecture</Button>
                </div>
              </StepPanel>
            )}

            {step === "architecture" && (
              <StepPanel
                title="Infrastructure architecture"
                subtitle="Proposed multi-service topology for Zerops private networking."
                badge="Architecture Builder"
              >
                <Card>
                  <div className="flex flex-wrap items-center justify-center gap-4 py-8">
                    {["Frontend", "API", "PostgreSQL", "Redis"].map((node, i) => (
                      <motion.div
                        key={node}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.1 }}
                        className="flex items-center gap-4"
                      >
                        <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/10 px-6 py-4 text-center shadow-glow-sm">
                          <p className="text-sm font-semibold text-white">{node}</p>
                          <p className="mt-1 text-[10px] text-zinc-500">
                            {i === 0 ? "Next.js" : i === 1 ? "Node / Python" : i === 2 ? "Postgres" : "Cache"}
                          </p>
                        </div>
                        {i < 3 && (
                          <motion.span
                            animate={{ opacity: [0.3, 1, 0.3] }}
                            transition={{ repeat: Infinity, duration: 2, delay: i * 0.2 }}
                            className="text-indigo-400"
                          >
                            →
                          </motion.span>
                        )}
                      </motion.div>
                    ))}
                  </div>
                </Card>
                <div className="mt-6">
                  <Button onClick={loadPlan} loading={loading}>
                    Deployment Plan
                  </Button>
                </div>
              </StepPanel>
            )}

            {step === "plan" && plan && (
              <StepPanel
                title="Deployment plan"
                subtitle="Estimated resources, cost, and build time before you deploy."
                badge="Deployment Planner"
              >
                <div className="grid gap-4 sm:grid-cols-3">
                  <StatCard
                    label="Est. monthly cost"
                    value={`$${plan.estimated_cost_usd_month ?? "—"}`}
                    icon="💰"
                  />
                  <StatCard
                    label="Build time"
                    value={`${plan.estimated_build_minutes ?? "—"} min`}
                    icon="⏱️"
                  />
                  <StatCard
                    label="Services"
                    value={String((plan.services as unknown[])?.length ?? 0)}
                    icon="📦"
                  />
                </div>
                <div className="mt-6">
                  <Button onClick={loadYaml} loading={loading}>
                    Generate Zerops Config
                  </Button>
                </div>
              </StepPanel>
            )}

            {step === "configure" && yaml && (
              <StepPanel
                title="Zerops configuration"
                subtitle="Import YAML + zerops.yaml generated from your repository analysis."
                badge="Zerops Native"
              >
                <div className="grid gap-4 lg:grid-cols-2">
                  <YamlPreview title="import.yaml" content={yaml.import} />
                  <YamlPreview title="zerops.yaml" content={yaml.zerops} />
                </div>
                <div className="mt-6">
                  <Button onClick={runDeploy} loading={loading}>
                    Deploy to Zerops
                  </Button>
                </div>
              </StepPanel>
            )}

            {step === "deploy" && (
              <StepPanel
                title="Deploying to Zerops"
                subtitle="Real-time pipeline status from build to readiness check."
                badge="Deployment Engine"
              >
                <Card>
                  <ul className="space-y-3">
                    {DEPLOY_STAGES.map((s, i) => (
                      <motion.li
                        key={s}
                        initial={{ opacity: 0, x: -8 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.05 }}
                        className="flex items-center gap-3"
                      >
                        <span
                          className={
                            i < deployStage
                              ? "text-emerald-400"
                              : i === deployStage
                                ? "text-indigo-400"
                                : "text-zinc-600"
                          }
                        >
                          {i < deployStage ? "✓" : i === deployStage ? "●" : "○"}
                        </span>
                        <span
                          className={
                            i <= deployStage ? "text-zinc-200" : "text-zinc-600"
                          }
                        >
                          {s}
                        </span>
                        {i === deployStage && loading && (
                          <span className="h-1 flex-1 overflow-hidden rounded-full bg-white/5">
                            <motion.span
                              className="block h-full w-1/3 rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 shimmer"
                              animate={{ x: ["-100%", "400%"] }}
                              transition={{ repeat: Infinity, duration: 1.5 }}
                            />
                          </span>
                        )}
                      </motion.li>
                    ))}
                  </ul>
                </Card>
                {!loading && (
                  <div className="mt-6">
                    <Button onClick={() => setStep("operate")}>Open Observability</Button>
                  </div>
                )}
              </StepPanel>
            )}

            {step === "operate" && (
              <StepPanel
                title="Observability"
                subtitle="Unified metrics, logs, and health — AIOps is watching."
                badge="Observability Layer"
              >
                <div className="grid gap-4 sm:grid-cols-3">
                  <StatCard label="CPU" value="12.5%" icon="📊" delay={0} />
                  <StatCard label="Memory" value="256 MB" icon="💾" delay={0.08} />
                  <StatCard label="Status" value="Healthy" icon="✅" delay={0.16} />
                </div>
                <div className="mt-6 flex items-center gap-3">
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
                  </span>
                  <span className="text-sm text-zinc-400">No incidents — monitoring active</span>
                </div>
                <div className="mt-6">
                  <Button onClick={() => setStep("incidents")}>View Incidents</Button>
                </div>
              </StepPanel>
            )}

            {step === "incidents" && (
              <StepPanel
                title="AIOps incidents"
                subtitle="Detect, diagnose, and remediate production failures."
                badge="AIOps Engine"
              >
                {incidents.length === 0 ? (
                  <Card className="text-center">
                    <p className="text-emerald-400">✓ No active incidents</p>
                    <p className="mt-2 text-sm text-zinc-500">
                      Run deploy in Demo Mode to simulate a failure scenario.
                    </p>
                  </Card>
                ) : (
                  incidents.map((inc, i) => (
                    <Card key={i} delay={i * 0.1} className="mb-4 border-red-500/20">
                      <div className="flex items-start justify-between">
                        <div>
                          <Badge tone="critical">Critical</Badge>
                          <h3 className="mt-2 font-semibold text-white">
                            {String(inc.title ?? "Incident")}
                          </h3>
                          {inc.diagnosis && typeof inc.diagnosis === "object" && (
                            <p className="mt-2 text-sm text-zinc-400">
                              {String((inc.diagnosis as Record<string, unknown>).root_cause ?? "")}
                            </p>
                          )}
                        </div>
                      </div>
                    </Card>
                  ))
                )}
                <div className="mt-6">
                  <Button onClick={loadScore} loading={loading}>
                    Deployment Score
                  </Button>
                </div>
              </StepPanel>
            )}

            {step === "score" && score && (
              <StepPanel
                title="Deployment score"
                subtitle="Production readiness across security, performance, and reliability."
                badge="Optimization Advisor"
              >
                <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-5">
                  {Object.entries(score).map(
                    ([k, v], i) =>
                      typeof v === "number" && (
                        <ScoreRing key={k} label={k} value={v} delay={i * 0.08} />
                      ),
                  )}
                </div>
              </StepPanel>
            )}
          </AnimatePresence>
        </div>
    </AppShell>
  );
}

function YamlPreview({ title, content }: { title: string; content: string }) {
  return (
    <Card>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-mono text-sm font-medium text-indigo-300">{title}</h3>
        <Badge tone="default">Generated</Badge>
      </div>
      <pre className="max-h-80 overflow-auto rounded-lg bg-black/40 p-4 font-mono text-xs leading-relaxed text-zinc-400">
        {content}
      </pre>
    </Card>
  );
}
