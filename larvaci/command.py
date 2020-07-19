import logging
import asyncio
import subprocess
import time


# -------------------------------------------------------------------------------------------------
async def _with_timeout(coro, timeout=None):
    if timeout is None:
        return await coro
    return await asyncio.wait_for(coro, timeout=timeout)


# -------------------------------------------------------------------------------------------------
class Process:
    STDOUT = "STDOUT"
    STDERR = "STDERR"

    async def __aenter__(self):
        await self.run()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if self.returncode is None:
            try:
                await self.terminate()
            except ProcessLookupError:
                pass

    def _log_output(self, reader, out):
        async def func():
            while True:
                l = await reader.readline()
                if not l:
                    return
                s = l.decode("utf-8", errors="ignore").strip()
                self.logger.debug(f"[PID={self.pid}, {out}] {s}")

        asyncio.create_task(func())

    def __init__(self, args, cwd, logger):
        self.logger = logger
        self._args = args
        self._cwd = cwd
        self._proc = None

    @property
    def pid(self):
        return self._proc.pid
    
    @property
    def returncode(self):
        return self._proc.returncode

    async def run(self):
        self.logger.debug(f"Run command {self._args} with workdir={self._cwd} ...")
        self._proc = await asyncio.create_subprocess_exec(
            *self._args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self._cwd
        )
        self.logger.info(f"Command {self._args} with workdir={self._cwd} started a process with PID={self._proc.pid}")

    async def wait(self, noexcept=False, nolog=False, timeout=None):
        retcode = self._proc.returncode
        if retcode is None:
            if not nolog:
                self._log_output(self._proc.stdout, self.STDOUT)
                self._log_output(self._proc.stderr, self.STDERR)
            try:
                retcode = await _with_timeout(self._proc.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                self.logger.warning(f"Process PID={self.pid} didn't finish in {timeout} secconds")
                raise

        self.logger.info(f"Process PID={self.pid} finished with code {retcode}")
        if noexcept or retcode == 0:
            return retcode
        raise RuntimeError(f"command failed with code = {retcode}")

    async def read_stdout(self, **kwargs):
        async for line in self.read_stdout_until(separator=b"\n", **kwargs):
            yield line
    
    async def read_stdout_until(self, separator=b"\n", raw=False, noexcept=False, nolog=False, timeout=None):
        if not nolog:
            self._log_output(self._proc.stderr, self.STDERR)

        eof = False
        while not eof:
            try:
                chunk = await _with_timeout(self._proc.stdout.readuntil(separator), timeout=timeout)
            except asyncio.IncompleteReadError as err:
                chunk = err.partial
                eof = True
            if not chunk:
                break  # no more output in STDOUT
            if not raw:
                chunk = chunk[:-len(separator)].decode("utf-8", errors="ignore")
            self.logger.debug(f"[PID={self.pid}, {self.STDOUT}] {chunk}")
            yield chunk

        # STDOUT is closed, STDERR is being logged already
        await self.wait(noexcept=noexcept, nolog=True, timeout=timeout)

    async def terminate(self, timeout=10):
        self._proc.terminate()
        try:
            self.logger.warning(f"Terminate process PID={self.pid} ...")
            return await self.wait(noexcept=True, nolog=True, timeout=timeout)
        except asyncio.TimeoutError:
            self.logger.warning(f"Could not terminate process PID={self.pid}, try to kill it...")

        self._proc.kill()
        try:
            self.logger.warning(f"Kill process PID={self.pid} ...")
            return await self.wait(noexcept=True, nolog=True, timeout=timeout)
        except asyncio.TimeoutError:
            self.logger.error(f"Could not kill process PID={self.pid}")


# -------------------------------------------------------------------------------------------------
class Command:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger()

    def run(self, args, cwd=None):
        return Process(args, cwd, self.logger)
    
    async def exec(self, args, cwd=None, **kwargs):
        """
        Extra kwargs:
        `noexcept` - do not raise exception if running process is failed
        `nolog` - do not log STDERR output
        `timeout` - timeout for process completion (raise asyncio.TimeoutError)
        """
        async with self.run(args, cwd) as proc:
            return await proc.wait(**kwargs)

    async def read_stdout(self, args, cwd=None, **kwargs):
        """ Async generator of lines obtained from STDOUT

        Extra kwargs:
        `raw` - do not decode bytes read from STDOUT
        `noexcept` - do not raise exception if running process is failed
        `nolog` - do not log STDERR output
        `timeout` - timeout for reading lines from STDOUT (raise asyncio.TimeoutError)
        """
        async with self.run(args, cwd) as proc:
            async for line in proc.read_stdout(**kwargs):
                yield line

    async def read_stdout_until(self, args, separator=b"\n", cwd=None, **kwargs):
        async with self.run(args, cwd) as proc:
            async for chunk in proc.read_stdout(separator=separator, **kwargs):
                yield chunk


# -------------------------------------------------------------------------------------------------
async def run(args):
    cmd = Command()
    async for l in cmd.read_stdout_until(args, separator=b"\n"):
        print(l)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)

    asyncio.run(run(["ls", "-lah", "/"]))
