import asyncio
import json
import os
import httpx
from lxml import etree


class Client:
    client: httpx.AsyncClient = None

    @classmethod
    async def init(cls, client: httpx.AsyncClient):
        cls.client = client

    @classmethod
    async def get(cls, url: str):
        response = None
        for _ in range(5):
            try:
                response = await cls.client.get(url)
            except:
                await asyncio.sleep(3)
        if response is None:
            raise ValueError(f"Unable to fetch URL: {url}")

        if response.status_code != 200:
            raise ValueError(f"Invalid status code({response.status_code}): {url}")
        return response

    @classmethod
    async def get_tree(cls, url: str):
        response = await cls.get(url)
        content = response.text
        tree = etree.HTML(content)
        if tree is None:
            raise ValueError("Invalid HTML")
        return tree


def load_json(file_path: str, default=None) -> dict | list:
    if default is None:
        default = {}

    if not os.path.exists(file_path):
        return default

    with open(file_path, "r") as f:
        return json.load(f)


def save_json(file_path: str, data: dict | list):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)
