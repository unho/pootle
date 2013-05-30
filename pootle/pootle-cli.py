# -*- coding: utf-8 -*-
#
# Copyright 2013 Zuza Software Foundation
#
# This file is part of Pootle.
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, see <http://www.gnu.org/licenses/>.

import slumber


# Change the following to match your Pootle URL, your username and password.
API_URL = "http://127.0.0.1:8000/api/v1/"
#AUTH=('usuario', 'usuario')
AUTH=('admin', 'admin')

api = slumber.API(API_URL, auth=AUTH)


# TODO Add another repo with a pootle-cli client capable of interacting with all the Pootle API.


## Delete a particular language
#api.languages(135).delete()


# Get all languages data.
lang_data = api.languages.get()

#for lang in lang_data["objects"]:
#    print(lang["code"])

print("\n%d languages\n" % len(lang_data["objects"]))

#print(type(lang_data)) # Type is dict

#TODO pip install simplejson
#import simplejson as json
#print(json.dumps(lang_data, sort_keys=True, indent=4, separators=(',', ': ')))



## Add a new language
#nlang = {
#    "code": "aby",
#    "description": "ayyzzd",
#    "fullname": "Ayy (eyyz)",
#    "nplurals": 2,
#    "pluralequation": "(n != 1)",
#    "specialchars": ""
#}
#new = api.languages.post(nlang)

#print("Type is:")
#print(type(new))


## Get a particular language
#n95 = api.languages(135).get()
##print(n95["id"])
#print(n95)


## Change an existing language
#clang = {
#    "description": "new description for this lang",
#    "fullname": "zu Lang name (in here)",
#    "specialchars": "áè"
#}
#api.languages(95).patch(clang)


## Change an existing language
#clang = {
#    "description": "new descdsfdsf this lang",
#    "fullname": "zu aaavikl",
#    "specialchars": "áè"
#}
#api.languages(95).put(clang)




## Add a new language
#nlang = {
#    "code": "aby",
#    "description": "ayyzzd",
#    "fullname": "Ayy (eyyz)",
#    "nplurals": 2,
#    "pluralequation": "(n != 1)",
#    "specialchars": ""
#}
#new = api.languages.post(nlang)


#sugg_data = api.suggestions(3).get()

#print sugg_data

#print(type(sugg_data)) # Type is dict



## Add a new project
#nproj = {
#    "checkstyle": "standard",
#    "code": "ayyzzd",
#    "description": "",
##    "directory": "10",
#    "fullname": "New proj from slumber",
##    "ignoredfiles": "",
##    "localfiletype": "po",
##    "report_target": "",
#    "source_language": "/api/v1/languages/20/",
##    "treestyle": "nongnu"
#}
#newproj = api.projects.post(nproj)


##curl --basic --user admin:admin --verbose --dump-header - -H "Content-Type: application/json" -X POST --data '{"checkstyle": "standard", "code": "ayyzzd", "description": "", "fullname": "New proj from slumber", "source_language": "/api/v1/languages/20/"}' --url http://localhost:8000/api/v1/projects/


#print("Type is:")
#print(type(newproj))

