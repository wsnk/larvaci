import logging
import asyncio
import subprocess
import time
import sys


# -------------------------------------------------------------------------------------------------
async def _output_to_logger(reader, logger, prefix=""):
    while True:
        l = await reader.readline()
        if not l:
            return
        s = l.decode("utf-8", errors="ignore").strip()
        logger.info(prefix + s)


async def _output_to_fobj(reader, fobj):
    while True:
        l = await reader.readline()
        if not l:
            return
        fobj.write(l)


async def _output_to_file(reader, fname):
    with open(fname, "wb") as f:
        await _output_to_fobj(reader, f)


async def _output_to_devnull(reader):
    while (await reader.read(1024)):
        pass


# -------------------------------------------------------------------------------------------------
class Process:
    STDOUT = "STDOUT"
    STDERR = "STDERR"

    async def __aenter__(self):
        await self._run()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if self.returncode is None:
            try:
                await self.terminate()
            except ProcessLookupError:
                pass

    def _redirect_output(self, reader, out):
        name = "STDERR" if (reader is self._proc.stderr) else "STDOUT"

        if isinstance(out, logging.Logger):
            dst = "logger (info level)"
            asyncio.create_task(_output_to_logger(reader, out, prefix=f"[PID={self.pid}, {name}] "))
        elif out == subprocess.DEVNULL:
            dst = "DEVNULL"
            asyncio.create_task(_output_to_devnull(reader))
        elif hasattr(out, "write"):
            dst = f"FileObject ({out})"
            asyncio.create_task(_output_to_fobj(reader, out))
        elif isinstance(out, str):
            dst = f"file ({out})"
            asyncio.create_task(_output_to_file(reader, out))
        else:
            raise RuntimeError(f"invalid 'out' argument: {out}")

        self.logger.info(f"Redirect {name} of process PID={self.pid} to {dst}")

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

    async def _run(self):
        self.logger.debug(f"Run command {self._args} with workdir={self._cwd} ...")
        self._proc = await asyncio.create_subprocess_exec(
            *self._args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self._cwd
        )
        self.logger.info(f"Command {self._args} with workdir={self._cwd} started a process with PID={self._proc.pid}")

    async def _wait(self, noexcept=False, noredirect=False, timeout=None, stdout=None, stderr=None):
        retcode = self._proc.returncode
        if retcode is None:
            if not noredirect:
                self._redirect_output(self._proc.stdout, self.logger if stdout is None else stdout)
                self._redirect_output(self._proc.stderr, self.logger if stderr is None else stderr)

            try:
                retcode = await asyncio.wait_for(self._proc.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                self.logger.warning(f"Process PID={self.pid} didn't finish in {timeout} secconds")
                raise

        self.logger.info(f"Process PID={self.pid} finished with code {retcode}")
        if noexcept or retcode == 0:
            return retcode
        raise RuntimeError(f"command failed with code = {retcode}")

    async def exec(self, noexcept=False, timeout=None, stdout=None, stderr=None):
        return await self._wait(noexcept=noexcept, timeout=timeout, stdout=stdout, stderr=stderr)

    async def read_stdout_until(self, separator=b"\n", raw=False, stderr=None, timeout=None, noexcept=False):
        self._redirect_output(self._proc.stderr, out=self.logger if stderr is None else stderr)

        eof = False
        while not eof:
            try:
                chunk = await asyncio.wait_for(self._proc.stdout.readuntil(separator), timeout=timeout)
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
        await self._wait(noexcept=noexcept, noredirect=True, timeout=timeout)

    async def read_stdout(self, **kwargs):
        async for line in self.read_stdout_until(separator=b"\n", **kwargs):
            yield line

    async def terminate(self, timeout=10):
        self._proc.terminate()
        try:
            self.logger.warning(f"Terminate process PID={self.pid} ...")
            return await self._wait(noexcept=True, noredirect=True, timeout=timeout)
        except asyncio.TimeoutError:
            self.logger.warning(f"Could not terminate process PID={self.pid}, try to kill it...")

        self._proc.kill()
        try:
            self.logger.warning(f"Kill process PID={self.pid} ...")
            return await self._wait(noexcept=True, noredirect=True, timeout=timeout)
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
        `timeout` - timeout for process completion (raise asyncio.TimeoutError)
        `stderr`, `stdout` - one of:
            None - log output via logger (default)
            subprocess.DEVNULL - drop output to nowhere
            <file name> - write ouput as-is into a file
            File-like object (with `write` method) - write to it
        """
        async with self.run(args, cwd) as proc:
            return await proc.exec(**kwargs)

    async def read_stdout(self, args, cwd=None, **kwargs):
        async for line in self.read_stdout_until(args, separator=b"\n", cwd=cwd, **kwargs):
            yield line

    async def read_stdout_until(self, args, separator=b"\n", cwd=None, **kwargs):
        """ Async generator of lines obtained from STDOUT

        Extra kwargs:
        `raw` - do not decode bytes read from STDOUT
        `noexcept` - do not raise exception if running process is failed
        `timeout` - timeout for process completion (raise asyncio.TimeoutError)
        `stderr`, `stdout` - one of:
            None - log output via logger (default)
            subprocess.DEVNULL - drop output to nowhere
            <file name> - write ouput as-is into a file
            File-like object (with `write` method) - write to it
        """
        async with self.run(args, cwd) as proc:
            async for chunk in proc.read_stdout_until(separator=separator, **kwargs):
                yield chunk


# -------------------------------------------------------------------------------------------------
async def run(args):
    cmd = Command()
    # await cmd.exec(args)
    # async for l in cmd.read_stdout_until(args, separator=b"\n"):
    #     print(l)
    # async for l in cmd.read_stdout(args):
    #     print(l)

    async for l in cmd.read_stdout_until(args, separator=b"\n", stderr="zazaza"):
        print(l)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)

    asyncio.run(run(["curl", "-v", "yandex.ru"]))
