import { Link } from "react-router-dom";

export default function Navbar() {
  return (
    <nav className="bg-[#002A5E] text-white shadow-md px-8 py-4 flex justify-between items-center">
      <h1 className="text-2xl font-semibold tracking-wide">
        Synapse<span className="text-[#00AEEF]">AI</span>
      </h1>
      <div className="flex space-x-6">
        <Link to="/" className="hover:text-[#00AEEF]">Início</Link>
        <Link to="/chat" className="hover:text-[#00AEEF]">Assistente</Link>
        <Link to="/sobre" className="hover:text-[#00AEEF]">Sobre</Link>
      </div>
      <div className="space-x-4">
        <Link
          to="/login"
          className="px-4 py-2 rounded-md bg-[#0057B8] hover:bg-[#007BFF]"
        >
          Login
        </Link>
        <Link
          to="/register"
          className="px-4 py-2 rounded-md border border-white hover:bg-white hover:text-[#002A5E]"
        >
          Registrar
        </Link>
      </div>
    </nav>
  );
}


