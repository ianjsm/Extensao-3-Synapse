import { Link } from "react-router-dom";

export default function Home() {
  return (
    <section className="min-h-[calc(100vh-64px)] flex flex-col items-center justify-center bg-gradient-to-b from-[#002A5E] to-[#0057B8] text-white text-center px-6">
      <h1 className="text-5xl font-bold mb-4">Transforme reuniões em requisitos claros</h1>
      <p className="text-lg max-w-2xl mb-8 text-gray-200">
        Gere histórias, backlog e documentação automaticamente a partir de texto ou áudio.
        Entregue clareza para a equipe e velocidade para o projeto.
      </p>
      <div className="space-x-4">
        <Link
          to="/chat"
          className="px-6 py-3 bg-white text-[#002A5E] rounded-lg font-semibold hover:bg-gray-100"
        >
          Abrir Assistente
        </Link>
        <Link
          to="/login"
          className="px-6 py-3 border border-white rounded-lg hover:bg-white hover:text-[#002A5E]"
        >
          Entrar
        </Link>
      </div>
    </section>
  );
}


