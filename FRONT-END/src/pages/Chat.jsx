import { useState, useRef } from "react";
import ChatLayout from "../components/ChatLayout";
import ChatMessage from "../components/ChatMessage";

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [recording, setRecording] = useState(false);
  const [loading, setLoading] = useState(false); // novo estado
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // Envia mensagem de texto
  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMsg = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true); // ativa "Pensando..."

    try {
      const res = await fetch("http://127.0.0.1:8000/start_analysis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_request: input }),
      });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { sender: "assistant", text: data.generated_requirements || "...", 
          canApprove: true,
          originalRequest: input, },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { sender: "assistant", text: "Erro ao conectar com o servidor." },
      ]);
    } finally {
      setLoading(false); // desativa "Pensando..."
    }
  };

  // Inicia/para gravação e envia para o back-end
  const handleVoiceInput = async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      alert("Seu navegador não suporta gravação de áudio.");
      return;
    }

    if (!recording) {
      setRecording(true);
      audioChunksRef.current = [];
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        setRecording(false);
        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        const file = new File([blob], "audio.webm", { type: "audio/webm" });
        await sendAudio(file);
      };

      mediaRecorder.start();
    } else {
      mediaRecorderRef.current.stop();
    }
  };

  // Envia o áudio para o back-end
  const sendAudio = async (file) => {
    const formData = new FormData();
    formData.append("file", file);
    setLoading(true); // ativa "Pensando..." enquanto processa áudio

    try {
      const res = await fetch("http://127.0.0.1:8000/audio_chat", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { sender: "user", text: data.transcript },
        { sender: "assistant", text: data.llm_response },
      ]);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        { sender: "assistant", text: "Erro ao processar áudio." },
      ]);
    } finally {
      setLoading(false); // desativa "Pensando..."
    }
  };

  // Função para aprovar e mandar para o Jira
  const approveAndSendToJira = async (message) => {
    try {
      await fetch("http://127.0.0.1:8000/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          final_requirements: message.text,
          original_request: message.originalRequest,
        }),
      });
      alert("Requisitos enviados para o Jira com sucesso!");
    } catch (err) {
      console.error(err);
      alert("Erro ao enviar para o Jira.");
    }
  };

  return (
    <ChatLayout>
      {messages.map((m, i) => (
        <div key={i} className="mb-2">
          <ChatMessage sender={m.sender} text={m.text} />
          {m.canApprove && (
            <button
              onClick={() => approveAndSendToJira(m)}
              className="mt-1 px-3 py-1 bg-green-500 text-white rounded hover:bg-green-600"
            >
              Aprovar e Mandar para o Jira
            </button>
          )}
        </div>
      ))}

      {loading && <ChatMessage sender="assistant" text="Pensando..." />}

      <div className="border-t flex items-center p-4 bg-white mt-4">
        <input
          type="text"
          placeholder="Descreva o sistema que você gostaria de desenvolver..."
          className="flex-1 px-4 py-3 border rounded-xl mr-2 focus:outline-none focus:ring-2 focus:ring-[#0057B8] text-gray-900 placeholder:text-gray-500"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        />

        {/* Botão de Áudio */}
        <button
          onClick={handleVoiceInput}
          className={`mr-2 p-3 rounded-full transition-colors duration-200 ${
            recording
              ? "bg-red-500 hover:bg-red-600 text-white"
              : "bg-gray-200 hover:bg-gray-300 text-gray-700"
          }`}
          title={recording ? "Parar gravação" : "Falar"}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-5 w-5"
            fill={recording ? "white" : "currentColor"}
            viewBox="0 0 24 24"
          >
            <path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3z" />
            <path d="M19 11a7 7 0 0 1-14 0" />
            <line x1="12" y1="19" x2="12" y2="23" stroke="currentColor" strokeWidth="2" />
            <line x1="8" y1="23" x2="16" y2="23" stroke="currentColor" strokeWidth="2" />
          </svg>
        </button>

        <button
          onClick={sendMessage}
          className="bg-[#0057B8] text-white px-5 py-3 rounded-xl hover:bg-[#00449A]"
        >
          Enviar
        </button>
      </div>
    </ChatLayout>
  );
}



