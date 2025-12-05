import { useState } from "react";
import TaskEditorModal from "./TaskEditorModal";

export default function SprintDetail({ sprint, onUpdate, onDelete }) {
  const [editingTask, setEditingTask] = useState(null);
  const [statusMessage, setStatusMessage] = useState("");
  const [working, setWorking] = useState(false);

  const showStatus = (msg, duration = 3000) => {
    setStatusMessage(msg);
    setTimeout(() => setStatusMessage(""), duration);
  };

  const updateTask = (taskId, changes) => {
    const updated = {
      ...sprint,
      tasks: sprint.tasks.map((t) => (t.id === taskId ? { ...t, ...changes } : t)),
    };
    onUpdate(updated);
  };

  const addTask = (task) => {
    const newTask = { id: crypto.randomUUID(), ...task };
    const updated = { ...sprint, tasks: [...sprint.tasks, newTask] };
    onUpdate(updated);
  };

  const removeTask = (taskId) => {
    const updated = { ...sprint, tasks: sprint.tasks.filter((t) => t.id !== taskId) };
    onUpdate(updated);
  };

  const replanWithAI = async (instruction = "Replanejar para reduzir complexidade e equilibrar estimativas") => {
    setWorking(true);
    showStatus("🔄 Replanejando com IA...");
    try {
      const res = await fetch("http://127.0.0.1:8000/sprint/replan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_tasks: sprint.tasks, instruction }),
      });
      if (!res.ok) throw new Error("Falha no replanejamento");
      const data = await res.json();
      const updated = { ...sprint, tasks: data.tasks || [] };
      onUpdate(updated);
      showStatus("✅ Sprint replanejada com sucesso!", 2000);
    } catch (err) {
      console.error(err);
      showStatus("❌ Erro ao replanejar com IA", 2000);
    } finally {
      setWorking(false);
    }
  };

  const sendToJira = async () => {
    setWorking(true);
    showStatus("📤 Enviando ao Jira...");
    try {
      const res = await fetch("http://127.0.0.1:8000/sprint/send_sprint_to_jira", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(sprint),
      });
      const data = await res.json();
      if (res.ok) {
        showStatus(`✅ ${data.created_issues?.length || 0} issues criadas no Jira`, 2000);
      } else {
        console.error(data);
        showStatus("❌ Erro ao enviar para o Jira", 2000);
      }
    } catch (err) {
      console.error(err);
      showStatus("❌ Erro de conexão ao enviar para Jira", 2000);
    } finally {
      setWorking(false);
    }
  };

  return (
    <div className="bg-gray-50 p-6 rounded-xl shadow-lg max-w-6xl mx-auto relative">
      {/* Status Message fixo e moderno */}
      {statusMessage && (
        <div className="fixed top-6 right-6 bg-gray-900 text-white px-5 py-3 rounded-lg shadow-lg flex items-center gap-2 animate-fadeIn z-50">
          <span>{statusMessage}</span>
        </div>
      )}

      {/* Header da Sprint */}
      <div className="flex justify-between items-center mb-6 flex-wrap gap-3">
        <div>
          <h3 className="text-2xl font-extrabold text-gray-800">{sprint.sprint_name}</h3>
          <p className="text-sm text-gray-500 mt-1">Criado em {new Date(sprint.created_at).toLocaleString()}</p>
        </div>
        <div className="flex gap-3 flex-wrap">
          <button
            onClick={() => replanWithAI()}
            disabled={working}
            className={`flex items-center gap-2 px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-white font-semibold rounded-lg shadow transition ${
              working ? "opacity-60 cursor-not-allowed" : ""
            }`}
          >
            {working ? "⏳ Processando..." : "Replanejar com IA"}
          </button>
          <button
            onClick={sendToJira}
            disabled={working}
            className={`flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg shadow transition ${
              working ? "opacity-60 cursor-not-allowed" : ""
            }`}
          >
            {working ? "⏳ Processando..." : "Enviar Jira"}
          </button>
          <button
            onClick={onDelete}
            className={`flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 text-white font-semibold rounded-lg shadow transition" ${
              working ? "opacity-60 cursor-not-allowed" : ""
            }`}
          >       
            {working ? "Excluir Sprint" : "Excluir Sprint"}
          </button>
        </div>
      </div>

      {/* Lista de Tasks */}
      <div className="grid md:grid-cols-2 gap-4 mb-6">
        {sprint.tasks.map((t) => (
          <div key={t.id} className="bg-white p-5 rounded-xl shadow hover:shadow-lg transition-shadow relative">
            <div className="flex justify-between items-start">
              <div>
                <h4 className="text-lg font-semibold text-gray-800">{t.us_title || "Sem título"}</h4>
                <p className="text-gray-600 mt-1">{t.description}</p>
                <p className="text-sm text-gray-400 mt-1">ID: {t.us_id || "-"}</p>
                <p className="text-sm text-gray-400 mt-1">Estimativa: {t.estimate ?? "-"}</p>
              </div>
              <div className="flex flex-col gap-2 ml-4">
                <button
                  onClick={() => setEditingTask({ ...t, isEditing: true })}
                  className="w-10 h-10 flex items-center justify-center rounded-full bg-blue-100 hover:bg-blue-200 text-blue-600 shadow-sm hover:shadow-md transition"
                  title="Editar tarefa"
                >
                  ✏
                </button>
                <button
                  onClick={() => removeTask(t.id)}
                  className="w-10 h-10 flex items-center justify-center rounded-full bg-red-100 hover:bg-red-200 text-red-600 hover:text-red-800 shadow-sm hover:shadow-md transition"
                  title="Excluir tarefa"
                >
                  🗑
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Adicionar Task */}
      <div className="flex justify-center">
        <button
          onClick={() => setEditingTask({})}
          className="px-5 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-lg transition-colors flex items-center gap-2"
        >
          + Adicionar Tarefa
        </button>
      </div>

      {/* Modal */}
      {editingTask !== null && (
        <TaskEditorModal
          task={editingTask}
          isEditing={editingTask?.isEditing ?? false}
          onClose={() => setEditingTask(null)}
          onSave={(payload) => {
            if (editingTask?.isEditing) {
              updateTask(editingTask.id, payload);
            } else {
              addTask(payload);
            }
            setEditingTask(null);
          }}
        />
      )}
    </div>
  );
}



