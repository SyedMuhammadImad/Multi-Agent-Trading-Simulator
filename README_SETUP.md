# NexusAI V2 Package — Installation Order

1. Copy `NEXUSAI_V2_SPECIFICATION.md`, `AGENTS.md`, and `knowledge/` into the NexusAI repository root.
2. Commit them on the current controlled-rebuild branch or a dedicated governance branch.
3. In Obsidian choose **Open folder as vault** and select `NexusAI/knowledge/`.
4. Review `knowledge/DECISIONS.md` and resolve only decisions required by the current phase.
5. Mark P0 complete only after its exit criteria pass.
6. Configure Astra/Codex to read `AGENTS.md` before each task.
7. Development then proceeds one roadmap task at a time: plan -> implement -> test -> evidence -> vault update -> commit.
8. Configure the nightly audit only after the vault is in the repository. The nightly job is read-only and writes a dated audit report; normal task completion updates the vault immediately.

Do not copy the old Master Prompt into the vault as current authority. Keep it as historical/reference material if desired.
