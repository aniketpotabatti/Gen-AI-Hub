# CodeSense

> A real-time, LLM-powered source-code analyzer for the web and VS Code.

CodeSense gives developers fast, focused help where they write code: explain a snippet, review a saved file, or suggest the next logical completion. It streams results through a local gateway and uses a bring-your-own-key provider configuration in the web UI.

## Features

- **Explain** — concise, intent-first explanation of the selected or active code.
- **Review** — structured feedback highlighting strengths, improvements, and one refactor idea.
- **Suggest** — completion-only output designed for inline / ghost-text experiences.
- **Streaming responses** — Server-Sent Events (SSE) make feedback appear as it is generated.
- **Dual editor targets** — a React + Monaco web editor and an initial VS Code extension client.
- **Bring your own provider** — enter a provider API key directly in the UI; no `.env` file is required.
- **Flexible provider routing** — direct Anthropic support plus OpenAI-compatible providers such as OpenAI, Gemini, Groq, Together AI, Ollama, and compatible self-hosted endpoints.
- **Guardrails** — input validation, request-size limits, context trimming, and per-IP rate limiting.

## Architecture

```text
┌───────────────────────┐        ┌──────────────────────────┐
│  Monaco Web Editor    │        │     VS Code Extension    │
│  React + Vite         │        │     TypeScript           │
└───────────┬───────────┘        └────────────┬─────────────┘
            │                                  │
            └──────────── POST + SSE ──────────┘
                              │
                   ┌──────────▼──────────┐
                   │  CodeSense Gateway  │
                   │ Express · validation│
                   │ rate limits · prompts│
                   └──────────┬──────────┘
                              │
              ┌───────────────┴────────────────┐
              │                                │
     ┌────────▼────────┐              ┌────────▼────────┐
     │ Anthropic Claude │              │ OpenAI-compatible│
     │ direct API       │              │ provider endpoint │
     └─────────────────┘              └─────────────────┘
```

The shared `@codesense/core` package holds prompt construction, request validation, and cursor-aware context extraction. Editors send only the nearby code window rather than the full file.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Web editor | React, Vite, Monaco Editor |
| Gateway | Node.js, Express, SSE |
| Providers | Anthropic SDK, OpenAI SDK |
| VS Code client | TypeScript, VS Code API, esbuild |
| Shared logic | Native JavaScript workspace package |

## Project Structure

```text
codesense/
├── apps/
│   ├── gateway/            # Secure LLM proxy and SSE API
│   ├── web/                # React + Monaco editor
│   └── vscode-extension/   # VS Code extension client
├── packages/
│   └── core/               # Prompts, validation, context extraction
└── package.json
```

## Getting Started

### Prerequisites

- Node.js 20 or newer
- npm 9 or newer
- A key from a supported LLM provider, entered in the CodeSense UI

### Installation

```bash
git clone https://github.com/<your-username>/codesense.git
cd codesense
npm install
```

No `.env` file is required. CodeSense does not store provider keys. Enter provider settings in the CodeSense sidebar for the current browser session.

### Provider configuration

Choose a provider in the **Connection** panel, enter its API key, and optionally override the model or base URL.

| Provider selection | API key | Base URL | Example model |
| --- | --- | --- | --- |
| OpenAI or compatible | Required | Optional for OpenAI; required for most other providers | `gpt-4o-mini` |
| Anthropic Claude | Required | Not required | `claude-3-5-haiku-latest` |
| Google Gemini | Required | Set automatically; can be overridden | `gemini-2.0-flash` |

For OpenAI-compatible providers, enter the provider's OpenAI-compatible base URL and a model name available in your account. Examples include:

| Provider | Base URL | Example model |
| --- | --- | --- |
| OpenAI | Leave blank | `gpt-4o-mini` |
| Groq | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` |
| Ollama (local) | `http://localhost:11434/v1` | `llama3.2` |
| Google Gemini | Use the Gemini option | `gemini-2.0-flash` |

> A provider must expose either the Anthropic Messages API or an OpenAI-compatible Chat Completions API. Arbitrary, proprietary API formats require a small gateway adapter before CodeSense can use them.

### Run locally

Start the API gateway:

```bash
npm run dev
```

In a second terminal, start the web editor:

```bash
npm run dev:web
```

Open `http://localhost:5173` in your browser. The gateway is available at `http://localhost:8787`.

> The gateway root URL is intentionally not a web page. Check `GET /health` to confirm it is running.

## API

### `POST /api/codesense`

Streams a response using Server-Sent Events.

```json
{
  "mode": "explain",
  "language": "typescript",
  "snippet": "const square = (n: number) => n * n;",
  "cursorLine": 1,
  "cursorCol": 24
}
```

Supported modes are `explain`, `review`, and `suggest`.

Example stream:

```text
data: {"delta":"This function returns the square of a number."}

data: "[DONE]"
```

### `GET /health`

Returns service status. Provider keys are supplied per request from the UI and never returned by this endpoint.

```json
{
  "status": "ok",
  "authentication": "Bring your own API key"
}
```

## Safety and Limits

- API keys are entered by the user, sent only to the local CodeSense gateway for the active request, and never written to project files or browser storage.
- Request bodies are limited to 20 KB and code snippets to 12,000 characters.
- The context extractor keeps approximately 30 lines before and 10 lines after the cursor.
- Requests are limited to 30 per IP per minute in this development implementation.
- Generated review output is capped at 600 tokens; explain and suggest output at 400 tokens.

## VS Code Extension

Build the extension bundle:

```bash
npm run build --workspace=codesense-vscode
```

The initial extension provides **CodeSense: Explain Selection**. Open the extension folder in VS Code, run the extension host, select code, and invoke the command from the Command Palette. It expects the gateway at `http://localhost:8787` by default.

## Roadmap

- [x] Secure streaming gateway
- [x] Monaco web editor with explain, review, and suggest modes
- [x] Initial VS Code explain command
- [ ] Web inline completion rendering
- [ ] VS Code inline completion provider and review panel
- [ ] User-configurable debounce and model settings
- [ ] Automated tests and CI
- [ ] Deployment configuration and extension packaging

## Contributing

Issues and pull requests are welcome. New provider adapters should preserve the streaming API contract and must never persist user API keys.

## License

MIT — see the [Gen-AI-Hub](https://github.com/aniketpotabatti/gen-ai-hub) repository LICENSE.