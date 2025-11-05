import { useState } from 'react';
import axios from 'axios';
import './index.css';

// URL da nossa API Backend (que está rodando em localhost:8000)
const API_URL = "http://127.0.0.1:8000";

function App() {
  // --- Estados do React ---
  // Histórico da conversa (para renderizar na tela e enviar ao /refine)
  const [chatHistory, setChatHistory] = useState([]);
  // O que o usuário está digitando agora
  const [currentInput, setCurrentInput] = useState("");
  // A *primeira* solicitação do cliente (para o /approve)
  const [originalRequest, setOriginalRequest] = useState("");
  // Estado da conversa: 'START' (esperando 1ª msg) ou 'REFINING' (já conversando)
  const [appState, setAppState] = useState("START");
  // Para mostrar "Carregando..."
  const [isLoading, setIsLoading] = useState(false);

  // --- Função: Lida com o envio da mensagem ---
  const handleSubmit = async (e) => {
    e.preventDefault(); // Impede o recarregamento da página
    if (!currentInput.trim() || isLoading) return; // Não envia se estiver vazio ou carregando

    const userMessage = currentInput;
    setCurrentInput(""); // Limpa o input
    setIsLoading(true);

    try {
      if (appState === "START") {
        // --- 1. É a PRIMEIRA MENSAGEM: Chama /start_analysis ---
        setOriginalRequest(userMessage); // Salva a 1ª mensagem

        const response = await axios.post(`${API_URL}/start_analysis`, {
          client_request: userMessage
        });
        
        // A API retorna o histórico completo (usuário + assistente)
        setChatHistory(response.data.history);
        setAppState("REFINING"); // Muda o estado para refinamento
      } 
      else {
        // --- 2. É REFINAMENTO: Chama /refine ---
        const response = await axios.post(`${API_URL}/refine`, {
          instruction: userMessage,
          history: chatHistory // Envia o histórico atual
        });

        // A API retorna o histórico ATUALIZADO
        setChatHistory(response.data.history);
      }
    } catch (error) {
      console.error("Erro ao enviar mensagem:", error);
      // Adiciona uma mensagem de erro ao chat
      setChatHistory(prev => [...prev, { role: "assistant", content: `Erro ao processar: ${error.message}` }]);
    } finally {
      setIsLoading(false); // Para de carregar
    }
  };

  // --- Função: Lida com a aprovação e envio ao Jira ---
  const handleApprove = async () => {
    if (!originalRequest || chatHistory.length === 0) {
      alert("Não há nada para aprovar.");
      return;
    }

    // Pega a ÚLTIMA resposta do assistente no histórico
    const lastAssistantMessage = chatHistory.findLast(msg => msg.role === "assistant");
    if (!lastAssistantMessage) {
      alert("Erro: não foi possível encontrar a última resposta dos requisitos.");
      return;
    }

    setIsLoading(true);
    try {
      const response = await axios.post(`${API_URL}/approve`, {
        final_requirements: lastAssistantMessage.content,
        original_request: originalRequest
      });

      // Sucesso!
      const ticketKeys = response.data.created_tickets.map(t => t.key).join(", ");
      alert(`Sucesso! ${response.data.message}\nTickets criados: ${ticketKeys}`);
      
      // Reseta a aplicação
      setChatHistory([]);
      setOriginalRequest("");
      setAppState("START");

    } catch (error) {
      console.error("Erro ao aprovar:", error);
      alert(`Erro ao enviar para o Jira: ${error.response?.data?.detail || error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // --- Renderização da UI (JSX) ---
  return (
    <div className="app-container">
      <h1>Assistente de Requisitos</h1>
      
      <div className="chat-window">
        {chatHistory.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            {/* Usamos <pre> para o assistente para respeitar as quebras de linha e formatação */}
            {msg.role === 'assistant' ? (
              <pre style={{ fontFamily: 'inherit', fontSize: 'inherit' }}>{msg.content}</pre>
            ) : (
              msg.content
            )}
          </div>
        ))}
        {isLoading && <div className="loading-indicator">Assistente está pensando...</div>}
      </div>

      <div className="controls">
        {/* Mostra o botão de Aprovar apenas se já tivermos uma conversa */}
        {appState === "REFINING" && (
          <button 
            className="approve-button"
            onClick={handleApprove}
            disabled={isLoading}
          >
            Aprovar e Enviar ao Jira
          </button>
        )}
        
        <form className="input-form" onSubmit={handleSubmit}>
          <input
            type="text"
            value={currentInput}
            onChange={(e) => setCurrentInput(e.target.value)}
            placeholder={
              appState === "START"
                ? "Digite a solicitação do cliente..."
                : "Digite uma instrução de refinamento..."
            }
            disabled={isLoading}
          />
          <button type="submit" disabled={isLoading}>Enviar</button>
        </form>
      </div>
    </div>
  );
}

export default App;