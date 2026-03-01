# AI Resume Tailor

> Tailor your resume and cover letter for any job — powered by Claude AI.

![Demo](demo.gif)

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Streamlit UI (app.py)               │
│  ┌──────────┬──────────┬──────────┬────────────────┐ │
│  │  Input   │ Analysis │ Resume   │ Cover Letter   │ │
│  │   Tab    │   Tab    │   Tab    │     Tab        │ │
│  └────┬─────┴────┬─────┴────┬─────┴────────┬───────┘ │
│       │          │          │              │         │
│  ┌────▼────┐ ┌───▼────┐ ┌──▼──────────┐ ┌─▼──────┐ │
│  │ Resume  │ │   AI   │ │  Resume     │ │ Cover  │ │
│  │ Parser  │ │ Engine │ │  Generator  │ │ Letter │ │
│  └─────────┘ └───┬────┘ └─────────────┘ └────────┘ │
│                  │                                   │
│              ┌───▼────┐    ┌──────────────┐          │
│              │ Claude │    │ Job Tracker  │          │
│              │  API   │    │  (SQLite)    │          │
│              └────────┘    └──────────────┘          │
└─────────────────────────────────────────────────────┘
```

## Features

- **Job Description Analysis** — Extract requirements, skills, and ATS keywords
- **Fit Scoring** — AI-powered alignment score (0-100) with actionable feedback
- **Keyword Match Report** — See which keywords you're hitting and missing
- **Tailored Resume** — AI-rewritten resume optimized for the target role
- **Cover Letter** — Personalized 4-paragraph cover letter
- **Document Export** — Download as .docx and .pdf
- **Job Tracker** — SQLite-backed application tracker with CSV export

## Quick Start

### Prerequisites

- Python 3.11+
- [Anthropic API key](https://console.anthropic.com/)

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-resume-tailor.git
cd ai-resume-tailor

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Run the app
streamlit run app.py
```

### Docker

```bash
docker build -t ai-resume-tailor .
docker run -p 8501:8501 -e ANTHROPIC_API_KEY=your-key ai-resume-tailor
```

## Project Structure

```
ai-resume-tailor/
├── app.py                     # Main Streamlit application
├── src/
│   ├── ai_engine.py           # Claude API integration
│   ├── resume_parser.py       # .docx / .pdf / .txt parsing
│   ├── resume_generator.py    # .docx and .pdf output
│   ├── cover_letter.py        # Cover letter .docx output
│   ├── job_tracker.py         # SQLite job tracker
│   └── utils.py               # URL fetching utilities
├── tests/                     # Pytest test suite
├── .streamlit/config.toml     # Streamlit theme config
├── requirements.txt
├── .env.example
├── Dockerfile
└── README.md
```

## Running Tests

```bash
pytest tests/ -v
```

## Tech Stack

| Component       | Technology            |
| --------------- | --------------------- |
| Frontend        | Streamlit             |
| AI Engine       | Claude API (Anthropic)|
| Resume Parsing  | python-docx, PyPDF2   |
| Document Output | python-docx, ReportLab|
| Job Tracking    | SQLite                |
| Containerization| Docker                |

## License

MIT
