import uvicorn

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    uvicorn.run("web.app:app", host=host, port=port, reload=False)


def main() -> None:
    run_server()
