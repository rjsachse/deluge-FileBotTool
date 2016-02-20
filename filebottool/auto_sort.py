"""
Module that watches for finished torrents and decides if filebottool should
sort them.
"""
__author__ = 'laharah'

import re
from collections import namedtuple

# noinspection PyUnresolvedReferences
import deluge.component as component

from filebottool.common import Log

log = Log()

VALID_FIELDS = ['label', 'tracker', 'save_path', 'file path']

OPERATOR_MAP = {
    "is exactly": lambda x, y: x == y,
    "contains": lambda x, y: y in x,
    "starts with": lambda x, y: x.startswith(y),
    "ends with": lambda x, y: x.endswith(y),
    "matches(regex)": lambda x, y: re.search(y, x),
}

FilterRule = namedtuple("FilterRule", ["id", "field", "operator", "value",
                                       "handler_name"])


def check_rules(torrent_id, sorting_rules):
    """
    match sorting rules to a torrent id and get appropriate handler
    Args:
        torrent_id: torrent_id
        sorting_rules: list of rule tuples

    Returns: handler name or None
    """
    core = component.get('Core')
    sorting_rules = [FilterRule(*rule) for rule in sorting_rules]

    for rule in sorted(sorting_rules):
        if rule.field == 'file path':  # special handeling for file path
            files = component.get('TorrentManager')[torrent_id].get_files()
            for f in files:
                if OPERATOR_MAP[rule.operator](f['path'], rule.value):
                    logline ='Torrent:file {0}:{1} matched rule {2}'
                    log.info(logline.format(torrent_id, f['path'], rule.id))
                    return rule.handler_name

        elif OPERATOR_MAP[rule.operator](
                core.get_torrent_status(torrent_id, [rule.field])[rule.field],
                rule.value):
            log.info("Torrent {0} matched rule {1}".format(torrent_id, rule.id))
            return rule.handler_name

    else:
        log.debug("No rule filter matched for torrent {}".format(torrent_id))
        return None