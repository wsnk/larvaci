import logging
import asyncio
import subprocess
import time


class Command:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger()
        self._tasks = []

    def _read_output(self, reader):
        async def read():
            while True:
                l = (await reader.readline()).decode("utf-8").strip()
                if not l:
                    self.logger.debug(f"OUT: <EOF>")
                    return
                self.logger.debug(f"OUT: {l}")

        self._tasks.append(asyncio.create_task(read()))

    async def run(self, args, cwd=None):
        self.logger.debug(f"Run command: {args}...")

        self.proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )

        self.logger.debug(f"Command {args} started a process with PID={self.proc.pid}")
        self._read_output(self.proc.stdout)
        self._read_output(self.proc.stderr)

    async def wait(self):
        return await self.proc.wait()