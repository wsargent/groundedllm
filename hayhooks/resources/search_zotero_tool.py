import os
from typing import List

import requests


def search_zotero(query: List[dict]) -> str:
    """Search the Zotero database using a MongoDB-style query object or a list of query objects logically ANDed together.

    An example zotero item in Python looks like this:

        {u'ISBN': u'0810116820',
           u'abstractNote': u'',
           u'accessDate': u'',
           u'archive': u'',
           u'archiveLocation': u'',
           u'callNumber': u'HIB 828.912 BEC:3g N9',
           u'collections': [u'2UNGXMU9'],
           u'creators': [{u'creatorType': u'author',
                          u'firstName': u'Daniel',
                          u'lastName': u'Katz'}],
           u'date': u'1999',
           u'dateAdded': u'2010-01-04T14:50:40Z',
           u'dateModified': u'2014-08-06T11:28:41Z',
           u'edition': u'',
           u'extra': u'',
           u'itemType': u'book',
           u'key': u'VDNIEAPH',
           u'language': u'',
           u'libraryCatalog': u'library.catalogue.tcd.ie Library Catalog',
           u'numPages': u'',
           u'numberOfVolumes': u'',
           u'place': u'Evanston, Ill',
           u'publisher': u'Northwestern University Press',
           u'relations': {u'dc:replaces': u'http://zotero.org/users/436/items/9TXN8QUD'},
           u'rights': u'',
           u'series': u'',
           u'seriesNumber': u'',
           u'shortTitle': u'Saying I No More',
           u'tags': [{u'tag': u'Beckett, Samuel', u'type': 1},
                     {u'tag': u'Consciousness in literature', u'type': 1},
                     {u'tag': u'English prose literature', u'type': 1},
                     {u'tag': u'Ireland', u'type': 1},
                     {u'tag': u'Irish authors', u'type': 1},
                     {u'tag': u'Modernism (Literature)', u'type': 1},
                     {u'tag': u'Prose', u'type': 1},
                     {u'tag': u'Self in literature', u'type': 1},
                     {u'tag': u'Subjectivity in literature', u'type': 1}],
           u'title': u'Saying I No More: Subjectivity and Consciousness in The Prose of Samuel Beckett',
           u'url': u'',
           u'version': 792,
           u'volume': u''},
           u'key': u'VDNIEAPH',
           u'library': {u'id': 436,
                        u'links': {u'alternate': {u'href': u'https://www.zotero.org/urschrei',
                                                    u'type': u'text/html'}},
                        u'name': u'urschrei',
                        u'type': u'user'},
           u'links': {u'alternate': {u'href': u'https://www.zotero.org/urschrei/items/VDNIEAPH',
                                    u'type': u'text/html'},
                        u'self': {u'href': u'https://api.zotero.org/users/436/items/VDNIEAPH',
                                u'type': u'application/json'}},
           u'meta': {u'creatorSummary': u'Katz',
                    u'numChildren': 0,
                    u'parsedDate': u'1999-00-00'},
           u'version': 792}

    Args:
        query (List[dict]): The MongoDB-style query object(s) to search for. Keys are field paths and values are the values to match.
            If more than one query object is provided, they are logically ANDed together (all must match).

            Examples:
            - [{"DOI": "10.3389/fnins.2012.00138"}] matches items where data.DOI equals "10.3389/fnins.2012.00138"
            - [{"url": "http://journal.frontiersin.org/article/10.3389/fnins.2012.00138/abstract"}] matches items.
            - [{"shortTitle": "foo"}] matches items where data.shortTitle equals "foo"
            - [{"title": "Example Paper"}] matches items where data.title equals "Example Paper"
            - [{"creators.lastName": "Brooker"}] matches items where any creator has lastName "Brooker"
            - [{"title": "Example Paper"}, {"DOI": "10.1234/test"}] matches items where both conditions are true

    Returns:
        str: A list of matching Zotero items as JSON objects.
            Use the extract tool with an item's URL to extract the full text content.
            Use the excerpt tool with several items URLs to ask an LLM a question about the items.
    """

    hayhooks_base_url = os.getenv("HAYHOOKS_BASE_URL")
    response = requests.post(
        f"{hayhooks_base_url}/search_zotero/run",
        json={"query": query},  # Keep the parameter name as "jsonpath" for backward compatibility
    )
    response.raise_for_status()
    json_response = response.json()

    if "result" in json_response:
        result = json_response["result"]
        return result
    else:
        return f"Internal error: {json_response}"
