from lib.core.github.remote import fetch_github_remote_info, prepare_github_download

async def handle_github_repo():
    await fetch_github_remote_info()

async def handle_github_download():
    await prepare_github_download()

