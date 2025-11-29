import { useState, useRef, useEffect, useContext } from "react";
import ChatLayout from "../components/ChatLayout";
import ChatMessage from "../components/ChatMessage";
import { UserContext } from "../context/UserContext";

export default function Chat() {
  const { user } = useContext(UserContext);
  const userId = user?.id;

  const [chats, setChats] = useState([]);
  const [activeChat, setActiveChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [pdfStatus, setPdfStatus] = useState("");
  const [recording, setRecording] = useState(false);
  const [loading, setLoading] = useState(false);
  const [isFirstMessage, setIsFirstMessage] = useState(true);
  const [jiraStatus, setJiraStatus] = useState(""); // ← status de integração com Jira
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // --- GERAR DOCUMENTAÇÃO ---
  const generateDocumentation = async () => {
    const lastAssistantMsg = [...messages].reverse().find(m => m.sender === "assistant");
    if (!lastAssistantMsg) {
      setPdfStatus("Nada para gerar em PDF.");
      return;
    }

    setPdfStatus("Gerando documentação...");

    try {
      const res = await fetch("http://127.0.0.1:8000/generate_pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          client_request: messages[0]?.content || "N/A",
          requirements: lastAssistantMsg.content 
        }),
      });

      if (!res.ok) throw new Error("Falha ao gerar PDF.");

      // Se o backend retornar o PDF binário:
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "documentacao_requisitos.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();

      setPdfStatus("✅ PDF gerado com sucesso!");
    } catch (err) {
      console.error(err);
      setPdfStatus("❌ Erro ao gerar PDF.");
    }
  };


  // ------------------ LOAD HISTÓRICO ------------------
  const fetchChats = async () => {
    if (!userId) return;

    try {
      const res = await fetch(`http://127.0.0.1:8000/chats?user_id=${userId}`);
      const data = await res.json();
      setChats(data);
      if (data.length > 0) {
        setActiveChat(data[0]);
        setMessages(data[0].messages);
      } else {
        setActiveChat(null);
        setMessages([]);
      }
    } catch (err) {
      console.error("Erro ao buscar chats:", err);
    }
  };

  useEffect(() => {
    fetchChats();
  }, [userId]);

  const selectChat = (chat) => {
    setActiveChat(chat);
    setMessages(chat.messages);
    setPdfStatus("");     // <-- limpa status
    setJiraStatus("");    // <-- limpa status
  };

  // ------------------ BUILD HISTORY ------------------
  const buildHistory = () => messages.map(m => ({ role: m.sender, content: m.content }));

  // ------------------ ENVIAR MENSAGEM ------------------
  const sendMessage = async () => {
    if (!input.trim() || !userId || loading) return;
    setLoading(true);
    setJiraStatus(""); // limpa status Jira

    const userMsg = { sender: "user", content: input };
    setMessages(prev => [...prev, userMsg]);
    const messageContent = input;
    setInput("");

    try {
      // cria chat se não existir
      let chatId = activeChat?.id;
      if (!chatId) {
        const chatRes = await fetch("http://127.0.0.1:8000/chat_message", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: userId,
            content: messageContent,
            sender: "user",
            chat_id: null,
          }),
        });
        const chatData = await chatRes.json();
        chatId = chatData.chat_id;
        setActiveChat({ id: chatId, title: messageContent.substring(0, 50) });
      } else {
        await fetch("http://127.0.0.1:8000/chat_message", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: userId,
            content: messageContent,
            sender: "user",
            chat_id: chatId,
          }),
        });
      }

      // chamada da LLM
      let res;
      if (isFirstMessage) {
        res = await fetch("http://127.0.0.1:8000/start_analysis", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ client_request: messageContent }),
        });
        setIsFirstMessage(false);
      } else {
        res = await fetch("http://127.0.0.1:8000/refine", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ instruction: messageContent, history: buildHistory() }),
        });
      }

      const data = await res.json();
      const assistantMsg = {
        sender: "assistant",
        content: data.generated_requirements || data.refined_requirements || "...",
      };
      setMessages(prev => [...prev, assistantMsg]);

      // salva no DB
      await fetch("http://127.0.0.1:8000/chat_message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          content: assistantMsg.content,
          sender: "assistant",
          chat_id: chatId,
        }),
      });

      fetchChats();
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { sender: "assistant", content: "Erro ao conectar com o servidor." }]);
    } finally {
      setLoading(false);
    }
  };

  // ------------------ INTEGRAR AO JIRA ------------------
  function extractJson(text) {
    try {
      // remove blocos ```json ... ```
      const cleaned = text
        .replace(/```json/gi, "")
        .replace(/```/g, "")
        .trim();

      return JSON.parse(cleaned);
    } catch (e) {
      console.error("JSON inválido:", e);
      return null;
    }
  }

  const integrateToJira = async () => {
    const lastAssistantMsg = [...messages].reverse().find(m => m.sender === "assistant");
    const lastUserMsg = [...messages].reverse().find(m => m.sender === "user");

    if (!lastAssistantMsg || !lastUserMsg) {
      setJiraStatus("Nada para enviar ao Jira.");
      return;
    }

    setJiraStatus("Enviando ao Jira...");

    try {
      
      const parsed = extractJson(lastAssistantMsg.content);

      if (!parsed) {
        setJiraStatus("❌ O assistente não retornou JSON válido.");
        return;
      }

      console.log("DEBUG >>> Enviando para o approve()", parsed);

      const res = await fetch("http://127.0.0.1:8000/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          final_requirements: JSON.stringify(parsed),
          original_request: lastUserMsg.content,
        }),
      });

      const data = await res.json();

      if (res.ok) {
        if (data.created_tickets?.length > 0) {
          setJiraStatus(`✅ ${data.created_tickets.length} tickets criados no Jira!`);
        } else if (data.invalid_requirements?.length > 0) {
          setJiraStatus("⚠️ Alguns requisitos precisam ser revisados antes de enviar.");
        } else {
          setJiraStatus("✅ Enviado com sucesso!");
        }
      } else {
        setJiraStatus("❌ Erro ao enviar ao Jira.");
      }
    } catch (err) {
      console.error(err);
      setJiraStatus("❌ Erro de conexão com o Jira.");
    }
  };

  // ------------------ VOICE INPUT ------------------
  const handleVoiceInput = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      alert("Seu navegador não suporta gravação de áudio.");
      return;
    }

    if (!recording) {
      setRecording(true);
      audioChunksRef.current = [];
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => audioChunksRef.current.push(e.data);
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

  const sendAudio = async (file) => {
    const formData = new FormData();
    formData.append("file", file);
    setLoading(true);

    try {
      const res = await fetch("http://127.0.0.1:8000/audio_chat", { method: "POST", body: formData });
      const data = await res.json();
      setMessages(prev => [
        ...prev,
        { sender: "user", content: data.transcript },
        { sender: "assistant", content: data.llm_response },
      ]);
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { sender: "assistant", content: "Erro ao processar áudio." }]);
    } finally {
      setLoading(false);
    }
  };

  // ------------------ RENDER ------------------
  return (
    <ChatLayout>
      <div className="flex h-full">
        {/* --- SIDEBAR --- */}
        <div className="w-64 border-r border-gray-300 overflow-y-auto bg-white">
          <h2 className="p-4 font-bold text-lg border-b text-black">Meus Chats</h2>

          {userId && (
            <button
              onClick={async () => {
                try {
                  const res = await fetch("http://127.0.0.1:8000/chat_message", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      user_id: userId,
                      content: "Novo chat",
                      sender: "user",
                      chat_id: null,
                    }),
                  });
                  const data = await res.json();
                  const newChat = { id: data.chat_id, title: "Novo chat", messages: [] };
                  setChats(prev => [newChat, ...prev]);
                  setActiveChat(newChat);
                  setMessages([]);
                } catch (err) {
                  console.error("Erro ao criar novo chat:", err);
                }
              }}
              className="w-[calc(100%-2rem)] mx-4 my-3 bg-[#0057B8] text-white font-semibold py-2 rounded-xl hover:bg-[#00449A] transition-colors"
            >
              + Novo Chat
            </button>
          )}

          {userId ? (
            chats.length > 0 ? (
              chats.map(chat => (
                <div
                  key={chat.id}
                  className={`p-3 cursor-pointer hover:bg-gray-100 ${
                    activeChat?.id === chat.id ? "bg-gray-200 font-semibold" : ""
                  } text-gray-900`}
                  onClick={() => selectChat(chat)}
                >
                  {chat.title}
                </div>
              ))
            ) : (
              <p className="p-4 text-gray-700 text-sm">Você ainda não tem chats.</p>
            )
          ) : (
            <p className="p-4 text-gray-700 text-sm">Entre para ver seu histórico de chats.</p>
          )}
        </div>

        {/* --- CHAT PRINCIPAL --- */}
        <div className="flex-1 flex flex-col">
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((m, i) => (
              <div key={i}>
                <ChatMessage sender={m.sender} text={m.content} />
                {/* Exibe botões somente na última resposta do assistente */}
                {m.sender === "assistant" && i === messages.length - 1 && (
                  <div className="mt-2 flex flex-wrap gap-2 items-center">
                    {/* --- BOTÃO JIRA --- */}
                    <button
                      onClick={integrateToJira}
                      className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
                    >
                      Aprovar e Integrar ao Jira
                    </button>

                    {/* --- BOTÃO PDF (vermelho) --- */}
                    <button
                      onClick={generateDocumentation}
                      className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      Gerar PDF
                    </button>

                    {/* Status das operações */}
                    {(jiraStatus || pdfStatus) && (
                      <div className="w-full mt-1 text-sm text-gray-700">
                        {jiraStatus && <p>{jiraStatus}</p>}
                        {pdfStatus && <p>{pdfStatus}</p>}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
            {loading && <ChatMessage sender="assistant" text="Pensando..." />}
          </div>

          {/* --- CAMPO DE ENTRADA --- */}
          <div className="border-t flex items-center p-4 bg-white">
            <input
              type="text"
              placeholder="Descreva o sistema que você gostaria de desenvolver..."
              className="flex-1 px-4 py-3 border rounded-xl mr-2 focus:outline-none focus:ring-2 focus:ring-[#0057B8] text-gray-900 placeholder:text-gray-500"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && sendMessage()}
            />

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
        </div>
      </div>
    </ChatLayout>
  );
}




