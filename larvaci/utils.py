from . import github as gh
from .flow import FlowBase
import os


def are_equal_by_subset(d1, d2, keys):
    for k in keys:
        if d1.get(k) != d2.get(k):
            return False
    return True


class PullRequestProcessorFlowBase(FlowBase):
    REPO_OWNER = None
    REPO_NAME = None

    async def process_pull_request(self, repodir, pr):
        raise NotImplementedError("process_pull_request() must be implemented in sublcasses")

    def save_processed_pull_request(self, pr, success):
        pr_context = self.context.setdefault("__pull_requests", [])
        pr_context.append({
            "id": pr["id"],
            "baseRefOid": pr["baseRefOid"],
            "headRefOid": pr["headRefOid"],
            "success": success
        })
        del pr_context[:-100]
    
    def was_pull_request_processed(self, pr):
        for processed in self.context.get("__pull_requests", []):
            if are_equal_by_subset(processed, pr, ("id", "baseRefOid", "headRefOid")):
                return True
        return False

    async def run(self):
        repodir = os.path.join(self.workdir, self.REPO_NAME)

        response = await self.github.request(
            gh.pull_requests(
                repo_owner=self.REPO_OWNER, repo_name=self.REPO_NAME, states=[gh.PullRequestState.OPEN]
            )
        )

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
            if self.was_pull_request_processed(pr):
                self.logger.debug(f"PR {pr} has been processed")
                continue
            self.logger.debug(f"PR {pr} has not been processed")
            try:
                self.logger.info(f"Start processing of PR {pr} ...")
                success = await self.process_pull_request(repodir, pr)
                self.logger.info(f"PR {pr} was processed, success={success}")
                self.save_processed_pull_request(pr, success)
                continue
            except Exception:
                # exception here means internal flow error, PR will be reprocessed on the next iteration
                self.logger.exception(f"Processing of PR failed with exception")
            await self.github.request(gh.add_comment(
                subject_id=pr["id"],
                content="larvaci failed, see logs"
            ))
