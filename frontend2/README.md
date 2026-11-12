# Fieldwise — Exploration Copilot UI

A self-contained frontend prototype for GeoHackathon Challenge 1. It is designed to be opened in a browser without a build step or third-party JavaScript packages.

## Run locally

From this folder, serve the files with Python:

```bash
python3 -m http.server 5173
```

Open `http://localhost:5173` in a browser. On the hackathon HPC, use the team's approved Jupyter or web-serving workflow and keep challenge data in the provided HPC storage.

## What works in this prototype

- Workspace navigation for overview, data library, interpretation, analogue search and risk review.
- Responsive layout for desktop and mobile widths.
- Conceptual seismic preview with horizon and well marker toggles. It is an interface illustration, not a seismic section from the challenge data.
- File selection and drag-and-drop that display local filenames only. The browser does not upload or parse selected files.
- Conversational prompt chips and a chat composer. Until connected to an API, replies explain the evidence needed and are labelled as illustrative.
- Optional OpenAI-compatible chat endpoint configuration, described below.

## Challenge input context

The participant material lists 9 Challenge 1/2 seismic volumes (5 stack and 4 inversion) and 13 well packages on the HPC. The UI labels these as available on HPC, not as files already loaded into this browser. It also leaves basin analogues unpopulated until the team adds references.

## Connect the Python workflow

Before `app.js` loads, define `window.COPILOT_CONFIG` in `index.html` or an environment-specific config file:

```html
<script>
  window.COPILOT_CONFIG = {
    chatEndpoint: "/api/chat",
    model: "google/gemma-4-26B-A4B-it"
  };
</script>
<script src="app.js"></script>
```

The configured endpoint receives an OpenAI-compatible request body and should return `choices[0].message.content` (or a simple `reply` / `answer` field). A small Python service can proxy the request to the team's allowed LLM endpoint and expose notebook-generated evidence summaries. Serving the UI and proxy from the same origin avoids browser CORS issues. Keep credentials and private HPC access details on the server; never put them in `app.js` or a public repository.

For evidence-based outputs, have the Python side return source references with each observation, separate observations from interpretations, show meaningful alternatives, and identify unresolved risks. Do not treat the prototype's sample answers as analysis of the challenge data.

## Suggested public-repository hygiene

- Commit this UI and a setup README, not raw challenge seismic or well files.
- Do not publish team access credentials, private tokens or environment secrets.
- Check that any screenshots clearly label the conceptual seismic preview as illustrative.
