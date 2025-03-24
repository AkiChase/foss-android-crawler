from f_droid import crawl_f_droid
from github import crawl_github_info_for_f_droid
import httpx
import asyncio

from util import Client


async def main():
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        await Client.init(client)
        await crawl_f_droid()
        await crawl_github_info_for_f_droid()
    # from github import export_excel
    # from util import load_json
    # export_excel(load_json("github.json"))

if __name__ == "__main__":
    asyncio.run(main())
