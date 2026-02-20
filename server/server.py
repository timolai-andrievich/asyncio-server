from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import asyncio
import random
import re

from logger import get_logger
from settings import get_settings


settings = get_settings()
logger = get_logger()


@dataclass
class ClientPing:
    number: int

    @staticmethod
    def parse(data: bytes) -> Optional["ClientPing"]:
        pattern = rb"^\[(\d+)\] PING\n$"
        match = re.match(pattern, data)
        if not match:
            return None
        number = int(match.group(1))
        return ClientPing(number)


class AsyncCounter:
    def __init__(self, start: int = 0):
        self.counter = start
        self.lock = asyncio.Lock()

    async def __call__(self):
        async with self.lock:
            result = self.counter
            self.counter += 1
            return result


class Server:
    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 8080,
        seed: int | None = None,
    ):
        self.host = host
        self.port = port
        self.client_counter = AsyncCounter(1)
        self.response_counter = AsyncCounter(0)
        self.random = random.Random(seed)

    async def handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        client_id = await self.client_counter()

        async def keepalive():
            while True:
                await asyncio.sleep(5.0)
                response_id = await self.response_counter()
                message = f"[{response_id}] keepalive\n".encode()
                writer.write(message)
                await writer.drain()

        asyncio.create_task(keepalive())
        while True:
            try:
                data = await reader.readline()
            except ConnectionResetError:
                break
            request_time = datetime.now()
            date_formatted = request_time.strftime("%Y-%m-%d")
            request_time_formatted = (
                request_time.strftime("%H:%M:%S.")
                + f"{request_time.microsecond // 1000:03d}"
            )
            ping = ClientPing.parse(data)
            if ping is None:
                continue
            ignore = self.random.random() < 0.1
            if ignore:
                logger.info(
                    f"{date_formatted} {request_time_formatted} "
                    f"{data.decode().strip()} (проигнорировано)"
                )
                continue
            delay = self.random.randint(100, 1000) / 1000
            await asyncio.sleep(delay)
            response_id = await self.response_counter()
            response = f"[{response_id}/{ping.number}] PONG ({client_id})\n".encode()
            writer.write(response)
            await writer.drain()
            response_time = datetime.now()
            response_time_formatted = (
                response_time.strftime("%H:%M:%S.")
                + f"{response_time.microsecond // 1000:03d}"
            )
            logger.info(
                f"{date_formatted} {request_time_formatted} "
                f"{data.decode().strip()} {response_time_formatted} "
                f"{response.decode().strip()}"
            )

    async def run(self):
        server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port,
        )
        await server.serve_forever()


def main():
    server = Server(
        host=settings.host,
        port=settings.port,
        seed=settings.random_seed,
    )
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
