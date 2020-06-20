import os
import logging
import asyncio
import functools
import time
from .log import init_logger


__FLOWS = {}
__PID_FILE = os.path.join(os.getcwd(), "larvaci.pid")
__LOG_DIR = os.path.join(os.getcwd(), "larvaci-logs")
__WORK_DIR = os.path.join(os.getcwd(), "larvaci-workdir")
__STOP_SIGNALS = ("SIGINT", "SIGTERM")  # these signals will stop service
__GITHUB_TOKEN_VAR = "GITHUB_ACCESS_TOKEN"


def register_flow(flow_cls):
    __FLOWS[flow_cls.__name__] = flow_cls
    return flow_cls


async def main_loop(workdir_base, github_token):
    import signal

    logging.info("Start main loop...")

    flows = []
    tasks = []
    for name, flow_cls in __FLOWS.items():
        workdir = os.path.join(workdir_base, name)
        logdir = os.path.join(workdir, "logs")

        os.makedirs(workdir, exist_ok=True)
        logger = init_logger(name=name, logdir=logdir, verbose=True)

        logging.info(f"Run flow {name} in {workdir}")
        flow = flow_cls(workdir=workdir, logger=logger, github_token=github_token)
        tasks.append(asyncio.create_task(flow._run()))
        flows.append(flow)

    def stop():
        logging.info("Stopping, cancel all tasks...")
        for task in tasks:
            task.cancel()

    eloop = asyncio.get_event_loop()
    for signame in __STOP_SIGNALS:
        eloop.add_signal_handler(getattr(signal, signame), stop)

    done, pending = await asyncio.wait(tasks)
    logging.info("All tasks has been finished")

def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--list",     help="List all registered flows", action="store_true")
    parser.add_argument("-v", "--verbose",  help="Enable debug logs", action="store_true", default=False)
    parser.add_argument("--detach",         help="Fork process", action="store_true", default=False)
    parser.add_argument("--pid-file",       help="File to write PID into", default=None, type=str)
    parser.add_argument("--log-dir",        help="Directory to write logs into", default=None, type=str)
    parser.add_argument("--work-dir",       help="Base working directory", default=__WORK_DIR, type=str)
    parser.add_argument("--github-token",   help="GitHub acces token", type=str)

    args = parser.parse_args()

    if args.list:
        print("\n".join(name for name in __FLOWS.keys()))
        exit(0)

    log_dir = None

    if args.detach:
        if args.pid_file is None:
            args.pid_file = __PID_FILE

        log_dir = os.path.join(args.work_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)

        pid = os.fork()
        if pid:
            print("Process has been forked\n"
                  f"PID={pid}\n"
                  f"PID_FILE={args.pid_file}\n"
                  f"WORK_DIR={args.work_dir}")
            exit(0)

        for f in (sys.stdin, sys.stdout, sys.stderr):
            os.close(f.fileno())

    if args.pid_file is not None:
        with open(args.pid_file, "w") as f:
            f.write(str(os.getpid()))

    init_logger(verbose=args.verbose, logdir=log_dir)
    if args.github_token is None:
        args.github_token = os.environ[__GITHUB_TOKEN_VAR]

    asyncio.run(main_loop(
        workdir_base=args.work_dir,
        github_token=args.github_token
    ))

