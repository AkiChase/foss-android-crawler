import asyncio

from util import Client, load_json, save_json
import openpyxl


async def get_github_repo_info(package: dict) -> dict | None:
    url = package["source"]
    try:
        tree = await Client.get_tree(url)
    except ValueError as e:
        if isinstance(e.args[0], str) and e.args[0].startswith('Invalid status code(404)'):
            package["star"] = "0"
            package["open_issues"] = "0"
            return package
        raise e

    star = tree.xpath('//span[@id="repo-stars-counter-star"]')
    if len(star) == 0:
        star = "0"
    else:
        star = star[0].text

    open_issue = tree.xpath('//span[@id="issues-repo-tab-count"]')
    if len(open_issue) == 0:
        open_issues_count = "0"
    else:
        open_issues_count = open_issue[0].text
    package["star"] = star
    package["open_issues"] = open_issues_count
    return package


async def crawl_github_info_for_f_droid():
    print("Crawling github info for f-droid...")
    f_droid: dict[str, list[dict[str]]] = load_json("f_droid.json")
    github = load_json("github.json", [])

    saved_package_set = set([item["package"] for item in github])
    print(f"Already crawled: {len(saved_package_set)}")

    for index, [category, packages] in enumerate(f_droid.items(), 1):
        len_f_droid = len(packages)
        packages = [
            package for package in packages
            if package.get("source") is not None and package.get("source").startswith("https://github.com")
        ]
        print(f"Crawling category: {category}, all packages: {len_f_droid}, github repos: {len(packages)}")
        packages_in_github = [package for package in packages if package["package"] not in saved_package_set]
        print(f"Crawling details for {len(packages_in_github)} packages...")

        # 分块加载
        block_size = 5
        for i in range(0, len(packages_in_github), block_size):
            tasks = [get_github_repo_info(package) for package in packages_in_github[i:i + block_size]]
            github.extend(await asyncio.gather(*tasks))
            save_json("github.json", github)
            print(
                f"[{index - 1}/{len(f_droid)}][{i + block_size}/{len(packages_in_github)}] Crawled and saved {block_size} packages"
            )
            print("Waiting for 3 second...")
            await asyncio.sleep(3)


def export_excel(data: list, file_path="github.xlsx"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "App Data"

    # 写入表头
    headers = ["Package", "Name", "Summary", "Star", "Open Issues", "Source", "Version", "Time"]
    ws.append(headers)

    # 写入数据
    for item in data:
        package = item.get("package", "")
        name = item.get("name", "")
        summary = item.get("summary", "")
        source = item.get("source", "")
        version = item.get("version", "")
        time = item.get("time", "")

        star = item.get("star", 0)
        if isinstance(star, str):
            if star.endswith("k"):
                star = int(float(star[:-1]) * 1000)
            else:
                star = int(star)

        open_issues = item.get("open_issues", 0)
        if isinstance(open_issues, str):
            if open_issues.endswith("k+"):
                open_issues = int(float(open_issues[:-2]) * 1000)
            elif open_issues.endswith("k"):
                open_issues = int(float(open_issues[:-1]) * 1000)
            else:
                open_issues = int(open_issues)

        ws.append([
            package,
            name,
            summary,
            star,
            open_issues,
            source,
            version,
            time,
        ])

    # 保存文件
    wb.save(file_path)
    print(f"Data successfully exported to {file_path}")
