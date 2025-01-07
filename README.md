# Development

## Installation

- Install `uv` package & project manager: [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Install French locale.

```bash
sudo apt install language-pack-fr
sudo locale-gen fr_FR.UTF-8
sudo update-locale
locale -a
```

```bash
uv sync
source .venv/bin/activate
chainlit run app.py 
```

## Packaging

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t qnduong/lisa:1.0 .
docker login
docker push qnduong/lisa:1.0
```

## Environment variables

```text
OPENAI_API_KEY=
RECOGNIZERS_BASE_URL=
AGENDA_BASE_URL=
CHAINLIT_PORT=8080
MODEL_NAME=gpt-4o-mini
```

## Debug

In `app.py`

```python
if __name__ == "__main__":
    from chainlit.cli import run_chainlit

    run_chainlit(__file__)
```
