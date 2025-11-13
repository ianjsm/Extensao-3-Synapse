import { Link, useNavigate } from "react-router-dom";
import { useContext } from "react";
import { UserContext } from "../context/UserContext";

export default function Navbar() {
  const { user, logout } = useContext(UserContext);
  const navigate = useNavigate();

  const firstName = user?.name?.split(" ")[0];

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

      <div className="space-x-4 flex items-center">
        {user ? (
          <>
            <span>Olá, {firstName}</span>
            <button
              onClick={() => navigate("/config")}
              className="p-2 rounded-full hover:bg-[#00449A] transition-colors"
              title="Configurações"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 4v1m0 14v1m8-8h1M4 12H3m15.364-6.364l.707.707M6.343 17.657l-.707.707m12.728 0l.707-.707M6.343 6.343l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z"
                />
              </svg>
            </button>
            <button
              onClick={logout}
              className="px-4 py-2 rounded-md bg-red-600 hover:bg-red-700 transition-colors"
            >
              Sair
            </button>
          </>
        ) : (
          <>
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
          </>
        )}
      </div>
    </nav>
  );
}



