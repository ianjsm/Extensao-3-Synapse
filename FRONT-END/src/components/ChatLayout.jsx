export default function ChatLayout({ children }) {
  return (
    <div className="flex flex-col h-[calc(100vh-64px)] bg-white rounded-lg shadow-md mx-auto max-w-6xl w-full border">
      <header className="px-6 py-4 border-b bg-[#002A5E] text-white text-lg font-semibold text-center">
        Assistente de Requisitos
      </header>
      <main className="flex-1 overflow-y-auto p-6 bg-gray-50">
        {children || (
          <p className="text-gray-500 text-center mt-10">
            Nenhum chat disponível. Entre para começar a usar o assistente.
          </p>
        )}
      </main>
    </div>
  );
}

