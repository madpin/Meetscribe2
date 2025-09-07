"""
LLM-based notes generation service.

This module provides the LLMNotesGenerator class that uses LangChain
to generate different types of meeting notes (Q, W, E) from transcription text.
"""

from pathlib import Path
from typing import Set, Dict
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from app.core.config_models import LLMConfig
from app.core.utils import ensure_directory_exists


class LLMNotesGenerator:
    """
    Service for generating LLM-powered meeting notes.

    This service uses LangChain with ChatOpenAI to generate three types of notes:
    - Q: Executive summary
    - W: Holistic analysis
    - E: Actionable tasks

    The service is designed to be easily replaceable with agent-based implementations
    in the future (e.g., Glean, MCP).
    """

    def __init__(self, cfg: LLMConfig, logger):
        """
        Initialize the LLM notes generator.

        Args:
            cfg: LLM configuration containing model, prompts, and API settings
            logger: Logger instance for status and error messages
        """
        self.cfg = cfg
        self.logger = logger
        self.llm = ChatOpenAI(
            model=cfg.model,
            temperature=cfg.temperature,
            api_key=cfg.api_key or None,
            base_url=cfg.base_url or None,
        )

    def _resolve_output_folder(self, mode: str, default_base: Path) -> Path:
        """
        Resolve the output folder for a given mode.

        Args:
            mode: The note mode ('Q', 'W', or 'E')
            default_base: Default output folder to use if mode-specific folder not set

        Returns:
            Path to the resolved output folder
        """
        mapping = {
            "Q": self.cfg.paths.q_output_folder,
            "W": self.cfg.paths.w_output_folder,
            "E": self.cfg.paths.e_output_folder,
        }
        folder_path = mapping.get(mode)
        if not folder_path or not str(folder_path).strip():
            # Use the default base folder if not set or empty
            return Path(default_base)

        # Convert to Path and check if absolute or relative
        p = Path(folder_path)
        if p.is_absolute():
            # Return absolute path as-is
            return p
        else:
            # Join relative path with default_base and resolve
            return (Path(default_base) / p).resolve()

    def _build_prompt(self, mode: str, content: str) -> str:
        """
        Build the complete prompt for a given mode and content.

        Args:
            mode: The note mode ('Q', 'W', or 'E')
            content: The transcription content to process

        Returns:
            Complete prompt string with system instructions and content
        """
        prompt_map = {"Q": self.cfg.prompts.q, "W": self.cfg.prompts.w, "E": self.cfg.prompts.e}
        user_prompt = prompt_map[mode]
        return f"You are an expert meeting assistant.\n\n{user_prompt}\n\nUse the meeting content below:\n---\n{content}\n---\nReturn only the notes."

    def generate_for_modes(self, content: str, modes: Set[str], file_stem: str, base_output: Path, reprocess: bool) -> Dict[str, Path]:
        """
        Generate LLM notes for the specified modes.

        Args:
            content: The transcription content to process
            modes: Set of modes to generate ('Q', 'W', 'E')
            file_stem: Base filename stem (without extension)
            base_output: Default output folder
            reprocess: Whether to overwrite existing files

        Returns:
            Dictionary mapping mode letters to generated file paths
        """
        outputs: Dict[str, Path] = {}

        for mode in sorted({m.upper() for m in modes}):
            try:
                folder = self._resolve_output_folder(mode, base_output)
                ensure_directory_exists(folder, self.logger)
                target = folder / f"{file_stem}.{mode}.txt"

                if not reprocess and target.exists():
                    self.logger.info(f"Skipping LLM {mode} for {file_stem}: {target} already exists")
                    outputs[mode] = target
                    continue

                prompt_text = self._build_prompt(mode, content)
                tpl = ChatPromptTemplate.from_messages([("human", "{prompt}")])
                chain = tpl | self.llm
                resp = chain.invoke({"prompt": prompt_text})
                text = resp.content if hasattr(resp, "content") else str(resp)

                target.write_text(text)
                self.logger.info(f"LLM {mode} notes saved to {target}")
                outputs[mode] = target

            except Exception as e:
                # Provide detailed error information for debugging
                error_type = type(e).__name__
                error_msg = str(e)
                self.logger.error(f"Failed to generate LLM {mode} for {file_stem}: {error_type}: {error_msg}")

                # Log additional context for common errors
                if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                    self.logger.error(f"Connection details: model={self.cfg.model}, base_url={self.cfg.base_url}, api_key={'***' if self.cfg.api_key else 'None'}")
                elif "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
                    self.logger.error(f"Authentication issue: api_key={'***' if self.cfg.api_key else 'None'}, base_url={self.cfg.base_url}")
                elif "model" in error_msg.lower():
                    self.logger.error(f"Model issue: model={self.cfg.model}, available models may vary by provider")

        return outputs
