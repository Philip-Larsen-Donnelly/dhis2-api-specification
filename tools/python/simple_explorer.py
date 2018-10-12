#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 18 15:34:25 2018

Copyright (c) 2018, University of Oslo
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.
* Neither the name of the HISP project nor the names of its contributors may
  be used to endorse or promote products derived from this software without
  specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE

@author: philld
"""

from dhis2api.explorer import endpoint_explorer
import json
import jsonref

if __name__ == "__main__":
    components = {}
    #mypaths = ["constants","dashboards", "categoryCombos","categories", "categoryOptions","me"]
    mypaths = ["organisationUnits","constants","dashboards","trackedEntityInstances","categoryCombos","categories", "categoryOptions"]
    #mypaths = ["constants"]

    specfile="../../docs/spec/openapi.json"
    ofile=open(specfile,'r')
    openapi = json.load(ofile)
    ofile.close()

    # paths = openapi["paths"]
    # for p in paths:
    #     mypaths.append(p.strip('/'))

    for path in mypaths:
        print("PATH________________________________:",path)
        epx = endpoint_explorer("http://localhost:8080",path,openapi)
        epx.explore()
        openapi = epx.get_schema()

        outfile= open("schema_out.json",'w')
        #outfile.write(json.dumps(openapi , sort_keys=True, indent=2, separators=(',', ': ')))
        json.dump(openapi,outfile)
        outfile.close()
