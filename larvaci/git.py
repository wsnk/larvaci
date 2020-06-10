from .command import Command


class Git:
    def __init__(self, git_path="git", logger=None):
        self.git_path = git_path
        self.cmd = Command(logger=logger)

    async def run(self, args, cwd=None):
        args.insert(0, self.git_path)
        await self.cmd.run(args, cwd=cwd)
        retcode = await self.cmd.wait()
        if retcode != 0:
            raise RuntimeError(f"git command failed with code = {retcode}")

    async def clone(self, url, dst_dir, branch=None):
        opts = ["--recurse-submodules", "--shallow-submodules"]
        if branch is not None:
            opts += ["--branch", branch]
        return await self.run(["clone"] + opts + [url, dst_dir])

    async def checkout(self, repo_dir, revision):
        return await self.run(["checkout", "--force", revision], cwd=repo_dir)
