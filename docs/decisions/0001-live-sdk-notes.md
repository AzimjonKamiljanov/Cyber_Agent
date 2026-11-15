# Decision Record 0001: Gemini Live SDK Introspection & Interface Notes

**Date:** 2026-11-15  
**Package:** `google-genai==3.3.0`  
**Status:** Approved  
**Context:** Verification of real classes and signatures for `gemini-3.8-live` integration against MASTER_PLAN Appendix B.

---

## 1. Verified SDK Signatures

### 1.1 Client Connection
- **Module:** `google.genai.Client`
- **Async Live Connection:**
  ```python
  client = genai.Client(api_key=settings.gemini_api_key)
  async with client.aio.live.connect(model=model_id, config=config) as session:
      ...
  ```
  `client.aio.live.connect` takes `model: str` and `config: types.LiveConnectConfig`.
  Returns an asynchronous context manager yielding `google.genai.live.AsyncSession`.

### 1.2 Configuration Class (`google.genai.types.LiveConnectConfig`)
- `response_modalities`: `list[google.genai.types.Modality]`, pass `["AUDIO"]`.
- `system_instruction`: `str` or `types.Content`.
- `input_audio_transcription`: `types.AudioTranscriptionConfig()` (enables user speech-to-text).
- `output_audio_transcription`: `types.AudioTranscriptionConfig()` (enables agent text transcript).
- `session_resumption`: `types.SessionResumptionConfig(handle=str, transparent=bool)`.
- `context_window_compression`: `types.ContextWindowCompressionConfig(trigger_tokens=int, sliding_window=...)`.
- **Prohibited Flags for `gemini-3.8-live`:**
  - `thinking_config`: Do NOT set (3.8 Live errors if provided).
  - `enable_affective_dialog`: Do NOT set.

### 1.3 Streaming Input & Barge-in (`google.genai.live.AsyncSession`)
- **Audio input streaming:**
  ```python
  await session.send_realtime_input(
      audio=types.Blob(data=pcm16_bytes, mime_type="audio/pcm;rate=16000")
  )
  ```
- **Barge-in / Generation Interruption:**
  ```python
  await session.send_client_content(turn_complete=True)
  ```
  Instantly signals end-of-turn and cancels pending model speech generation.

### 1.4 Server Messages (`google.genai.types.LiveServerMessage`)
`session.receive()` yields `types.LiveServerMessage` instances containing:
- `server_content`: `types.LiveServerContent`
  - Model turns contain parts with PCM16 24 kHz audio data and real-time output transcript text.
  - User turns contain input transcript text.
- `go_away`: `types.LiveServerGoAway(time_left=str)`
  - Signals server-initiated session wind-down. Handled by draining output and reconnecting using the latest resumption handle.
- `session_resumption_update`: `types.LiveServerSessionResumptionUpdate`
  - Attributes: `new_handle: str`, `resumable: bool`, `last_consumed_client_message_index: int`.
  - Stored in memory as the latest resumption handle.

### 1.5 Function Calling & Non-blocking Behavior
- **Tool Declaration:**
  `types.LiveConnectConfig(tools=[types.Tool(function_declarations=[...])])`
- **Function Declaration:**
  `types.FunctionDeclaration(name=..., description=..., parameters_json_schema=..., behavior=types.Behavior.NON_BLOCKING)`
- **Server Tool Calls:**
  Received via `msg.tool_call.function_calls: list[types.FunctionCall]` where each item has `.id`, `.name`, `.args`.
- **Client Tool Responses:**
  Sent via `await session.send_tool_response(function_responses=[types.FunctionResponse(id=..., name=..., response=...)])`.

---

## 2. Differences from Appendix B
- **Realtime Input:** `session.send_realtime_input(audio=types.Blob(...))` is explicitly typed with `audio` parameter in `google-genai==3.3.0` (as predicted in Appendix B).
- **Session Resumption Update:** Received directly on `msg.session_resumption_update.new_handle`.
- **GoAway Signal:** Received on `msg.go_away` with `time_left`.
