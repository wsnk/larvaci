from .command import Command


class Git:
    def __init__(self, git_path="git", logger=None):
        self.git_path = git_path
        self.cmd = Command(logger=logger)

    async def run(self, args, cwd=None):
        args.insert(0, self.git_path)
        await self.cmd.exec(args, cwd=cwd)

    async def clone(self, url, dst_dir, branch=None):
        return await self.run(["clone", url, dst_dir])

    async def clean(self, repo_dir):
        return await self.run(["clean", "--force", "-d", "-x"], cwd=repo_dir)

    async def checkout(self, repo_dir, revision):
        return await self.run(["checkout", "--force", revision], cwd=repo_dir)

    async def fetch(self, repo_dir):
        return await self.run(["fetch", "--force"], cwd=repo_dir)

    async def submodule_init(self, repo_dir):
        return await self.run(["submodule", "update", "--init", "--recursive"], cwd=repo_dir)

    async def submodule_deinit(self, repo_dir):
        return await self.run(["submodule", "deinit", "--force", "--all"], cwd=repo_dir)