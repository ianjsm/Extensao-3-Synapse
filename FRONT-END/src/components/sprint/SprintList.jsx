export default function SprintList({ sprints = [], onSelect, selectedId, onDelete }) {
  return (
    <div className="bg-gray-50 p-4 rounded-2xl shadow-lg max-w-md mx-auto">
      {sprints.length === 0 && (
        <p className="text-sm text-gray-500 text-center py-4">
          Nenhum planejamento ainda.
        </p>
      )}
      <div className="flex flex-col gap-3">
        {sprints.map(s => (
          <div
            key={s.id}
            className={`flex justify-between items-center p-4 rounded-xl cursor-pointer transition-shadow ${
              selectedId === s.id
                ? "bg-blue-50 shadow-inner"
                : "bg-white hover:shadow-md"
            }`}
          >
            <div onClick={() => onSelect(s.id)} className="flex flex-col">
              <div className="font-semibold text-gray-800 text-lg">{s.sprint_name}</div>
              <div className="text-xs text-gray-500 mt-1">{new Date(s.created_at).toLocaleString()}</div>
              <div className="text-xs text-gray-400 mt-1">{s.tasks.length} tasks</div>
            </div>
            <div>
              <button
                onClick={() => onDelete(s.id)}
                className="text-red-500 hover:text-red-700 font-semibold text-sm"
              >
                Excluir
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
