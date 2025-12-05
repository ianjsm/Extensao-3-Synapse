import { useState, useEffect } from "react";

export default function TaskEditorModal({ task = {}, isEditing = false, onClose, onSave }) {
  const [description, setDescription] = useState(task.description || "");
  const [us_id, setUsId] = useState(task.us_id || "");
  const [us_title, setUsTitle] = useState(task.us_title || "");
  const [estimate, setEstimate] = useState(task.estimate ?? 1);

  useEffect(() => {
    setDescription(task.description || "");
    setUsId(task.us_id || "");
    setUsTitle(task.us_title || "");
    setEstimate(task.estimate ?? 1);
  }, [task]);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 animate-fadeIn">
        <h3 className="text-2xl font-bold mb-5 text-gray-800">
          {isEditing ? "Editar Tarefa" : "Adicionar Tarefa"}
        </h3>
        
        <div className="flex flex-col gap-4">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Descrição</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              className="w-full border border-gray-300 rounded-lg p-3 text-gray-800 focus:ring-2 focus:ring-blue-400 focus:outline-none"
              rows={4}
              placeholder="Descreva a tarefa..."
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">US ID</label>
            <input
              value={us_id}
              onChange={e => setUsId(e.target.value)}
              className="w-full border border-gray-300 rounded-lg p-3 text-gray-800 focus:ring-2 focus:ring-blue-400 focus:outline-none"
              placeholder="Ex: US-123"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Título</label>
            <input
              value={us_title}
              onChange={e => setUsTitle(e.target.value)}
              className="w-full border border-gray-300 rounded-lg p-3 text-gray-800 focus:ring-2 focus:ring-blue-400 focus:outline-none"
              placeholder="Ex: Implementar login"
            />
          </div>

          <div className="flex items-center gap-3">
            <label className="block text-sm font-semibold text-gray-700">Estimativa (pontos)</label>
            <input
              type="number"
              min={1}
              value={estimate}
              onChange={e => setEstimate(Number(e.target.value))}
              className="w-24 border border-gray-300 rounded-lg p-2 text-gray-800 focus:ring-2 focus:ring-blue-400 focus:outline-none"
            />
          </div>
        </div>

        {/* Ações */}
        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-5 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold rounded-lg transition"
          >
            Cancelar
          </button>
          <button
            onClick={() => onSave({ description, us_id, us_title, estimate })}
            className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow transition"
          >
            Salvar
          </button>
        </div>
      </div>
    </div>
  );
}

