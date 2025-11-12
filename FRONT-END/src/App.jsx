import React, { useState, useRef } from "react";
import axios from "axios";
import "./index.css";

const API_URL = "http://127.0.0.1:8000";

export default function App() {
  const [message, setMessage] = useState("");
  const [chat, setChat] = useState([]); // items: { role: 'user'|'assistant', content: '...' }
  const [appState, setAppState] = useState("START");
  const [originalRequest, setOriginalRequest] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // UTIL: normaliza history vindo do backend para nosso formato
  function normalizeHistory(history) {
    if (!Array.isArray(history)) return [];
    return history.map((m) => {
      // Suporta {role, content} ou {sender, text}
      return {
        role: m.role || m.sender || "assistant",
        content: m.content ?? m.text ?? "",
      };
    });
  }

  // ENVIA TEXTO: start_analysis ou refine conforme estado
  const sendMessage = async () => {
    if (!message.trim() || isLoading) return;

    const userText = message.trim();

    // Adiciona mensagem do usuário localmente (imediato)
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

        // Preferir 'history' se existir (retorno mostrado no seu back)
        if (res.data?.history) {
          setChat(normalizeHistory(res.data.history));
        } else if (res.data?.generated_requirements) {
          // Fallback: cria history a partir do generated_requirements
          setChat([
            { role: "user", content: userText },
            { role: "assistant", content: res.data.generated_requirements },
          ]);
        } else {
          // Caso inesperado, mostra raw
          setChat((prev) => [
            ...prev,
            { role: "assistant", content: JSON.stringify(res.data) },
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
        } else {
          setChat((prev) => [
            ...prev,
            { role: "assistant", content: JSON.stringify(res.data) },
          ]);
        }
      }
    } catch (err) {
      console.error("sendMessage error:", err);
      setChat((prev) => [
        ...prev,
        { role: "assistant", content: "Erro ao processar texto. Veja console para detalhes." },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // APROVAR e enviar ao Jira
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
      alert(`Sucesso! ${res.data.message || "Tickets criados."}`);

      // Reset
      setChat([]);
      setOriginalRequest("");
      setAppState("START");
    } catch (err) {
      console.error("approveRequest error:", err);
      alert("Erro ao aprovar — ver console.");
    } finally {
      setIsLoading(false);
    }
  };

  // INICIA gravação
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];

      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => audioChunksRef.current.push(e.data);
      recorder.onstop = sendAudioToBackend;

      recorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error("startRecording error:", err);
      alert("Erro ao acessar microfone (permissão?).");
    }
  };

  // PARA gravação
  const stopRecording = () => {
    if (mediaRecorderRef.current) mediaRecorderRef.current.stop();
    setIsRecording(false);
  };

  // ENVIA áudio para /audio_chat e depois injeta transcript + resposta do LLM
  const sendAudioToBackend = async () => {
    const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
    const form = new FormData();
    form.append("file", blob, "audio.webm");

    setIsLoading(true);
    try {
      const res = await axios.post(`${API_URL}/audio_chat`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      console.log("audio_chat response:", res.data);

      const transcript = res.data?.transcript ?? "";
      const llm_response = res.data?.llm_response ?? "";

      // adiciona transcript e resposta
      setChat((prev) => [
        ...prev,
        { role: "user", content: transcript },
        { role: "assistant", content: llm_response },
      ]);

      // se esta era a primeira interação, atualiza estado
      if (appState === "START") setAppState("REFINING");
    } catch (err) {
      console.error("sendAudioToBackend error:", err);
      setChat((prev) => [...prev, { role: "assistant", content: "Erro ao processar áudio." }]);
    } finally {
      setIsLoading(false);
    }
  };

  // RENDER helpers
  const handleEnter = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="app-layout">
      {/* NAVBAR */}
      <nav className="navbar-container">
        <div className="logo">Synapse</div>
        <div className="nav-links">
          <button className="nav-btn">Sobre</button>
          <button className="nav-btn">Login</button>
          <button className="nav-btn highlight">Registrar</button>
        </div>
      </nav>

      {/* HERO */}
      <section className="hero-section">
        <h1 className="hero-title">Transforme ideias em requisitos claros</h1>
        <p className="hero-subtitle">Seu assistente inteligente para documentar projetos com precisão.</p>

        <div className="hero-input-area">
          <input
            placeholder="Digite a solicitação..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleEnter}
            disabled={isLoading}
          />

          <button className="send-btn" onClick={sendMessage} disabled={isLoading}>
            ↑
          </button>

          {!isRecording ? (
            <button className="mic-btn" onClick={startRecording} title="Gravar áudio (máx 2 min)">
              🎤
            </button>
          ) : (
            <button className="mic-btn recording" onClick={stopRecording}>
              🔴
            </button>
          )}
        </div>
      </section>

      {/* CHAT */}
      <div className="chat-container">
        <div className="chat-header">Assistente de Requisitos</div>

        <div className="chat-window">
          {chat.length === 0 && <div className="empty-hint">Envie a primeira solicitação (texto ou áudio)</div>}

          {chat.map((m, i) => (
            <div key={i} className={`message ${m.role === "user" ? "user" : "assistant"}`}>
              {m.content}
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



