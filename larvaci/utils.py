from . import github as gh
from .flow import FlowBase
import os
import shutil
import time


def are_equal_by_subset(d1, d2, keys):
    for k in keys:
        if d1.get(k) != d2.get(k):
            return False
    return True


def make_rundir(basedir, pr):
    date = time.strftime("%Y%m%dT%H%M%S", time.localtime())
    base_ref = pr["baseRefOid"]
    head_ref = pr["headRefOid"]

    rundir = os.path.join(basedir, f"runs/{date}_{base_ref}_{head_ref}")
    if os.path.exists(rundir):
        shutil.rmtree(rundir)

    os.makedirs(rundir)
    return rundir


class PullRequestProcessorFlowBase(FlowBase):
    REPO_OWNER = None
    REPO_NAME = None
    MAX_ATTEMPTS = 3

    RES_SUCCESS = "success"
    RES_FAILURE = "failure"
    RES_CRASHED = "crashed"

    async def process_pull_request(self, repodir, pr, rundir):
        raise NotImplementedError("process_pull_request() must be implemented in sublcasses")

    def save_processed_pull_request(self, pr, result, attempt):
        pr_context = self.context.setdefault("__pull_requests", [])
        pr_context.append({
            "id": pr["id"],
            "baseRefOid": pr["baseRefOid"],
            "headRefOid": pr["headRefOid"],
            "result": result,
            "attempt": attempt
        })
        del pr_context[:-100]  # remeber 100 recent PRs
    
    def was_pull_request_processed(self, pr):
        for processed in self.context.get("__pull_requests", []):
            if are_equal_by_subset(processed, pr, ("id", "baseRefOid", "headRefOid")):
                return True
        return False
    
    def get_pr_context(self, pr):
        for ctx in self.context.get("__pull_requests", []):
            if are_equal_by_subset(ctx, pr, ("id", "baseRefOid", "headRefOid")):
                return ctx
        return None

    async def run(self):
        repodir = os.path.join(self.workdir, self.REPO_NAME)

        response = await self.github.open_pull_requests(repo_owner=self.REPO_OWNER, repo_name=self.REPO_NAME)

        ssh_url = response["data"]["repository"]["sshUrl"]
        if os.path.isdir(repodir):
            self.logger.debug(f"Check if {repodir} is valid repository...")
            retcode = await self.command.exec(["git", "remote", "-v"], cwd=repodir, noexcept=True)
            if retcode != 0:
                self.logger.warning(f"{repodir} doesn't look like valid repository")
                return  # TODO remove the dir

        if not os.path.isdir(repodir):
            self.logger.info(f"Clone repository into {repodir} ...")
            await self.git.clone(ssh_url, repodir)
            self.logger.info(f"Repository has been cloned into {repodir}")

        prs = [edge["node"] for edge in response["data"]["repository"]["pullRequests"]["edges"]]
        self.logger.debug(f"There are {len(prs)} open PRs")
        for pr in prs:
            ctx = self.get_pr_context(pr)
            if ctx is not None:
                if ctx["result"] == self.RES_SUCCESS:
                    self.logger.debug(f"PR {pr} has been successfully processed")
                    continue
                attempt = ctx["attempt"] + 1
            else:
                attempt = 1

            if attempt > self.MAX_ATTEMPTS:
                self.logger.debug(f"PR {pr} has been tried to process {attempt} times")
                continue

            try:
                rundir = make_rundir(self.workdir, pr)
                self.logger.info(f"Start processing of PR {pr} (rundir={rundir})")
                success = await self.process_pull_request(repodir=repodir, pr=pr, rundir=rundir)
                result = self.RES_SUCCESS if success else self.RES_FAILURE
                self.logger.info(f"PR {pr} was processed, result={result}")
                self.save_processed_pull_request(pr, result, attempt)
                continue
            except Exception:
                self.logger.exception(f"Processing of PR failed with exception")
                await self.github.add_comment(subject_id=pr["id"], content=f"larvaci failed ({attempt} attempt), see logs")
                self.save_processed_pull_request(pr, self.RES_CRASHED, attempt)
