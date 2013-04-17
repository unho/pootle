.. _api:

Pootle API
**********

Pootle provides a REST API for interacting with it using external tools,
allowing those to retrieve data, for example translation stats, or save data to
Pootle, e.g. translations. This reference document is written for those
interested in:

* Developing software to use this API
* Integrating existing software with this API
* Exploring API features in detail


.. _api#how_to_perform_queries:

How to perform API queries
==========================

The API can be queried using URLs like:

http://pootle.locamotion.org/api/languages/

The structure of the URLs is as follows::

  $(SERVER)/api/$(API_VERSION)/$(QUERY)

Where:

+--------------+---------------------------------------+
| SERVER       | The URL of the Pootle server          |
+--------------+---------------------------------------+
| API_VERSION  | Version number of the API             |
+--------------+---------------------------------------+
| QUERY        | Resource query URI                    |
+--------------+---------------------------------------+


.. _api#authentication:

Authentication
==============

Pootle API requires authentication for accessing the API.

The method used for authentication is providing an username and an API key with
each request. The API key can be seen on each user private dashboard in Pootle,
for example ``http://pootle.locamotion.org/accounts/edit/``.


.. _api#authentication:

Formats
=======

By default Pootle API returns only `JSON <http://en.wikipedia.org/wiki/JSON>`_
replies. It is possible to use all the `formats supported
<http://django-tastypie.readthedocs.org/en/latest/settings.html#tastypie-default-formats>`_
by `Tastypie <http://tastypieapi.org/>`_.


.. _api#authentication:

Tools and libraries
===================

There are several `libraries and programs
<http://django-tastypie.readthedocs.org/en/latest/tools.html#python>`_ that are
capable of interacting with Pootle API. For example here is an example script
that uses Slumber to retrieve and print the list of used languages in Pootle.

.. code-block:: python

  import slumber

  # Change the following to match your Pootle URL, your username and API key.
  API_URL = "http://127.0.0.1:8000/api/v0.9/"
  ARGS = {
      'username': "username",
      'api_key': "70357b9a605abdae0c3db15346f1d866fa3222fe",
  }

  api = slumber.API(API_URL)
  lang_data = api.language.get(**ARGS)

  for lang in lang_data["objects"]:
      print(lang["code"])


.. note:: Remember to `install Slumber <http://slumber.readthedocs.org/>`_ in
   order to run the previous code.


.. TODO add another repo with a pootle-cli client capable of interacting with
   all the Pootle API.


.. _api#authentication:

Available resources
===================

The Pootle API exposes a number of resources. Next you have a complete list of
them with data about the accepted HTTP methods, result limits, authentication
requirements or other constraints.

.. note:: All paths should be appended to the base URL of the API:
   ``$(SERVER)/api/$(API_VERSION)/``.


Listing languages in a project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:URL: ``/projects/PROJECT/languages/``
:Description: Returns the language list on a given ``PROJECT`` project.
:API versions: 1
:Method: GET
:Returns: Language list on a given ``PROJECT`` project.

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
            }
        ]
    }


