import { useState, useRef, useEffect } from "react";
import aiAvatar from "../../assets/ai-avatar.png"; // coloque sua imagem aqui

export default function AiInstructionSidebar({ sprint, onUpdateSprint }) {
  const [instruction, setInstruction] = useState("");
  const [working, setWorking] = useState(false);
  const [messages, setMessages] = useState([]);
  const chatRef = useRef(null);

  // Scroll automático para a última mensagem
  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  if (!sprint) {
    return (
      <div className="bg-gray-50 rounded-2xl shadow-lg p-4 text-center text-gray-500">
        Selecione uma sprint para usar o assistente.
      </div>
    );
  }

  const handleAskAI = async () => {
    if (!instruction.trim()) return;
    setWorking(true);

    const userMessage = { text: instruction, from: "user" };
    setMessages(prev => [...prev, userMessage]);
    setInstruction("");

    try {
      const res = await fetch("http://127.0.0.1:8000/sprint/replan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_tasks: sprint.tasks, instruction })
      });

      if (!res.ok) throw new Error("Erro IA");
      const data = await res.json();

      const updated = { ...sprint, tasks: data.tasks || sprint.tasks };
      onUpdateSprint(updated);

      const aiMessage = {
        text: "Sprint atualizada com base na sua instrução ✅",
        from: "ai"
      };
      setMessages(prev => [...prev, aiMessage]);
    } catch (err) {
      console.error(err);
      const errorMessage = {
        text: "Erro ao processar sua solicitação 😓",
        from: "ai"
      };
      setMessages(prev => [...prev, errorMessage]);
      alert("Erro ao solicitar IA.");
    } finally {
      setWorking(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-2xl p-4 flex flex-col gap-4 max-w-md mx-auto">
      <h4 className="font-bold text-xl text-gray-800">SynapseAI</h4>
      <p className="text-sm text-gray-500">
        Peça mudanças na sprint (ex.: "reduza complexidade", "divida a task X").
      </p>

      {/* Chat */}
      <div
        ref={chatRef}
        className="flex flex-col gap-3 h-64 overflow-y-auto p-2 bg-gray-50 rounded-xl border border-gray-200"
      >
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex items-start gap-2 ${
              m.from === "ai" ? "justify-start" : "justify-end"
            }`}
          >
            {m.from === "ai" && (
              <img
                src={aiAvatar}
                alt="AI"
                className="w-8 h-8 rounded-full shadow-sm"
              />
            )}
            <div
              className={`px-3 py-2 rounded-xl max-w-xs break-words ${
                m.from === "ai" ? "bg-blue-100 text-gray-800" : "bg-blue-600 text-white"
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="flex gap-2 mt-2 text-gray-800">
        <textarea
          value={instruction}
          onChange={e => setInstruction(e.target.value)}
          rows={2}
          className="flex-1 border border-gray-300 rounded-xl p-3 focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none"
          placeholder="Escreva sua instrução para o SynapseAI..."
        />
        <button
          onClick={handleAskAI}
          disabled={working || !instruction.trim()}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {working ? "Processando..." : "Enviar"}
        </button>
      </div>
    </div>
  );
}


