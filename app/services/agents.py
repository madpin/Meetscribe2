"""
Agent-based notes generation service stubs.

This module provides placeholder interfaces and classes for future
agent-based implementations (e.g., Glean, MCP). These will eventually
replace or complement the LLMNotesGenerator with more sophisticated
agent workflows.

Note: This is currently a stub file for future development.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Set, Protocol
from app.core.config_models import AppConfig


class NotesEngine(Protocol):
    """
    Protocol defining the interface for notes generation engines.

    This protocol ensures that both LLM-based and agent-based implementations
    have the same interface, allowing them to be swapped seamlessly.
    """

    def generate_for_modes(
        self,
        content: str,
        modes: Set[str],
        file_stem: str,
        base_output: Path,
        reprocess: bool
    ) -> Dict[str, Path]:
        """
        Generate notes for the specified modes from transcription content.

        Args:
            content: The transcription content to process
            modes: Set of modes ('Q', 'W', 'E') to generate
            file_stem: Base filename stem (without extension)
            base_output: Default output folder
            reprocess: Whether to overwrite existing files

        Returns:
            Dictionary mapping mode letters to generated file paths
        """
        ...


# TODO: Implement when integrating with Glean
class GleanNotesGenerator:
    """
    Placeholder for Glean-based agent implementation.

    Glean is a framework for building AI agents with complex workflows,
    tool usage, and multi-step reasoning. This would provide more
    sophisticated note generation than simple LLM prompting.
    """
    pass


# TODO: Implement when integrating with MCP (Model Context Protocol)
class MCPNotesGenerator:
    """
    Placeholder for MCP-based agent implementation.

    MCP (Model Context Protocol) allows for more sophisticated interactions
    between AI models and tools, potentially providing better context
    awareness and tool integration for meeting note generation.
    """
    pass


# Example of how to extend the current LLMNotesGenerator to implement the protocol
def create_notes_engine(config: AppConfig, logger) -> NotesEngine:
    """
    Factory function to create the appropriate notes engine.

    Currently returns LLMNotesGenerator, but can be extended to return
    agent-based implementations based on configuration.

    Args:
        config: Application configuration
        logger: Logger instance

    Returns:
        NotesEngine implementation
    """
    # For now, always use LLM-based implementation
    from .llm_notes import LLMNotesGenerator
    return LLMNotesGenerator(config.llm, logger)

    # Future: Add logic to choose based on config
    # if config.llm.agent_framework == "glean":
    #     return GleanNotesGenerator(config, logger)
    # elif config.llm.agent_framework == "mcp":
    #     return MCPNotesGenerator(config, logger)
    # else:
    #     return LLMNotesGenerator(config.llm, logger)
