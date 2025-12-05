import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import SprintList from "./SprintList";
import SprintDetail from "./SprintDetail";
import AiInstructionSidebar from "./AiInstructionSidebar";

export default function SprintPlannerView({ initialTasks }) {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  // Carrega sprints existentes do localStorage
  const localStored = JSON.parse(localStorage.getItem("sprintPlans_v1") || "[]");

  // Se não existir nenhuma sprint salva, cria uma sprint inicial vinda do backend
  const initialSprint =
    localStored.length === 0
      ? [
          {
            id: crypto.randomUUID(),
            sprint_name: "Sprint Inicial (Gerada pelo Planejador)",
            created_at: new Date().toISOString(),
            tasks: initialTasks, // <<< tasks vindas do backend
          },
        ]
      : localStored;

  const [sprintPlans, setSprintPlans] = useState(initialSprint);

  // Sprint selecionada
  const defaultSelected =
    searchParams.get("sprintId") || initialSprint[0]?.id || null;

  const [selectedSprintId, setSelectedSprintId] = useState(defaultSelected);

  // Persistência no localStorage
  useEffect(() => {
    localStorage.setItem("sprintPlans_v1", JSON.stringify(sprintPlans));
  }, [sprintPlans]);

  // CRUD
  const handleDeleteSprint = (id) => {
    setSprintPlans((prev) => prev.filter((s) => s.id !== id));

    if (selectedSprintId === id) {
      const next = sprintPlans.find((s) => s.id !== id);
      setSelectedSprintId(next?.id ?? null);
    }
  };

  const handleUpdateSprint = (updated) => {
    setSprintPlans((prev) =>
      prev.map((s) => (s.id === updated.id ? updated : s))
    );
  };

  const handleAddSprint = (sprint) => {
    setSprintPlans((prev) => [sprint, ...prev]);
    setSelectedSprintId(sprint.id);
    navigate(`/sprint-planner?sprintId=${sprint.id}`);
  };

  const selectedSprint =
    sprintPlans.find((s) => s.id === selectedSprintId) || null;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex gap-6">
        {/* Sidebar esquerda com lista de sprints */}
        <div className="w-64">
          <div className="mb-6 flex items-center justify-between">
            <button
              onClick={() => navigate("/chat")}
              className="flex items-center gap-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-800 rounded-lg shadow transition"
            >
              ← Voltar
            </button>
            <h2 className="text-xl font-bold text-black">Histórico Sprints</h2>

            <button
              onClick={() => {
                const newSprint = {
                  id: crypto.randomUUID(),
                  sprint_name: `Sprint ${sprintPlans.length + 1}`,
                  created_at: new Date().toISOString(),
                  tasks: [],
                };
                handleAddSprint(newSprint);
              }}
              className="text-sm bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded"
            >
              + Nova
            </button>
          </div>

          <SprintList
            sprints={sprintPlans}
            onSelect={setSelectedSprintId}
            selectedId={selectedSprintId}
            onDelete={handleDeleteSprint}
          />
        </div>

        {/* Conteúdo central: detalhes da sprint */}
        <div className="flex-1">
          {selectedSprint ? (
            <SprintDetail
              sprint={selectedSprint}
              onUpdate={handleUpdateSprint}
              onDelete={() => handleDeleteSprint(selectedSprint.id)}
            />
          ) : (
            <div className="p-6 bg-white rounded shadow">
              Selecione uma sprint à esquerda ou crie uma nova.
            </div>
          )}
        </div>

        {/* Sidebar da IA */}
        <div className="w-96">
          <AiInstructionSidebar
            sprint={selectedSprint}
            onUpdateSprint={handleUpdateSprint}
          />
        </div>
      </div>
    </div>
  );
}
