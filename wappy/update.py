import os
import logging
import requests
import argparse
import re
import json
from .md5 import md5, get_file_md5

logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Update the technologies rules used by wappy."
    )

    source_group = parser.add_mutually_exclusive_group()

    source_group.add_argument(
        "-u", "--url",
        help="URL to retrieve the technologies file",
        default="https://github.com/AliasIO/wappalyzer/tree/master/src/technologies"
    )

    source_group.add_argument(
        "-f", "--file",
        help="File with technologies regexps",
        type=argparse.FileType('rb'),
    )

    parser.add_argument(
        "-c", "--check",
        action="store_true",
        help="Just check if update is required, without update",
    )

    parser.add_argument(
        "-v",
        dest="verbosity",
        help="Verbosity",
        action="count",
        default=0,
    )

    args = parser.parse_args()
    return args


def get_technologies_from_github(content):
    exp = r'<a class="js-navigation-open Link--primary" title=".*?\.json" data-pjax="#repo-content-pjax-container" href="\/AliasIO\/wappalyzer\/blob\/master\/src\/technologies\/.*?\.json">(.*?\.json)<\/a>'
    tech_folder = "https://raw.githubusercontent.com/AliasIO/wappalyzer/master/src/technologies"
    json_files = re.findall(exp, content)
    return [f"{tech_folder}/{json_file}" for json_file in json_files]


def merge_into_json_schema(categories, technologies):
    return {
        "$schema": "../schema.json",
        "categories": categories,
        "technologies": technologies
    }


def pack_technologies_json_files(files):
    technologies = {}
    for file in files:
        res = requests.get(file)
        technologies = dict(res.json(), **technologies)
    categories = requests.get("https://raw.githubusercontent.com/AliasIO/wappalyzer/master/src/categories.json").json()
    schema = merge_into_json_schema(categories, technologies)
    return json.dumps(schema, indent=2).encode('utf-8')


def main():
    args = parse_args()
    init_log(args.verbosity)
    script_dir = os.path.dirname(os.path.realpath(__file__))
    target_file = os.path.join(script_dir, "technologies.json")

    current_md5 = get_file_md5(target_file)
    logger.info("Current file MD5: %s", current_md5)

    if args.file:
        content = args.file.read()
    else:
        try:            
            res = requests.get(args.url)
            files = get_technologies_from_github(res.text)
            content = pack_technologies_json_files(files)
        except Exception as ex:
            logger.error("Error retrieving file from '%s': %s", args.url, ex)
            return -1

    new_md5 = md5(content)
    logger.info("New file MD5: %s", new_md5)

    if current_md5 != new_md5:
        if args.check:
            print("Update required")
        else:
            update_file(target_file, content)
            print("Update successful")
    else:
        print("No update required")


def init_log(verbosity=0, log_file=None):

    if verbosity == 1:
        level = logging.WARN
    elif verbosity == 2:
        level = logging.INFO
    elif verbosity > 2:
        level = logging.DEBUG
    else:
        level = logging.CRITICAL

    logging.basicConfig(
        level=level,
        filename=log_file,
        format="%(levelname)s:%(name)s:%(message)s"
    )


def update_file(filepath, content):
    with open(filepath, 'wb') as fo:
        fo.write(content)


if __name__ == '__main__':
    exit(main())
