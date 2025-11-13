import React, { useState, useRef } from "react";
import axios from "axios";
import "./index.css";
import ReactMarkdown from 'react-markdown'; // <-- MUDANÇA 1: IMPORTAR

const API_URL = "http://127.0.0.1:8000";

export default function App() {
  const [message, setMessage] = useState("");
  const [chat, setChat] = useState([]); 
  const [appState, setAppState] = useState("START");
  const [originalRequest, setOriginalRequest] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // (Função normalizeHistory como você escreveu... sem mudanças)
  function normalizeHistory(history) {
    if (!Array.isArray(history)) return [];
    return history.map((m) => {
      return {
        role: m.role || m.sender || "assistant",
        content: m.content ?? m.text ?? "",
      };
    });
  }

  // (Função sendMessage como você escreveu... sem mudanças)
  const sendMessage = async () => {
    if (!message.trim() || isLoading) return;
    const userText = message.trim();
    setChat((prev) => [...prev, { role: "user", content: userText }]);
    setMessage("");
    setIsLoading(true);

    try {
      if (appState === "START") {
        setOriginalRequest(userText);
        const res = await axios.post(`${API_URL}/start_analysis`, {
          client_request: userText,
        });
        console.log("start_analysis response:", res.data);
        if (res.data?.history) {
          setChat(normalizeHistory(res.data.history));
        } else if (res.data?.generated_requirements) {
          setChat([
            { role: "user", content: userText },
            { role: "assistant", content: res.data.generated_requirements },
          ]);
        }
        setAppState("REFINING");
      } else {
        // REFINAMENTO
        const res = await axios.post(`${API_URL}/refine`, {
          instruction: userText,
          history: chat,
        });
        console.log("refine response:", res.data);
        if (res.data?.history) {
          setChat(normalizeHistory(res.data.history));
        } else if (res.data?.refined_requirements) {
          setChat((prev) => [
            ...prev,
            { role: "user", content: userText },
            { role: "assistant", content: res.data.refined_requirements },
          ]);
        }
      }
    } catch (err) {
      console.error("sendMessage error:", err);
      setChat((prev) => [
        ...prev,
        { role: "assistant", content: "Erro ao processar texto. Veja console." },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // --- MUDANÇA 2: LÓGICA DE APROVAÇÃO ATUALIZADA ---
  const approveRequest = async () => {
    if (!originalRequest || chat.length === 0) return alert("Nada para aprovar.");

    const lastAssistant = [...chat].reverse().find((m) => m.role === "assistant");
    if (!lastAssistant) return alert("Nenhuma resposta do assistente para aprovar.");

    setIsLoading(true);
    try {
      const res = await axios.post(`${API_URL}/approve`, {
        final_requirements: lastAssistant.content,
        original_request: originalRequest,
      });

      console.log("approve response:", res.data);

      // --- NOVA VERIFICAÇÃO DE VALIDAÇÃO ---
      if (res.data.invalid_requirements && res.data.invalid_requirements.length > 0) {
        // O backend encontrou erros e não criou tickets
        let errorMsg = "Revisão Necessária! O backend encontrou problemas nos seguintes requisitos (nenhum ticket foi criado):\n\n";
        res.data.invalid_requirements.forEach(item => {
          errorMsg += `ERRO: ${item.erro_como_um ? "Falta 'Como um..'" : ""} ${item.erro_criterios ? "Falta 'Critério de Aceite'" : ""}\n`;
          errorMsg += `REQUISITO: ${item.requisito.substring(0, 100)}...\n\n`;
        });
        alert(errorMsg);
        
        // Adiciona o erro ao chat para o usuário consertar
        setChat(prev => [...prev, {role: "assistant", content: errorMsg}]);

      } else {
        // Sucesso!
        alert(`Sucesso! ${res.data.message || "Tickets criados."}`);
        // Reset
        setChat([]);
        setOriginalRequest("");
        setAppState("START");
      }
    } catch (err) {
      console.error("approveRequest error:", err);
      alert(`Erro ao aprovar: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // (Funções startRecording e stopRecording como você escreveu... sem mudanças)
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      recorder.ondataavailable = (e) => audioChunksRef.current.push(e.data);
      recorder.onstop = sendAudioToBackend; // Chama a função de envio ao parar
      recorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error("startRecording error:", err);
      alert("Erro ao acessar microfone (permissão?).");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) mediaRecorderRef.current.stop();
    setIsRecording(false);
  };

  // (Função sendAudioToBackend como você escreveu... sem mudanças)
  // Ela já está pronta para o novo backend!
  const sendAudioToBackend = async () => {
    const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
    const form = new FormData();
    form.append("file", blob, "audio.webm");

    setIsLoading(true);
    // Limpa a mensagem de texto, se houver
    setMessage("");

    try {
      const res = await axios.post(`${API_URL}/audio_chat`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      console.log("audio_chat response:", res.data);

      const transcript = res.data?.transcript ?? "";
      const llm_response = res.data?.llm_response ?? "";

      // Salva o transcrito como o "original" se for a primeira mensagem
      if (appState === "START") {
        setOriginalRequest(transcript);
      }

      // Adiciona transcrito (como user) e resposta (como assistant)
      setChat((prev) => [
        ...prev,
        { role: "user", content: `(Áudio transcrito): ${transcript}` },
        { role: "assistant", content: llm_response },
      ]);
      
      if (appState === "START") setAppState("REFINING");
    } catch (err) {
      console.error("sendAudioToBackend error:", err);
      const errorDetail = err.response?.data?.detail || "Erro ao processar áudio.";
      setChat((prev) => [...prev, { role: "assistant", content: `Erro: ${errorDetail}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  // (Função handleEnter como você escreveu... sem mudanças)
  const handleEnter = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="app-layout">
      {/* (Navbar e Hero Section como você escreveu... sem mudanças) */}
      <nav className="navbar-container">
        <div className="logo">Synapse</div>
        <div className="nav-links">
          <button className="nav-btn">Sobre</button>
          <button className="nav-btn">Login</button>
          <button className="nav-btn highlight">Registrar</button>
        </div>
      </nav>

      <section className="hero-section">
        <h1 className="hero-title">Transforme ideias em requisitos claros</h1>
        <p className="hero-subtitle">Seu assistente inteligente para documentar projetos com precisão.</p>
        <div className="hero-input-area">
          {/* ... (input e botões do hero) ... */}
        </div>
      </section>

      {/* CHAT */}
      <div className="chat-container">
        <div className="chat-header">Assistente de Requisitos</div>

        <div className="chat-window">
          {chat.length === 0 && <div className="empty-hint">Envie a primeira solicitação (texto ou áudio)</div>}

          {/* --- MUDANÇA 3: RENDERIZAÇÃO COM MARKDOWN --- */}
          {chat.map((m, i) => (
            <div key={i} className={`message ${m.role === "user" ? "user" : "assistant"}`}>
              {m.role === "assistant" ? (
                <ReactMarkdown>{m.content}</ReactMarkdown>
              ) : (
                m.content
              )}
            </div>
          ))}

          {isLoading && <div className="message assistant">Processando...</div>}
        </div>

        {appState === "REFINING" && (
          <button className="approve-btn" onClick={approveRequest} disabled={isLoading}>
            Aprovar e Enviar ao Jira
          </button>
        )}

        <div className="chat-input-area">
          <input
            placeholder="Digite sua mensagem..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleEnter}
            disabled={isLoading}
          />
          <button onClick={sendMessage} disabled={isLoading}>
            Enviar
          </button>
          {!isRecording ? (
            <button className="mic-btn" onClick={startRecording}>
              🎤
            </button>
          ) : (
            <button className="mic-btn recording" onClick={stopRecording}>
              🔴
            </button>
          )}
        </div>
      </div>
    </div>
  );
}