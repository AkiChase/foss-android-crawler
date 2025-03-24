import asyncio
import math
import re
from lxml import etree
from util import Client, load_json, save_json


async def get_all_categories():
    home_page = "https://f-droid.org/en/packages/"
    response = await Client.get(home_page)
    content = response.text
    pattern = r'<a href="/en/categories/([^/]+)/">Show all ([0-9,]+) packages'
    out = []
    for match in re.finditer(pattern, content):
        category = match.group(1)
        num = int(match.group(2).replace(",", ""))
        out.append((category, num))
    return out


async def _get_rest_page_packages_in_category(url: str):
    tree = await Client.get_tree(url)
    package_list = tree.xpath('//div[@id="news-content"]//a[@class="post-link"]')
    out = []
    for node in package_list:
        href: str = node.get("href")
        if href.endswith("/index.html"):
            href = href[:-10]
        package = href.strip("/").split("/")[-1]
        out.append(package)
    return out


async def get_all_packages_in_category(category: str, num: int):
    out = []

    # first page
    url = f"https://f-droid.org/en/categories/{category}/"
    tree = await Client.get_tree(url)
    package_list = tree.xpath('//a[@class="package-header"]')
    for node in package_list:
        package = node.get("href").strip("/").split("/")[-1]
        out.append(package)

    rest_page_list = [f"https://f-droid.org/en/categories/{category}/{i}/index.html" for i in
                      range(2, math.ceil(num / 30) + 1)]
    tasks = [_get_rest_page_packages_in_category(url) for url in rest_page_list]
    rest = await asyncio.gather(*tasks)
    for page in rest:
        out.extend(page)
    return out


async def get_package_details(package: str):
    url = f"https://f-droid.org/en/packages/{package}/index.html"
    response = await Client.get(url)
    content = response.text
    tree = etree.HTML(content)
    if tree is None:
        raise ValueError("Invalid HTML")

    name = tree.xpath('//h3[@class="package-name"]')[0].text.strip()
    summary = tree.xpath('//div[@class="package-summary"]')[0].text.strip()
    latest_version_node = tree.xpath('//li[@id="latest"]//div[@class="package-version-header"]')[0]
    version = latest_version_node.xpath('.//a[1]')[0].get("name")
    time_info = latest_version_node.xpath('./text()')[-1].strip()
    source = re.search(r'<a href="(.*?)">Source Code', content)
    if source is not None:
        source = source.group(1)
    else:
        source = None

    return {
        "package": package,
        "name": name,
        "summary": summary,
        "source": source,
        "version": version,
        "time": time_info,
    }


async def crawl_f_droid():
    f_droid = load_json("f_droid.json")

    print("Get all categories...")
    categories = await get_all_categories()
    print(f"Num of categories: {len(categories)}")
    for index, [category, num] in enumerate(categories, 1):
        if category not in f_droid:
            f_droid[category] = []
        elif len(f_droid[category]) >= num:
            print(f"[{index}/{len(categories)}] Category {category} already crawled")
            continue

        saved_packages_set = set([item["package"] for item in f_droid[category]])
        print(f"Crawling category: {category}, expected packages: {num}")
        packages = await get_all_packages_in_category(category, num)
        print(f"Get {len(packages)} packages in {category}")

        print(f"Already crawled: {len(saved_packages_set)}")
        # 过滤已加载的
        packages = [p for p in packages if p not in saved_packages_set]
        print(f"Crawling details for {len(packages)} packages...")

        # 分块加载
        block_size = 10
        for i in range(0, len(packages), block_size):
            tasks = [get_package_details(package) for package in packages[i:i + block_size]]
            f_droid[category].extend(await asyncio.gather(*tasks))
            save_json("f_droid.json", f_droid)
            print(
                f"[{index - 1}/{len(categories)}][{i + block_size}/{len(packages)}] Crawled and saved {block_size} packages")
            print("Waiting for 1 second...")
            await asyncio.sleep(1)

        print(f"[{index}/{len(categories)}] Category {category} crawled and saved")

    return f_droid
