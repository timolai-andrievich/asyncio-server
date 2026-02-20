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
class KeepaliveMessage:
    response_id: int
    full_text: bytes

    @staticmethod
    def parse(data: bytes) -> Optional["KeepaliveMessage"]:
        pattern = rb"^\[(\d+)\] keepalive\n$"
        match = re.match(pattern, data)
        if not match:
            return None
        response_id = int(match.group(1))
        return KeepaliveMessage(response_id, data)


@dataclass
class PongMessage:
    response_id: int
    response_to: int
    client_id: int
    full_text: bytes

    @staticmethod
    def parse(data: bytes) -> Optional["PongMessage"]:
        pattern = rb"^\[(\d+)/(\d+)\] PONG \((\d+)\)\n$"
        match = re.match(pattern, data)
        if not match:
            return None
        response_id = int(match.group(1))
        response_to = int(match.group(2))
        client_id = int(match.group(3))
        return PongMessage(response_id, response_to, client_id, data)


class AsyncCounter:
    def __init__(self, start: int = 0):
        self.counter = start
        self.lock = asyncio.Lock()

    async def __call__(self):
        async with self.lock:
            result = self.counter
            self.counter += 1
            return result


class Client:
    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 8080,
        seed: int | None = None,
        timeout: float = 5.0,
    ):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None
        self.ping_counter = AsyncCounter(0)
        self.random = random.Random(seed)
        self.pong_futures = {}
        self.timeout = timeout

    async def connect(self):
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.host, self.port
            )
            return True
        except Exception:
            logger.exception("Failed to connect to the server")
            return False

    async def handle_keepalive(self, message: KeepaliveMessage):
        response_time = datetime.now()
        date_formatted = response_time.strftime("%Y-%m-%d")
        time_formatted = (
            response_time.strftime("%H:%M:%S.")
            + f"{response_time.microsecond // 1000:03d}"
        )
        logger.info(
            "%s %s %s",
            date_formatted,
            time_formatted,
            message.full_text.decode().strip(),
        )

    async def handle_pong(self, message: PongMessage):
        future = self.pong_futures.get(message.response_to)
        if not future:
            return
        future.set_result(message)

    async def message_receiver(self):
        while True:
            data = await self.reader.readline()
            if message := KeepaliveMessage.parse(data):
                await self.handle_keepalive(message)
            elif message := PongMessage.parse(data):
                await self.handle_pong(message)

    async def run(self):
        if not await self.connect():
            return
        asyncio.create_task(self.message_receiver())
        loop = asyncio.get_running_loop()
        while True:
            ping_id = await self.ping_counter()
            pong_future = loop.create_future()
            self.pong_futures[ping_id] = pong_future
            request = f"[{ping_id}] PING\n".encode()
            self.writer.write(request)
            await self.writer.drain()
            request_time = datetime.now()
            date_formatted = request_time.strftime("%Y-%m-%d")
            request_time_formatted = (
                request_time.strftime("%H:%M:%S.")
                + f"{request_time.microsecond // 1000:03d}"
            )
            try:
                response = await asyncio.wait_for(pong_future, self.timeout)
                response_text = response.full_text.decode()
            except asyncio.TimeoutError:
                response_text = "(таймаут)"
            response_time = datetime.now()
            self.pong_futures.pop(ping_id)
            response_time_formatted = (
                response_time.strftime("%H:%M:%S.")
                + f"{response_time.microsecond // 1000:03d}"
            )
            logger.info(
                "%s %s %s %s %s",
                date_formatted,
                request_time_formatted,
                request.decode().strip(),
                response_time_formatted,
                response_text.strip(),
            )
            delay = self.random.randint(300, 3000) / 1000
            await asyncio.sleep(delay)


def main():
    client = Client(
        host=settings.host,
        port=settings.port,
        seed=settings.random_seed,
    )
    asyncio.run(client.run())


if __name__ == "__main__":
    main()
