import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

export default function Register() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [pass, setPass] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handle = async (e) => {
    e.preventDefault();

    if (!name || !email || !pass) {
      alert("Preencha todos os campos.");
      return;
    }

    setLoading(true);
    try {
    const res = await fetch("http://127.0.0.1:8000/cadastro", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password: pass })
    });;

    const data = await res.json();
    if (!res.ok) {
      alert("Erro: " + JSON.stringify(data));
      return;
    }

    alert("Conta criada com sucesso!");
  } catch (err) {
    console.error(err);
    alert("Erro ao conectar com o servidor.");
  } finally {
      setLoading(false);
  }
};

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#001a33] via-[#003366] to-[#004b8d]">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-8 border border-gray-200">
        <h2 className="text-3xl font-bold text-center text-[#003366] mb-6">
          Criar Conta
        </h2>

        <form onSubmit={handle} className="space-y-5">
          <div>
            <label className="block text-gray-700 font-medium mb-1">
              Nome completo
            </label>
            <input
              className="w-full p-3 rounded-lg border border-gray-300 focus:border-[#0057B8] focus:ring-2 focus:ring-[#0057B8]/30 outline-none transition"
              placeholder="Seu nome"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

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
            disabled={loading}
            className={`w-full py-3 rounded-lg text-white font-semibold transition-all duration-200 shadow-md ${
              loading ? "bg-gray-400 cursor-not-allowed" : "bg-[#0057B8] hover:bg-[#00449A]"
            }`}
          >
            {loading ? "Registrando..." : "Registrar"}
          </button>
        </form>

        <p className="mt-6 text-center text-gray-600 text-sm">
          Já tem conta?{" "}
          <Link
            to="/login"
            className="text-[#0057B8] font-medium hover:underline"
          >
            Entrar
          </Link>
        </p>
      </div>
    </div>
  );
}



