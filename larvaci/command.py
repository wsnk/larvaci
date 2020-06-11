import logging
import asyncio
import subprocess
import time


class Command:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger()
        self.stdout = bytearray()
        self._tasks = []

    def _read_output(self, reader):
        async def read():
            while True:
                l = await reader.readline()
                self.stdout += l
                if not l:
                    self.logger.debug(f"OUT: <EOF>")
                    return
                s = l.decode("utf-8").strip()
                self.logger.debug(f"OUT: {s}")

        self._tasks.append(asyncio.create_task(read()))

    async def run(self, args, cwd=None):
        self.logger.debug(f"Run command: {args}...")
        self.stdout = bytearray()

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

    async def exec(self, *args, **kwargs):
        await self.run(*args, **kwargs)
        retcode = await self.wait()
        if retcode != 0:
            raise RuntimeError(f"command failed with code = {retcode}")