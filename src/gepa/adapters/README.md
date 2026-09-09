# GEPA Adapters

> GEPA 🤝 Any Framework

This directory provides the interface to allow GEPA to plug into systems and frameworks of your choice! GEPA can interface with any system consisting of text components, by implementing `GEPAAdapter` in [../core/adapter.py](../core/adapter.py).

Currently, GEPA has the following adapters:
- [Default Adapter](./default_adapter/): Single-turn LLM prompt optimization via the system prompt.
- [Confidence Adapter](./confidence_adapter/): Logprob-aware classification optimization for structured JSON outputs.
- [Generic RAG Adapter](./generic_rag_adapter/): Vector store-agnostic RAG pipeline optimization.
- [MCP Adapter](./mcp_adapter/): MCP tool descriptions and system prompt optimization.
- [TerminalBench Adapter](./terminal_bench_adapter/): Terminal-use agent prompt optimization.
- [AnyMaths Adapter](./anymaths_adapter/): Mathematical problem-solving with litellm and ollama.

For [DSPy](https://dspy.ai/) program optimization, use [`dspy.GEPA`](https://dspy.ai/tutorials/gepa_ai_program/) in the DSPy framework.

If there are any frameworks you would like GEPA integrated into, please create an issue or PR!
