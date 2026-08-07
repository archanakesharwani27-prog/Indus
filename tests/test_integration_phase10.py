"""
Integration tests for Phase 10: Continuous Voice Assistant with Real APIs.
"""

import pytest
import os
import sys
import time
from unittest.mock import Mock, patch, MagicMock, PropertyMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Reset global consolidator before each test
import core.memory.consolidation as consolidation_module

from indus_phase10 import IndusVoiceAssistant
from core.voice.gemini_live import GeminiLiveClient, create_gemini_live_client
from core.voice.groq_tts import TTSClient, create_tts_client
from core.multiagent import create_orchestrator, AgentRole
from core.llm_provider import LLMProvider
from providers.mock_provider import MockProvider


@pytest.fixture(autouse=True)
def reset_consolidator():
    """Reset global consolidator state between tests."""
    consolidation_module._consolidator = None
    yield
    consolidation_module._consolidator = None


class TestPhase10VoiceAssistant:
    """Test the Phase 10 continuous voice assistant."""

    @pytest.fixture
    def mock_llm(self):
        return MockProvider()

    def test_assistant_initialization(self, mock_llm):
        """Test that the assistant initializes correctly."""
        with patch.dict(os.environ, {
            "NVIDIA_API_KEY": "test-key",
            "GEMINI_API_KEY": "test-gemini-key",
            "GROQ_API_KEY": "test-groq-key",
        }):
            with patch("indus_phase10.NVIDIAProvider", return_value=mock_llm):
                with patch("indus_phase10.create_tts_client", return_value=Mock()):
                    with patch("indus_phase10.create_gemini_live_client", return_value=Mock()):
                        assistant = IndusVoiceAssistant()
                        assert assistant is not None
                        assert assistant.engine is not None
                        assert assistant.memory is not None
                        assert assistant.orchestrator is not None
                        assistant.stop()

    def test_llm_provider_initialization(self, mock_llm):
        """Test LLM provider initialization from environment."""
        with patch.dict(os.environ, {"PROVIDER": "nvidia", "NVIDIA_API_KEY": "test"}):
            with patch("indus_phase10.NVIDIAProvider", return_value=mock_llm):
                assistant = IndusVoiceAssistant()
                assert assistant.llm_provider is not None
                assistant.stop()

    def test_tts_initialization_groq(self, mock_llm):
        """Test TTS initialization with Groq."""
        mock_tts = Mock()
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-groq-key"}):
            with patch("indus_phase10.NVIDIAProvider", return_value=mock_llm):
                with patch("indus_phase10.create_tts_client", return_value=mock_tts):
                    assistant = IndusVoiceAssistant()
                    assert assistant.tts == mock_tts
                    assistant.stop()

    def test_tts_initialization_edge_fallback(self, mock_llm):
        """Test TTS falls back to Edge TTS when Groq unavailable."""
        mock_tts = Mock()
        with patch.dict(os.environ, {}, clear=True):
            with patch("indus_phase10.NVIDIAProvider", return_value=mock_llm):
                with patch("indus_phase10.create_tts_client", side_effect=[Exception("Groq failed"), mock_tts]):
                    assistant = IndusVoiceAssistant()
                    assert assistant.tts == mock_tts
                    assistant.stop()

    def test_gemini_live_initialization(self, mock_llm):
        """Test Gemini Live client initialization."""
        mock_gemini = Mock()
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-gemini-key"}):
            with patch("indus_phase10.NVIDIAProvider", return_value=mock_llm):
                with patch("indus_phase10.create_tts_client", return_value=Mock()):
                    with patch("indus_phase10.create_gemini_live_client", return_value=mock_gemini):
                        assistant = IndusVoiceAssistant()
                        assert assistant.gemini_live == mock_gemini
                        assistant.stop()

    def test_gemini_live_initialization_no_key(self, mock_llm):
        """Test Gemini Live not initialized when no API key."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("indus_phase10.NVIDIAProvider", return_value=mock_llm):
                with patch("indus_phase10.create_tts_client", return_value=Mock()):
                    with patch("indus_phase10.create_gemini_live_client") as mock_create:
                        assistant = IndusVoiceAssistant()
                        assert assistant.gemini_live is None
                        mock_create.assert_not_called()
                        assistant.stop()

    def test_speak_method(self, mock_llm):
        """Test speak method with TTS."""
        mock_tts = Mock()
        with patch.dict(os.environ, {"GROQ_API_KEY": "test"}):
            with patch("indus_phase10.NVIDIAProvider", return_value=mock_llm):
                with patch("indus_phase10.create_tts_client", return_value=mock_tts):
                    with patch("indus_phase10.create_gemini_live_client", return_value=Mock()):
                        assistant = IndusVoiceAssistant()
                        assistant.speak("Hello world")
                        mock_tts.speak.assert_called_once_with("Hello world")
                        assistant.stop()

    def test_speak_method_no_tts(self, mock_llm, capsys):
        """Test speak method without TTS prints to console."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("indus_phase10.NVIDIAProvider", return_value=mock_llm):
                with patch("indus_phase10.create_tts_client", side_effect=Exception("No TTS")):
                    with patch("indus_phase10.create_gemini_live_client", return_value=Mock()):
                        assistant = IndusVoiceAssistant()
                        assistant.speak("Hello world")
                        captured = capsys.readouterr()
                        assert "Hello world" in captured.out
                        assistant.stop()

    def test_execute_with_voice_confirmation_simple(self, mock_llm):
        """Test command execution with regular chat engine."""
        with patch.dict(os.environ, {"NVIDIA_API_KEY": "test"}):
            with patch("indus_phase10.NVIDIAProvider", return_value=mock_llm):
                with patch("indus_phase10.create_tts_client", return_value=Mock()):
                    with patch("indus_phase10.create_gemini_live_client", return_value=Mock()):
                        assistant = IndusVoiceAssistant()
                        # Mock the engine respond method
                        assistant.engine.respond = Mock(return_value="Done")
                        assistant.speak = Mock()
                        
                        result = assistant._execute_with_voice_confirmation("open notepad")
                        
                        assert result == "Done"
                        assistant.engine.respond.assert_called_once_with("open notepad")
                        assistant.speak.assert_called_once_with("Done")
                        assistant.stop()

    def test_execute_with_voice_confirmation_multiagent(self, mock_llm):
        """Test command execution with multi-agent orchestrator."""
        mock_orchestrator = Mock()
        mock_orchestrator.run_workflow.return_value = {
            "results": {"verify": {"message": "Task completed"}},
            "error": None
        }
        
        with patch.dict(os.environ, {"NVIDIA_API_KEY": "test"}):
            with patch("indus_phase10.NVIDIAProvider", return_value=mock_llm):
                with patch("indus_phase10.create_tts_client", return_value=Mock()):
                    with patch("indus_phase10.create_gemini_live_client", return_value=Mock()):
                        assistant = IndusVoiceAssistant()
                        assistant.orchestrator = mock_orchestrator
                        assistant.speak = Mock()
                        
                        result = assistant._execute_with_voice_confirmation("plan a trip to Japan")
                        
                        assert "Task completed" in result
                        mock_orchestrator.run_workflow.assert_called_once()
                        assistant.stop()

    def test_execute_with_voice_confirmation_error(self, mock_llm):
        """Test command execution handles errors."""
        with patch.dict(os.environ, {"NVIDIA_API_KEY": "test"}):
            with patch("indus_phase10.NVIDIAProvider", return_value=mock_llm):
                with patch("indus_phase10.create_tts_client", return_value=Mock()):
                    with patch("indus_phase10.create_gemini_live_client", return_value=Mock()):
                        assistant = IndusVoiceAssistant()
                        assistant.engine.respond = Mock(side_effect=Exception("Test error"))
                        assistant.speak = Mock()
                        
                        result = assistant._execute_with_voice_confirmation("test command")
                        
                        assert "Error executing command" in result
                        assistant.speak.assert_called()
                        assistant.stop()

    def test_handle_transcription(self, mock_llm):
        """Test transcription handling."""
        with patch.dict(os.environ, {"NVIDIA_API_KEY": "test"}):
            with patch("indus_phase10.NVIDIAProvider", return_value=mock_llm):
                with patch("indus_phase10.create_tts_client", return_value=Mock()):
                    with patch("indus_phase10.create_gemini_live_client", return_value=Mock()):
                        assistant = IndusVoiceAssistant()
                        assistant._execute_with_voice_confirmation = Mock(return_value="Done")
                        
                        assistant._handle_transcription("open notepad")
                        
                        assistant._execute_with_voice_confirmation.assert_called_once_with("open notepad")
                        assistant.stop()

    def test_handle_transcription_exit(self, mock_llm):
        """Test transcription handling for exit commands."""
        with patch.dict(os.environ, {"NVIDIA_API_KEY": "test"}):
            with patch("indus_phase10.NVIDIAProvider", return_value=mock_llm):
                with patch("indus_phase10.create_tts_client", return_value=Mock()):
                    with patch("indus_phase10.create_gemini_live_client", return_value=Mock()):
                        assistant = IndusVoiceAssistant()
                        assistant.speak = Mock()
                        
                        assistant._handle_transcription("exit")
                        
                        assert assistant.running is False
                        assistant.speak.assert_called_with("Goodbye!")
                        assistant.stop()

    def test_handle_transcription_duplicate(self, mock_llm):
        """Test that duplicate transcriptions are ignored."""
        with patch.dict(os.environ, {"NVIDIA_API_KEY": "test"}):
            with patch("indus_phase10.NVIDIAProvider", return_value=mock_llm):
                with patch("indus_phase10.create_tts_client", return_value=Mock()):
                    with patch("indus_phase10.create_gemini_live_client", return_value=Mock()):
                        assistant = IndusVoiceAssistant()
                        assistant._execute_with_voice_confirmation = Mock()
                        
                        # Send same transcription twice
                        assistant._handle_transcription("open notepad")
                        assistant._handle_transcription("open notepad")
                        
                        # Should only execute once
                        assert assistant._execute_with_voice_confirmation.call_count == 1
                        assistant.stop()

    def test_handle_transcription_short(self, mock_llm):
        """Test that very short transcriptions are ignored."""
        with patch.dict(os.environ, {"NVIDIA_API_KEY": "test"}):
            with patch("indus_phase10.NVIDIAProvider", return_value=mock_llm):
                with patch("indus_phase10.create_tts_client", return_value=Mock()):
                    with patch("indus_phase10.create_gemini_live_client", return_value=Mock()):
                        assistant = IndusVoiceAssistant()
                        assistant._execute_with_voice_confirmation = Mock()
                        
                        assistant._handle_transcription("hi")
                        
                        assistant._execute_with_voice_confirmation.assert_not_called()
                        assistant.stop()

    def test_run_wake_word_mode(self, mock_llm):
        """Test wake word mode initialization."""
        with patch.dict(os.environ, {"NVIDIA_API_KEY": "test"}):
            with patch("indus_phase10.NVIDIAProvider", return_value=mock_llm):
                with patch("indus_phase10.create_tts_client", return_value=Mock()):
                    with patch("indus_phase10.create_gemini_live_client", return_value=None):
                        with patch("core.voice.wake_word.SimpleWakeWordDetector") as mock_wake:
                            mock_wake_instance = Mock()
                            mock_wake.return_value = mock_wake_instance
                            
                            assistant = IndusVoiceAssistant()
                            assistant.gemini_live = None
                            assistant.run_wake_word_mode()
                            
                            mock_wake_instance.start.assert_called_once()
                            assistant.stop()

    def test_stop_method(self, mock_llm):
        """Test stop method cleans up resources."""
        with patch.dict(os.environ, {"NVIDIA_API_KEY": "test"}):
            with patch("indus_phase10.NVIDIAProvider", return_value=mock_llm):
                with patch("indus_phase10.create_tts_client", return_value=Mock()):
                    with patch("indus_phase10.create_gemini_live_client", return_value=Mock()):
                        assistant = IndusVoiceAssistant()
                        assistant.engine.shutdown = Mock()
                        
                        assistant.stop()
                        
                        assert assistant.running is False
                        assistant.engine.shutdown.assert_called_once()


