#!/usr/bin/env python3
import requests
import logging
import wap
import argparse
from typing import List, Any, Iterator, Tuple
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Thread
from functools import partial
import sys
import json
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


logger = logging.getLogger(__name__)
DONE = -1


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "target",
        help="URL or file with URLs to request",
        nargs="*",
    )

    parser.add_argument(
        "--file",
        help="File with apps regexps",
        default="technologies.json"
    )

    parser.add_argument(
        "--workers", "-w",
        help="Set the number of workers",
        default=10,
        type=int
    )

    parser.add_argument(
        "--confidence", "-c",
        help="Show confidence",
        action="store_true",
    )

    parser.add_argument(
        "--version", "-b",
        help="Show version",
        action="store_true",
    )

    parser.add_argument(
        "--category", "-k",
        help="Show categories",
        action="store_true",
    )

    parser.add_argument(
        "--no-url", "-U",
        help="Hide URL",
        action="store_true",
    )

    parser.add_argument(
        "--delimiter", "-d",
        help="Set fields delimiter",
        default=" "
    )

    parser.add_argument(
        "--json", "-j",
        help="Print in json format",
        action="store_true",
    )

    parser.add_argument(
        "--no-redirect", "-R",
        help="Print in json format",
        action="store_true",
    )

    parser.add_argument(
        "-v",
        dest="verbosity",
        help="Verbosity",
        action="count",
        default=0,
    )

    args = parser.parse_args()
    args.allow_redirects = not args.no_redirect
    args.show_url = not args.no_url

    return args


def main():
    args = parse_args()
    init_log(args.verbosity)
    technologies, categories = wap.load_file(args.file)
    logger.info("Loaded %d technologies", len(technologies))
    logger.info("Loaded %d categories", len(categories))
    logger.info("Workers: %s", args.workers)
    logger.info("Output: %s format", "json" if args.json else "grep")

    pool = ThreadPoolExecutor(args.workers)
    q = Queue()
    t_print = launch_printer(
        q,
        json=args.json,
        delimiter=args.delimiter,
        version=args.version,
        confidence=args.confidence,
        category=args.category,
        url=args.show_url
    )
    request = partial(
        requests.get,
        verify=False,
        allow_redirects=args.allow_redirects
    )
    url_count = 0
    for url in read_text_targets(args.target):
        pool.submit(work, q, request, url, technologies)
        url_count += 1

    logger.info("%s urls requested", url_count)
    pool.shutdown(wait=True)
    q.put((DONE, DONE))
    t_print.join()


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


def read_text_targets(targets: Any) -> Iterator[str]:
    yield from read_text_lines(read_targets(targets))


def read_targets(targets):
    """Function to process the program ouput that allows to read an array
    of strings or lines of a file in a standard way. In case nothing is
    provided, input will be taken from stdin.
    """
    if not targets:
        yield from sys.stdin

    for target in targets:
        try:
            with open(target) as fi:
                yield from fi
        except FileNotFoundError:
            logger.debug("Not found file %s, returning as string", target)
            yield target


def read_text_lines(fd):
    """To read lines from a file and skip empty lines or those commented
    (starting by #)
    """
    for line in fd:
        line = line.strip()
        if line == "":
            continue
        if line.startswith("#"):
            continue

        yield line


def launch_printer(
        q: Queue,
        json: bool = False,
        delimiter: str = " ",
        version: bool = False,
        confidence: bool = False,
        category: bool = False,
        url: bool = False,
):
    handle_results = save_json_results if json else print_results
    results_iter = queue_to_iter(q)
    t_print = Thread(
        target=handle_results,
        args=(
            results_iter,
        ),
        kwargs={
            "version": version,
            "confidence": confidence,
            "category": category,
            "delimiter": delimiter,
            "url": url,
        }
    )
    t_print.start()
    return t_print


def queue_to_iter(
        q: Queue
) -> Iterator[Tuple[str, List[wap.TechMatch]]]:
    """Allows to process the consumption of the queue as an iterator
    """
    while True:
        resp, techno_matches = q.get()
        if resp == DONE:
            return
        yield resp, techno_matches


def print_results(
        results,
        version=False,
        confidence=False,
        category=False,
        delimiter=" ",
        url=False,
):
    """Consumer function to print the matches in a grepable format"""
    for url, techno_matches in results:
        for t in techno_matches:
            fields = []
            if url:
                fields.append(url)

            fields.append(t.technology.name)

            if version:
                fields.append(t.version)

            if confidence:
                fields.append(str(t.confidence))

            if category:
                fields.append(",".join(
                    [c.name for c in t.technology.categories]
                ))

            print(delimiter.join(fields), flush=True)


def save_json_results(
        results,
        version=False,
        confidence=False,
        category=False,
        url=False,
        **kwargs
):
    """Consumer function to print the matches in json format"""
    json_results = []
    for url, techno_matches in results:
        for t in techno_matches:
            fields = {
                "name": t.technology.name,
            }

            if url:
                fields["url"] = url

            if version:
                fields["version"] = t.version

            if confidence:
                fields["confidence"] = t.confidence

            if category:
                fields["categories"] = [
                    c.name for c in t.technology.categories
                ]
            json_results.append(fields)

    print(json.dumps(json_results))


def work(q, request, url, technologies):
    """Main worker function, that perform a HTTP request and
    identifies the technologies in the response. The matches in technologies
    are sent to the queue to be processed.
    """
    try:
        logger.info("Request %s", url)
        resp = request(url)
        matches = wap.discover_requests_technologies(technologies, resp)
        if len(matches) == 0:
            logging.info("%s: No technologies found", resp.url)
        q.put((url, matches))
    except Exception as ex:
        logger.error("Error URL:'%s' => %s", url, str(ex))
        raise


if __name__ == '__main__':
    main()
