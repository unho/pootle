.. _api_tp_resources:

Translation project resources
*****************************

The Pootle API exposes a number of resources. Next you have a complete list of
Translation project specific resources.

.. note:: All paths should be appended to the base URL of the API:
   ``<SERVER>/api/<API_VERSION>/``.


.. _api_tp_resources#list_languages_in_project:

Listing languages in a project
==============================

:URL: ``/projects/<PROJ>/languages/``
:Description: Returns the language list on a given ``<PROJ>`` project.
:API versions: 1
:Method: GET
:Returns: Language list on a given ``<PROJ>`` project.

.. code-block:: json

    {
        "meta": {
            "limit": 1000,
            "next": null,
            "offset": 0,
            "previous": null,
            "total_count": 65
        },
        "objects": [
            {
                "code": "af",
                "description": "",
                "description_html": "",
                "fullname": "Afrikaans",
                "id": 3,
                "nplurals": 2,
                "pluralequation": "(n != 1)",
                "resource_uri": "/api/v0.9/language/3/",
                "specialchars": "\u00eb\u00ef\u00ea\u00f4\u00fb\u00e1\u00e9\u00ed\u00f3\u00fa\u00fd"
            },
            {
                "code": "ak",
                "description": "",
                "description_html": "",
                "fullname": "Akan",
                "id": 4,
                "nplurals": 2,
                "pluralequation": "(n > 1)",
                "resource_uri": "/api/v0.9/language/4/",
                "specialchars": "\u025b\u0254\u0190\u0186"
            },
            ...
        ]
    }

