export default function ChatMessage({ sender, text }) {
  const isUser = sender === "user";

  return (
    <div
      className={`flex ${
        isUser ? "justify-end" : "justify-start"
      } mb-3 px-4`}
    >
      <div
        className={`max-w-[75%] px-4 py-2 rounded-2xl text-sm leading-relaxed break-words ${
          isUser
            ? "bg-[#0057B8] text-white" // mensagem do usuário
            : "bg-gray-100 text-gray-900" // resposta do assistente
        }`}
      >
        {text}
      </div>
    </div>
  );
}
