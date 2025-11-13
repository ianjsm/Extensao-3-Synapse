import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";

export default function Hero() {
  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="max-w-4xl mx-auto px-6 py-16 text-center"
    >
      <div className="rounded-2xl p-10 bg-gradient-to-br from-[#05203b]/60 to-[#013047]/40 border border-zinc-800 shadow-2xl backdrop-blur-md">
        <h1 className="text-4xl md:text-5xl font-extrabold leading-tight text-white">
          Transforme reuniões em <span className="text-[#aee1ff]">requisitos claros</span>
        </h1>
        <p className="mt-4 text-slate-200 max-w-2xl mx-auto">
          Gere histórias, backlog e documentação automaticamente a partir de texto ou áudio. Entregue clareza para a equipe e velocidade para o projeto.
        </p>

        <div className="mt-8 flex items-center justify-center gap-4">
          <a href="#chat" className="px-6 py-3 rounded-full bg-[#004b8d] hover:bg-[#0066b3] text-white font-semibold shadow">Abrir Assistente</a>
          <Link to="/login" className="px-5 py-3 rounded-full border border-zinc-700 text-zinc-200 hover:bg-white/5">Entrar</Link>
        </div>
      </div>
    </motion.section>
  );
}

