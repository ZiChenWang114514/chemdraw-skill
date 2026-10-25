"""Parse Office package XML without expanding entities or loading DTDs.

Office files come from users and mail; a part with an entity declaration must not
expand into a large tree or reach the network.
"""

from __future__ import annotations


def fromstring(data):
    from lxml import etree

    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    return etree.fromstring(data, parser)
