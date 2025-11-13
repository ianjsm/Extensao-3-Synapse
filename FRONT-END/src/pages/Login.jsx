import React, { useState } from "react";
import { Link } from "react-router-dom";

export default function Login() {
  const [email, setEmail] = useState("");
  const [pass, setPass] = useState("");

  const handle = (e) => {
    e.preventDefault();
    alert("Login teórico (implemente backend de auth depois).");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#001a33] via-[#003366] to-[#004b8d]">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-8 border border-gray-200">
        <h2 className="text-3xl font-bold text-center text-[#003366] mb-6">
          Acessar sua conta
        </h2>

        <form onSubmit={handle} className="space-y-5">
          <div>
            <label className="block text-gray-700 font-medium mb-1">
              E-mail
            </label>
            <input
              className="w-full p-3 rounded-lg border border-gray-300 focus:border-[#0057B8] focus:ring-2 focus:ring-[#0057B8]/30 outline-none transition"
              placeholder="exemplo@dominio.com"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-gray-700 font-medium mb-1">
              Senha
            </label>
            <input
              className="w-full p-3 rounded-lg border border-gray-300 focus:border-[#0057B8] focus:ring-2 focus:ring-[#0057B8]/30 outline-none transition"
              placeholder="********"
              type="password"
              value={pass}
              onChange={(e) => setPass(e.target.value)}
            />
          </div>

          <button
            type="submit"
            className="w-full py-3 rounded-lg bg-[#0057B8] hover:bg-[#00449A] text-white font-semibold transition-all duration-200 shadow-md"
          >
            Entrar
          </button>
        </form>

        <p className="mt-6 text-center text-gray-600 text-sm">
          Não tem conta?{" "}
          <Link
            to="/register"
            className="text-[#0057B8] font-medium hover:underline"
          >
            Registrar
          </Link>
        </p>
      </div>
    </div>
  );
}


