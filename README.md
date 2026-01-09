# AppForge

A modular AI pipeline for software development. Transform project ideas into clarified requirements, technical designs, and implementation plans.

## Features

- **Modular Steps**: Each pipeline stage is a swappable component
- **Registry Pattern**: Swap implementations with a single config change
- **Mock Mode**: Test pipeline logic without LLM calls
- **JSON Persistence**: All runs saved for inspection and replay
- **CLI Interface**: Simple command-line usage

## Installation

```bash
# Clone and install
cd appforge
pip install -e ".[dev]"

# Set up API keys (for LLM mode)
export OPENAI_API_KEY="your-key-here"
# or
export ANTHROPIC_API_KEY="your-key-here"
```

## Quick Start

### Run with Mock Steps (No LLM)

```bash
# Test the pipeline without making LLM calls
appforge run "Build a todo app with user authentication" --mock

# Test a single step
appforge test-step "Build a todo app" --step clarify --mock
```

### Run with LLM

```bash
# Full pipeline
appforge run "Build a todo app with user authentication"

# Specific steps only
appforge run "Build a todo app" --steps clarify,design

# Use Claude instead of GPT
appforge run "Build a todo app" --provider anthropic --model claude-3-sonnet-20240229
```

### View Results

```bash
# List all runs
appforge list-runs

# Show a specific run
appforge show 20240101_120000

# Show only one step's output
appforge show 20240101_120000 --step design
```

## Pipeline Steps

| Step | Purpose | Prompt |
|------|---------|--------|
| `clarify` | Analyze idea, identify gaps, ask questions | `prompts/v1/clarify.jinja` |
| `design` | Create technical architecture | `prompts/v1/design.jinja` |
| `plan` | Break down into implementation phases | `prompts/v1/plan.jinja` |

## Swapping Implementations

### Via CLI

```bash
# Swap clarify to use mock
appforge swap clarify mock_clarify

# Check current mappings
appforge list-steps
```

### Via Config

Edit `config.yaml`:

```yaml
steps:
  clarify:
    implementation: mock_clarify  # Use mock instead of LLM
```

### Programmatically

```python
from appforge.registry import get_default_registry
from appforge.steps.mock import MockStep

registry = get_default_registry()
registry.register("my_clarify", MockStep)
registry.set_active("clarify", "my_clarify")
```

## Creating Custom Steps

```python
from appforge.steps.base import BaseStep, StepResult
from appforge.registry import register_step

@register_step("my_custom_step")
class MyCustomStep(BaseStep):
    def execute(self, input_data, context=None):
        # Your logic here
        result = process(input_data)

        return StepResult(
            success=True,
            output=result,
            step_name=self.name,
        )
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=appforge

# Run specific test file
pytest tests/test_pipeline.py
```

## Project Structure

```
appforge/
├── src/appforge/
│   ├── __init__.py
│   ├── cli.py           # Command-line interface
│   ├── pipeline.py      # Pipeline orchestrator
│   ├── registry.py      # Step registration
│   └── steps/
│       ├── base.py      # BaseStep abstract class
│       ├── mock.py      # Mock implementations
│       └── llm.py       # LLM-powered steps
├── prompts/
│   └── v1/
│       ├── clarify.jinja
│       ├── design.jinja
│       └── plan.jinja
├── tests/
├── runs/                # Pipeline output (created on first run)
├── config.yaml
├── pyproject.toml
└── README.md
```

## Configuration

Environment variables:

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |

## Run Output

Each run creates a JSON file in `./runs/`:

```json
{
  "run_id": "20240101_120000",
  "status": "completed",
  "initial_input": "Build a todo app...",
  "final_output": "...",
  "steps_completed": ["clarify", "design", "plan"],
  "results": [
    {"step_name": "clarify", "success": true, "output": "..."},
    {"step_name": "design", "success": true, "output": "..."},
    {"step_name": "plan", "success": true, "output": "..."}
  ]
}
```

## Next Steps

This prototype provides the foundation. Future enhancements could include:

- Interactive clarification (ask follow-up questions)
- Code generation steps
- Integration with version control
- Web UI
- Parallel step execution
- Budget tracking and model routing
