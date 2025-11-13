import React, { useState, useRef } from "react";
import { startAnalysis, refine, approve } from "../lib/requirements";
import { startAudioChat } from "../lib/audio";

/**
 * Componente principal de interação.
 * Usa as funções do seu /src/lib para integrar com o backend.
 */

export default function AnalysisForm() {
  const [userInput, setUserInput] = useState("");
  const [analysis, setAnalysis] = useState("");
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("START");
  const [error, setError] = useState("");

  const fileInputRef = useRef(null);

  const handleStartAnalysis = async () => {
    if (!userInput.trim()) return;
    setLoading(true);
    setError("");

    try {
      const data = await startAnalysis(userInput);
      const text = data?.analysis ?? data?.generated_requirements ?? JSON.stringify(data);
      setAnalysis(text);
      setHistory([{ role: "user", content: userInput }, { role: "assistant", content: text }]);
      setStatus("REFINING");
    } catch (err) {
      console.error(err);
      setError("Erro ao iniciar análise. Verifique a API.");
    } finally {
      setLoading(false);
    }
  };

  const handleRefine = async (instruction) => {
    if (!instruction.trim()) return;
    setLoading(true);
    setError("");

    try {
      const data = await refine(instruction, history);
      const text = data?.analysis ?? data?.refined_requirements ?? JSON.stringify(data);
      setAnalysis(text);
      setHistory((prev) => [...prev, { role: "user", content: instruction }, { role: "assistant", content: text }]);
    } catch (err) {
      console.error(err);
      setError("Erro ao refinar requisitos.");
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!analysis) return;
    setLoading(true);
    setError("");
    try {
      await approve(analysis, history?.[0]?.content ?? "");
      setStatus("APPROVED");
    } catch (err) {
      console.error(err);
      setError("Erro ao aprovar requisitos.");
    } finally {
      setLoading(false);
    }
  };

  const handleAudioUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", file);
      const data = await startAudioChat(formData);
      const text = data?.analysis ?? data?.llm_response ?? data?.transcript ?? JSON.stringify(data);
      setAnalysis(text);
      setHistory([{ role: "user", content: "(Áudio enviado)" }, { role: "assistant", content: text }]);
      setStatus("REFINING");
    } catch (err) {
      console.error(err);
      setError("Erro ao processar áudio.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section id="analyze" className="mt-8">
      <div className="max-w-3xl mx-auto bg-white rounded-2xl shadow-lg p-6">
        <div className="flex items-start gap-4">
          <div className="flex-1">
            <label className="text-sm font-medium text-slate-600">Digite ou cole a ata / solicitação</label>
            <textarea
              rows={4}
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              placeholder="Descreva o que foi discutido na reunião, requisitos desejados, funcionalidades..."
              className="mt-2 w-full border rounded-lg p-4 focus:outline-none focus:ring-2 focus:ring-uece-mid"
            />
            <div className="mt-3 flex items-center gap-3">
              <button
                onClick={handleStartAnalysis}
                disabled={loading}
                className="px-5 py-2 rounded-lg bg-uece-deep text-white font-semibold shadow hover:opacity-95 disabled:opacity-50"
              >
                {loading ? "Analisando..." : "Iniciar Análise"}
              </button>

              <label className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-uece-mid/10 border border-uece-mid text-uece-mid cursor-pointer">
                🎤 Enviar Áudio
                <input ref={fileInputRef} type="file" accept="audio/*" className="hidden" onChange={handleAudioUpload} />
              </label>

              <button
                onClick={() => { setUserInput(""); setAnalysis(""); setHistory([]); setStatus("START"); setError(""); }}
                className="px-4 py-2 rounded-lg bg-slate-100 text-slate-700 border hover:bg-slate-50"
              >
                Limpar
              </button>
            </div>
          </div>

          <aside className="w-80 hidden md:block">
            <div className="bg-uece-deep/5 border border-uece-deep/10 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-uece-deep">Dica rápida</h4>
              <p className="mt-2 text-sm text-slate-600">Explique o contexto, papéis (cliente/tech), prioridades e restrições.</p>
            </div>
          </aside>
        </div>

        {/* Result / Analysis */}
        <div className="mt-6">
          <div className="text-sm text-slate-500">Resultado</div>
          <div className="mt-2 min-h-[120px] p-4 bg-slate-50 border rounded-lg whitespace-pre-wrap text-slate-800">
            {analysis || <span className="text-slate-400">Nenhum resultado ainda — envie uma solicitação ou áudio.</span>}
          </div>

          {error && <div className="mt-3 p-3 bg-red-50 text-red-700 rounded-md">{error}</div>}

          {status === "REFINING" && (
            <div className="mt-4 flex gap-2 items-center">
              <input
                placeholder="Instrua um refinamento (ex.: 'divida em épicos e histórias')"
                className="flex-1 border p-3 rounded-lg focus:outline-none focus:ring-uece-mid"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    const val = e.target.value;
                    if (val.trim()) {
                      handleRefine(val);
                      e.target.value = "";
                    }
                  }
                }}
              />
              <button
                onClick={handleApprove}
                disabled={loading}
                className="px-4 py-2 rounded-lg bg-uece-emerald text-white font-semibold hover:opacity-95 disabled:opacity-50"
              >
                {loading ? "Aprovando..." : "Aprovar e Enviar"}
              </button>
            </div>
          )}

          {status === "APPROVED" && (
            <div className="mt-4 p-3 bg-uece-emerald/10 text-uece-emerald rounded-lg font-medium">
              ✅ Requisitos aprovados e enviados ao Jira (ou processo simulado).
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
