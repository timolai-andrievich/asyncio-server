import asyncio
from typing import NoReturn
import time
import sys

from settings import get_settings


settings = get_settings()


class Server:
    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 8080,
    ):
        self.host = host
        self.port = port

    async def handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> NoReturn:
        while True:
            data = await reader.readline()
            writer.write(data)
            await writer.drain()

    async def run(self) -> NoReturn:
        server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port,
        )
        await server.serve_forever()


def main():
    server = Server(host=settings.host, port=settings.port)
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
