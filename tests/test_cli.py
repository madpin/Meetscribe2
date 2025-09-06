from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from app.cli import app
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
            mock_ctx.config = {
                "paths": {"output_folder": str(Path(tmpdir) / "output")}
            }
            mock_ctx.logger = MagicMock()

            with patch("app.cli.get_app_context", return_value=mock_ctx):
                result = runner.invoke(app, ["process", "dir", tmpdir])

                assert result.exit_code == 0
                mock_instance.process_audio_file.assert_called_once_with(
                    audio_file_path
                )

                output_file_path = Path(tmpdir) / "output" / "test.txt"
                assert output_file_path.exists()
                with open(output_file_path, "r") as f:
                    assert f.read() == "processed notes"