class TestPhase10GeminiLive:
    """Test Gemini Live integration."""

    @pytest.fixture
    def mock_gemini_client(self):
        client = Mock(spec=GeminiLiveClient)
        client.voice = "Aoede"
        client.system_instruction = "You are Zoya"
        client.proxy_url = None
        return client

    def test_create_gemini_live_client(self):
        """Test Gemini Live client creation."""
        with patch("core.voice.gemini_live.genai.Client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            
            client = create_gemini_live_client(
                api_key="test-key",
                voice="Aoede",
                persona="zoya"
            )
            
            assert client is not None
            mock_client.assert_called_once_with(api_key="test-key")


class TestPhase10TTS:
    """Test TTS integration."""

    def test_create_tts_client_groq(self):
        """Test TTS client creation with Groq."""
        with patch("core.voice.groq_tts.Groq", create=True) as mock_groq:
            mock_instance = Mock()
            mock_groq.return_value = mock_instance
            
            client = create_tts_client(backend="groq", voice="Arista")
            
            assert client is not None


class TestPhase10MultiAgentIntegration:
    """Test multi-agent integration in Phase 10."""

    def test_orchestrator_creation(self):
        """Test orchestrator is created with LLM provider."""
        mock_llm = MockProvider()
        orchestrator = create_orchestrator(llm_provider=mock_llm)
        
        assert orchestrator is not None
        assert orchestrator.llm_provider == mock_llm
        assert len(orchestrator.team) == 7  # 7 default agents

    def test_orchestrator_default_workflows(self):
        """Test built-in workflows are registered."""
        mock_llm = MockProvider()
        orchestrator = create_orchestrator(llm_provider=mock_llm)
        
        workflows = orchestrator.list_workflows()
        assert "research_plan_execute_verify" in workflows
        assert "plan_execute_verify" in workflows
        assert "parallel_research" in workflows
        assert "debate" in workflows

    def test_orchestrator_run_workflow(self):
        """Test running a workflow with mock provider."""
        mock_llm = MockProvider()
        orchestrator = create_orchestrator(llm_provider=mock_llm)
        
        result = orchestrator.run_workflow("plan_execute_verify", "open notepad")
        
        assert "workflow_id" in result
        assert result["goal"] == "open notepad"
        assert "results" in result


class TestPhase10AudioConfig:
    """Test audio configuration."""

    def test_audio_config_defaults(self):
        """Test AudioConfig has correct defaults."""
        from core.voice.audio_io import AudioConfig
        
        config = AudioConfig()
        assert config.sample_rate == 16000
        assert config.channels == 1

    def test_audio_stream_creation(self):
        """Test AudioStream creation."""
        from core.voice.audio_io import AudioConfig, AudioStream
        
        config = AudioConfig()
        stream = AudioStream(config)
        
        assert stream is not None
        assert stream.config == config


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])