import { JobHistoryList } from "@/components/vton/JobHistoryList";

export default function JobsPage() {
  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Historial de Generaciones</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Revisa tus pruebas virtuales anteriores
        </p>
      </div>

      <JobHistoryList />
    </div>
  );
}
