import { ExtractedGarmentsGrid } from "@/components/tryoff/extracted-garments-grid";

export default function ExtractedGarmentsPage() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Prendas Extraídas</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Prendas extraídas de tus imágenes con TryOff
        </p>
      </div>

      <ExtractedGarmentsGrid />
    </div>
  );
}
