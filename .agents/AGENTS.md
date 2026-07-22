# EchoMind Workspace Rules

## Post-Phase Graphify Update

After every phase completion (after the git commit), run:

```bash
graphify . --update --code-only
graphify cluster-only . --code-only
```

This keeps the knowledge graph current. Use `--code-only` to avoid LLM API key requirements.
