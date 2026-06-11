# Multi-Modal Session Insights Pipeline

Streamlit app for generating a parent-friendly learning report from one student's online class session.

## What It Processes
- Activity JSON
- Attendance JSON
- Optional video file
- Optional audio file
- Optional homework PDFs

Activity JSON and attendance JSON are required for every report.

## Pipeline Design
The project follows the assignment flow:

1. Ingest video, audio, activity JSON, attendance JSON, and homework PDFs.
2. Extract features with open-source tools.
3. Synthesize the final parent report.
4. Save JSON, styled HTML, and PDF output.

The report synthesis layer requires a local Ollama model. The Streamlit sidebar lets you choose the local model name. No cloud API key is required.

## Run
```bash
./run_app.sh
```

Then open:

```text
http://127.0.0.1:8501
```

## Install Dependencies
```bash
python3 -m pip install -r requirements.txt
```

## Local LLM Setup
Install Ollama and pull the small local model:
```bash
ollama pull llama3.2:1b
```

Run the app with local LLM synthesis:
```bash
export LLM_PROVIDER=ollama
export OLLAMA_MODEL=llama3.2:1b
./run_app.sh
```

The app keeps local generation short:
```bash
export LLM_MAX_OUTPUT_TOKENS=300
```

## Test Inputs
Use files in `test_inputs/`:

- Activity JSON: `test_inputs/activity/activity_log.json`
- Attendance JSON: `test_inputs/attendance/attendance.json`
- Audio WAV: `test_inputs/audio/sample_speech.wav`
- Homework PDF: `test_inputs/homework/homework_submission.pdf`
- Optional sample homework PDF: `test_inputs/homework/sample_homework_for_upload.pdf`

For video testing, upload your own `.mp4`, `.mov`, `.avi`, `.mkv`, or `.webm`.

## Outputs
Generated files are saved in `outputs/`:

- `outputs/report.json`
- `outputs/report.html`
- `outputs/report.pdf`

## Full Guide
The complete project flow and code explanation is in:

- `docs/full_project_explanation.html`

## Tests
```bash
python3 -m unittest discover -s tests -v
```

## Core Pipeline
The code in `src/` handles:
- Video focus analysis
- Audio fluency analysis
- Activity and attendance metrics
- Homework PDF parsing
- Optional LLM synthesis
- Report generation
- HTML and PDF export

## Model Choices
- Video: OpenCV Haar Cascade face detection for offline focus estimation.
- Audio: librosa for duration and pause features, with soundfile fallback for decoding.
- Speech transcription: faster-whisper when the model is available locally.
- Homework parsing: PyMuPDF for PDF text extraction.
- LLM synthesis: local Ollama only. Report generation fails if Ollama is unavailable or returns invalid output.

## Scaling to 10,000 Live Sessions
For production scale, each session should be processed as an asynchronous job. Uploads would go to object storage, metadata would live in a database, and workers would process video/audio/homework independently through a queue. Heavy models such as Whisper and face analysis should run on separate GPU-enabled worker pools, while LLM report generation can be batched, cached, retried, and monitored. The Streamlit prototype would become an internal/admin UI or be replaced by a production web app that reads completed reports from the database.
