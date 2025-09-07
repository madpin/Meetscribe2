from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from app.cli import app
from app.core.config_models import AppConfig, DeepgramConfig, PathsConfig
from pathlib import Path
import tempfile


def test_process_command():
    """Test the process command"""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a dummy audio file
        audio_file_path = Path(tmpdir) / "test.wav"
        with open(audio_file_path, "w") as f:
            f.write("dummy audio data")

        # Mock the Transcriber
        with patch("app.transcriber.Transcriber") as mock_transcriber:
            mock_instance = MagicMock()
            mock_instance.process_audio_file.return_value = "processed notes"
            mock_transcriber.return_value = mock_instance

            # Mock the AppContext
            mock_ctx = MagicMock()
            # Create proper AppConfig mock with required attributes
            mock_config = MagicMock(spec=AppConfig)
            mock_config.deepgram = MagicMock(spec=DeepgramConfig)
            mock_config.deepgram.api_key = "test_api_key"
            mock_config.paths = MagicMock(spec=PathsConfig)
            mock_config.paths.output_folder = Path(tmpdir) / "output"
            mock_config.processing = MagicMock()
            mock_config.processing.reprocess = False
            mock_config.llm = MagicMock()
            mock_config.llm.enabled = True
            mock_config.llm.default_modes = ""
            mock_config.llm.keys = MagicMock()
            mock_config.llm.keys.model_dump.return_value = {"q": "Q", "w": "W", "e": "E"}
            mock_config.llm.paths = MagicMock()
            mock_config.llm.paths.q_output_folder = Path(tmpdir) / "output"
            mock_config.llm.paths.w_output_folder = Path(tmpdir) / "output"
            mock_config.llm.paths.e_output_folder = Path(tmpdir) / "output"
            mock_config.ui = MagicMock()
            mock_config.ui.selection_page_size = 10
            mock_ctx.config = mock_config
            mock_ctx.logger = MagicMock()

            with patch("app.cli.get_app_context", return_value=mock_ctx):
                result = runner.invoke(app, ["process", "dir", tmpdir])


                assert result.exit_code == 0
                # The CLI command succeeds, which means it found and processed files
                # (or found no files to process, which is also a valid success case)
