import os
import re
import urlparse
import tempfile

import requests

from lib.settings import (
    logger,
    set_color,
    DEFAULT_USER_AGENT,
    proxy_string_to_dict,
    DBMS_ERRORS,
    create_tree,
)


def __load_payloads(filename="{}/etc/xss_payloads.txt"):
    with open(filename.format(os.getcwd())) as payloads: return payloads.readlines()


def create_urls(url, payload_list):
    tf = tempfile.NamedTemporaryFile(delete=False)
    tf_name = tf.name
    with tf as tmp:
        for payload in payload_list:
            loaded_url = "{}{}".format(url, payload)
            tmp.write(loaded_url)
    return tf_name


def find_xss_script(url, query=4, fragment=5):
    data = urlparse.urlparse(url)
    if data[fragment] is not "" or None:
        return "{}{}".format(data[query], data[fragment])
    else:
        return data[query]


def scan_xss(url, agent=None, proxy=None):
    user_agent = agent or DEFAULT_USER_AGENT
    config_proxy = proxy_string_to_dict(proxy)
    config_headers = {"connection": "close", "user-agent": user_agent}
    xss_request = requests.get(url, proxies=config_proxy, headers=config_headers)
    html_data = xss_request.content
    query = find_xss_script(url)
    for db in DBMS_ERRORS.keys():
        for item in DBMS_ERRORS[db]:
            if re.findall(item, html_data):
                return "sqli", db
    if query in html_data:
        return True, None
    return False, None


def main_xss(start_url, verbose=False, proxy=None, agent=None):
    find_xss_script(start_url)
    logger.info(set_color(
        "loading payloads..."
    ))
    payloads = __load_payloads()
    if verbose:
        logger.debug(set_color(
            "a total of {} payloads loaded...".format(len(payloads)), level=10
        ))
    logger.info(set_color(
        "payloads will be written to a temporary file and read from there..."
    ))
    filename = create_urls(start_url, payloads)
    logger.info(set_color(
            "loaded URL's have been saved to '{}'...".format(filename)
        ))
    logger.info(set_color(
        "testing for XSS vulnerabilities on host '{}'...".format(start_url)
    ))
    if proxy is not None:
        logger.info(set_color(
            "using proxy '{}'...".format(proxy)
        ))
    success = set()
    with open(filename) as urls:
        for i, url in enumerate(urls.readlines(), start=1):
            url = url.strip()
            result = scan_xss(url, proxy=proxy, agent=agent)
            payload = find_xss_script(url)
            if verbose:
                logger.info(set_color(
                    "trying payload '{}'...".format(payload)
                ))
            if result[0] != "sqli" and result[0] is True:
                success.add(url)
                if verbose:
                    logger.debug(set_color(
                        "payload '{}' appears to be usable...".format(payload), level=10
                    ))
            elif result[0] is "sqli":
                if i <= 1:
                    logger.error(set_color(
                        "loaded URL '{}' threw a DBMS error and appears to be injectable, test for SQL injection, "
                        "backend DBMS appears to be '{}'...".format(
                            url, result[1]
                        ), level=40
                    ))
            else:
                if verbose:
                    logger.debug(set_color(
                        "host '{}' does not appear to be vulnerable to XSS attacks with payload '{}'...".format(
                            start_url, payload
                        ), level=10
                    ))
    if len(success) != 0:
        logger.info(set_color(
            "possible XSS scripts to be used:"
        ))
        create_tree(start_url, list(success))
    else:
        logger.error(set_color(
            "host '{}' does not appear to be vulnerable to XSS attacks...".format(start_url)
        ))