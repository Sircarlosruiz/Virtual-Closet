# Workflows multi-agente

Contenido canónico del pipeline **Orquestador → Planner → Executor → Auditor**.

| Archivo | Rol |
|---------|-----|
| `orchestrator.md` | Coordina el ciclo automático |
| `planner.md` | Planificación técnica (sin código) |
| `executor.md` | Implementación paso a paso |
| `auditor.md` | Auditoría post-ejecución |

OpenCode carga estos archivos vía symlinks en `.opencode/agents/*-agent.md`.
