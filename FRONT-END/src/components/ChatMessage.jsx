// Para talvez um markdown no futuro:
// import ReactMarkdown from "react-markdown";
// import remarkGfm from "remark-gfm";

export default function ChatMessage({ sender, text }) {
  const isUser = sender === "user";

  let parsedJson = null;

  // tenta detectar JSON vindo da IA
  try {
    const clean = text.replace(/```json|```/g, "").trim();
    parsedJson = JSON.parse(clean);
  } catch (e) {
    parsedJson = null;
  }

  return (
    <div
      className={`flex items-start gap-3 mb-4 px-3 sm:px-4 ${
        isUser ? "justify-end" : "justify-start"
      }`}
    >
      {/* Avatar IA minimalista */}
      {!isUser && (
        <div className="flex-shrink-0 w-9 h-9 rounded-full bg-gray-200 border border-gray-300 flex items-center justify-center text-[10px] font-semibold text-gray-700 shadow-sm">
          IA
        </div>
      )}

      <div
        className={`
          max-w-[85%] sm:max-w-[75%]
          px-4 py-3
          rounded-2xl text-[0.92rem] sm:text-[0.95rem]
          leading-relaxed break-words
          shadow-sm transition-all
          ${isUser
            ? "bg-[#0057B8] text-white rounded-br-md shadow-md"
            : "bg-white text-gray-900 border border-gray-200 rounded-bl-md"
          }
        `}
      >
        {/* RENDERIZAÇÃO DE USER STORIES JSON */}
        {!isUser && parsedJson?.user_stories ? (
          <div className="space-y-5">
            {parsedJson.user_stories.map((story) => (
              <div
                key={story.id}
                className="border border-gray-300 rounded-xl p-4 bg-gray-50 shadow-sm hover:shadow-md transition-all"
              >
                <h3 className="text-base font-semibold text-gray-900 mb-1">
                  {story.id} — {story.title}
                </h3>

                <div className="text-gray-700 text-sm space-y-1">
                  <p className="font-medium">{story.story.role}</p>
                  <p>{story.story.goal}</p>
                  <p className="italic text-gray-600">{story.story.reason}</p>
                </div>

                <ul className="mt-3 list-disc pl-6 text-gray-800 text-sm space-y-1">
                  {story.acceptance_criteria.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>

                <div className="mt-3 flex flex-wrap gap-4 text-xs text-gray-600">
                  <span className="px-2 py-1 bg-gray-200 rounded-md">
                    <strong>Prioridade:</strong> {story.priority}
                  </span>
                  <span className="px-2 py-1 bg-gray-200 rounded-md">
                    <strong>Estimativa:</strong> {story.estimate} pts
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          // TEXTO NORMAL OU MARKDOWN (se ativado)
          <>
            {/* markdown desativado por enquanto */}
            {/* <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown> */}
            <span>{text}</span>
          </>
        )}
      </div>

      {/* Avatar Usuário minimalista */}
      {isUser && (
        <div className="flex-shrink-0 w-9 h-9 rounded-full bg-[#0057B8] text-white flex items-center justify-center text-[10px] font-semibold shadow-sm">
          Você
        </div>
      )}
    </div>
  );
}



