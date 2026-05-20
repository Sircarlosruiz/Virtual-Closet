"use client";

interface UploadProgressProps {
  progress: number;
  status: "idle" | "uploading" | "done" | "error";
}

export function UploadProgress({ progress, status }: UploadProgressProps) {
  const statusText = {
    idle: "Preparando...",
    uploading: "Subiendo imagen...",
    done: "Completado",
    error: "Error en la subida",
  };

  const statusColor = {
    idle: "bg-zinc-300",
    uploading: "bg-blue-500",
    done: "bg-green-500",
    error: "bg-red-500",
  };

  return (
    <div className="w-full space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-zinc-600 dark:text-zinc-400">
          {statusText[status]}
        </span>
        {status === "uploading" && (
          <span className="text-zinc-500">{Math.round(progress)}%</span>
        )}
      </div>
      <div className="h-2 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${statusColor[status]}`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
