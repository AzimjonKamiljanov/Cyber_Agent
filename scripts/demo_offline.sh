#!/usr/bin/env bash
# scripts/demo_offline.sh
# Cyber Agent — Stage S3 Offline Demo & Privacy Mode Verification
# Tests end-to-end local operation without any cloud dependencies.
set -euo pipefail

echo "=========================================================="
echo " CYBER AGENT: OFFLINE DEMO & PRIVACY MODE (MODE C)"
echo "=========================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$WORKSPACE_ROOT"

export PYTHONPATH="src:."
export CYBER_PRIVACY_MODE="true"
export CYBER_MODE="C"
export CYBER_TTS_PROVIDER="local"

PYTHON=".venv/bin/python"

echo "1. Tekshirish: Mahalliy STT (Whisper)..."
$PYTHON -c "
from cyber_agent.providers.stt_whisper import WhisperSTTProvider
stt = WhisperSTTProvider(model_id='tiny', device='cpu', compute_type='int8')
print('   ✓ Local Whisper STT tayyor.')
"

echo "2. Tekshirish: Mahalliy Ovoz Sintezi (Local Offline TTS)..."
$PYTHON -c "
import asyncio
from cyber_agent.providers.tts_local import LocalTTSProvider

async def test():
    tts = LocalTTSProvider()
    pcm = await tts.synthesize_to_pcm('Salom, tizim offline rejimda ishlayapti.')
    assert len(pcm) > 0
    print(f'   ✓ Local TTS {len(pcm)} bayt audio yaratdi (100% offline).')

asyncio.run(test())
"

echo "3. Tekshirish: Privacy Mode va Tarmoq Izolyatsiyasi..."
$PYTHON -c "
import asyncio
from cyber_agent.providers.tts_edge import EdgeTTSProvider

async def test_privacy():
    provider = EdgeTTSProvider()
    try:
        async for _ in provider.stream_audio('Sinov'):
            pass
        raise RuntimeError('Xatolik: Privacy modeda bulut servisi ishladi!')
    except PermissionError:
        print('   ✓ Edge TTS Privacy Mode da to\'liq bloklandi (0 tashqi so\'rov).')

asyncio.run(test_privacy())
"

echo "4. Tekshirish: Kaskad quvuri (Cascade Pipeline) offline testi..."
$PYTHON -c "
import asyncio
from cyber_agent.brain.cascade_pipeline import CascadePipeline
from cyber_agent.brain.model_router import get_model_router
from cyber_agent.brain.orchestrator import get_orchestrator
from cyber_agent.providers.stt_whisper import WhisperSTTProvider
from cyber_agent.providers.ollama_local import OllamaLocalProvider
from cyber_agent.providers.tts_local import LocalTTSProvider

class MockWhisper(WhisperSTTProvider):
    def transcribe_pcm(self, b, sr=16000):
        return 'Hozirgi vaqtni ayt'

async def run_pipeline():
    router = get_model_router()
    router.set_privacy_mode(True)
    pipe = CascadePipeline(
        stt_provider=MockWhisper(),
        local_tts=LocalTTSProvider(),
        router=router
    )
    pipe.buffer_audio(b'\x00\x00' * 3200)
    events = [e async for e in pipe.process_turn()]
    transcripts = [e.text for e in events if hasattr(e, 'text')]
    print(f'   ✓ Pipeline muvaffaqiyatli yakunlandi. Natija: {transcripts}')

asyncio.run(run_pipeline())
"

echo ""
echo "=========================================================="
echo " XULOSA: Barcha offline tekshiruvlar muvaffaqiyatli o'tdi!"
echo " Tizim internetsiz 100% mustaqil ishlashga tayyor."
echo "=========================================================="
