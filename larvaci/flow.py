import os
import json
import logging
import time
import asyncio
from .command import Command
from .git import Git

_CONTEXT_FNAME = "context.json"


class FlowBase:
    delay = 60

    def __init__(self, workdir, logger):
        self.workdir = workdir
        self.logger = logger
        self.command = Command(logger=self.logger)
        self.git = Git(logger=self.logger)
        self.context = {}

        self._context_path = os.path.join(self.workdir, _CONTEXT_FNAME)
        if os.path.exists(self._context_path):
            with open(self._context_path, "r") as f:
                self.context = json.load(f)
            logging.info(f"Context of {self.name} flow is loaded")
    
    @property
    def name(self):
        return self.__class__.__name__

    def shutdown(self):
        with open(self._context_path, "w") as f:
            json.dump(self.context, f)
        logging.info(f"Context of {self.name} flow is saved")
    
    async def _run(self, *args, **kwargs):
        try:
            while True:
                logging.debug(f"Run {self.name} flow...")

                t0 = time.monotonic()
                try:
                    await self.run(*args, **kwargs)
                except asyncio.CancelledError:
                    raise
                except Exception as err:
                    logging.exception(f"Flow {self.name} has failed with an exception")
                dur = time.monotonic() - t0

                logging.info(f"Flow {self.name} has finished in {dur} seconds")
                await asyncio.sleep(self.delay)
        except asyncio.CancelledError:
            logging.info(f"Flow {self.name} has been stopped")
        except BaseException as err:
            logging.exception(f"Flow {self.name} has epically crashed with an exception")

        self.shutdown()

    async def run(self):
        raise NotImplementedError("run() must be implemented in sublcasses")
