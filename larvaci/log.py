import logging
import logging.handlers
import os


def init_logger(name=None, logdir=None, verbose=False):
    logger = logging.getLogger(name)
    if logdir is not None:
        os.makedirs(logdir, exist_ok=True)
        fname = "larvaci.log" if (name is None) else f"larvaci-{name}.log"
        handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(logdir, fname),
            mode="a",
            maxBytes=2 << 20,  # 1Mb
            backupCount=5
        )
    else:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt="%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.propagate = False
    return logger


def init_logging(verbose=False, logdir=None):
    init_logger(name=None, verbose=verbose, logdir=logdir)
