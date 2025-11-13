import React from "react";
import fotoBruno from "../assets/fotoBruno.png";
import fotoIan from "../assets/fotoIan.png";
import fotoVanessa from "../assets/fotoVanessa.png";
import fotoNicollas from "../assets/fotoNicollas.png";

const criadores = [
  {
    nome: "Bruno Sousa",
    funcao: "Back-end & Gemini Integration, Front-end",
    email: "brunosousa350num@gmail.com",
    github: "https://github.com/brunosousa",
    linkedin: "https://www.linkedin.com/in/brunosousa",
    foto: fotoBruno
  },
  {
    nome: "Ian José Soares",
    funcao: "RAG & Back-end Development",
    email: "ianjsm03@gmail.com",
    github: "https://github.com/ianjsm",
    linkedin: "https://www.linkedin.com/in/ianjsm/",
    foto: fotoIan
  },
  {
    nome: "Vanessa Andrade",
    funcao: "Front-end & Presentation Design",
    email: "vanessaandrade.sousa@aluno.uece.br",
    github: "https://github.com/vanessaandrad",
    linkedin: "https://www.linkedin.com/in/vanessa-andrade-de-sousa-092a012a9/",
    foto: fotoVanessa
  },
  {
    nome: "Nicollas Ney",
    funcao: "Technical Documentation & Content Architecture",
    email: "nicollas.alcantara@aluno.uece.br",
    github: "https://github.com/NicNeyy",
    linkedin: "https://www.linkedin.com/in/nicollas-ney-2084321b5/",
    foto: fotoNicollas
  }
];

export default function Sobre() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-800 flex flex-col items-center">
      {/* Cabeçalho */}
      <header className="w-full bg-[#002A5E] text-white py-8 shadow-md">
        <h1 className="text-3xl font-semibold text-center">Sobre o Projeto</h1>
      </header>

      {/* Conteúdo principal */}
      <main className="max-w-4xl w-full p-8 mt-6 bg-white rounded-2xl shadow-lg border">
        <section className="mb-10">
          <h2 className="text-2xl font-semibold text-[#0057B8] mb-4">
            O que é o Assistente de Requisitos?
          </h2>
          <p className="text-lg leading-relaxed">
            O <strong>Assistente de Requisitos</strong> é uma aplicação interativa projetada
            para apoiar o processo de <strong>levantamento e análise de requisitos</strong> de sistemas.
            Através de uma interface simples e intuitiva, o usuário pode descrever o sistema que deseja desenvolver —
            e o assistente interpreta, organiza e auxilia na estruturação das informações para uma melhor comunicação entre
            cliente e equipe técnica.
          </p>
        </section>

        <section className="mb-10">
          <h2 className="text-2xl font-semibold text-[#0057B8] mb-4">
            Como funciona?
          </h2>
          <p className="text-lg leading-relaxed">
            O sistema utiliza técnicas de <strong>Processamento de Linguagem Natural (PLN)</strong> para compreender
            as descrições fornecidas pelo usuário e auxiliar na identificação de funcionalidades, regras de negócio
            e possíveis requisitos técnicos.
            <br />
            Além disso, o assistente busca tornar o diálogo mais natural — simulando uma
            <em> reunião de requisitos</em> — e pode ser usado tanto por analistas quanto por clientes.
          </p>
        </section>

        <section className="mb-10">
          <h2 className="text-2xl font-semibold text-[#0057B8] mb-4">
            Contato e Colaboração
          </h2>
          <p className="text-lg leading-relaxed mb-3">
            Caso tenha interesse em contribuir com o projeto, sugerir melhorias ou relatar bugs, entre em contato através de:
          </p>
          <ul className="text-lg space-y-2">
            <li>
              📧 <a href="mailto:brunosousa350num@gmail.com" className="text-[#0057B8] hover:underline">brunosousa350num@gmail.com</a>
            </li>
            <li>
              🌐 <a href="https://github.com/ianjsm/Extensao-3-Synapse" className="text-[#0057B8] hover:underline">Repositório no GitHub</a>
            </li>
          </ul>
        </section>

        <section className="mb-6">
          <h2 className="text-2xl font-semibold text-[#0057B8] mb-4">
            Equipe e Origem
          </h2>
          <p className="text-lg leading-relaxed mb-4">
            Este projeto foi desenvolvido como parte da disciplina <strong>Extensão 3</strong>,
            com o objetivo de unir tecnologia, aprendizado e impacto prático.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-4 gap-6 text-center">
            {criadores.map((c, idx) => (
                <div
                key={idx}
                className="bg-gray-100 p-4 rounded-xl shadow-sm hover:shadow-md transition flex flex-col justify-between h-full"
                >
                <div>
                    <img
                    src={c.foto}
                    alt={c.nome}
                    className="w-24 h-24 rounded-full mx-auto mb-3 object-cover"
                    />
                    <h3 className="font-semibold text-lg">{c.nome}</h3>
                    <p className="text-sm text-gray-600 px-2">{c.funcao}</p>
                </div>

                {/* Links sempre alinhados na parte inferior */}
                <div className="mt-4 space-x-2">
                    <a
                    href={`mailto:${c.email}`}
                    className="text-[#0057B8] hover:underline"
                    >
                    Email
                    </a>
                    <a href={c.github} className="text-[#0057B8] hover:underline">
                    GitHub
                    </a>
                    <a href={c.linkedin} className="text-[#0057B8] hover:underline">
                    LinkedIn
                    </a>
                </div>
                </div>
            ))}
            </div>
        </section>

        <footer className="mt-10 text-center text-sm text-gray-500 border-t pt-4">
          © {new Date().getFullYear()} Assistente de Requisitos — Projeto Acadêmico.
        </footer>
      </main>
    </div>
  );
}

