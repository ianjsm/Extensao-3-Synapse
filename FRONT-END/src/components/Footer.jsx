import React from "react";

export default function Footer() {
  return (
    <footer className="mt-12 py-6 text-zinc-400 border-t border-zinc-800">
      <div className="max-w-6xl mx-auto px-6 text-center">
        © {new Date().getFullYear()} Synapse — Projeto de Extensão · UECE
      </div>
    </footer>
  );
}

