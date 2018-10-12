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

import requests
import json
import sys, re
import logging
import random
from pprint import pprint
from datetime import datetime


class component:
    """
    This is a model for the endpoint item.
    It is initialised from a schema.
    """

    def __init__(self, schema, rnd_seed=None):
        self.schema = schema
        self.mode = ""
        self.uid_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        self.name_chars = "abcdefghijklmnopqrstuvwxyz       ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        self.functions = {
            "array": self.array_component ,
            "object": self.object_component ,
            "integer": self.integer_component ,
            "boolean": self.boolean_component,
            "number": self.number_component,
            "string": self.string_component
        }
        self.location=[]
        self.payload={}
        self.required={}
        self.readonly={}
        self.random_gen=random.Random()
        self.random_gen2=random.Random()
        self.reseed(rnd_seed)

    def reseed(self,rnd_seed):
        self.random_gen.seed(rnd_seed)
        self.random_gen2.seed(datetime.now().microsecond)

    def set_attributes(self,alist,attribute, val="true"):
        """
        we need to map the attribute list, with items in the form
         "<level1>:<level2>:..." (with one or more levels/names)
        to the structure like
         schema['items']['properties'][<level1>]['items']['properties'][<level2>]...
        The last "level" is the item we want to apply the attribute to
        """
        # create a "moving" reference to the schema
        schema_part = self.schema['items']

        # loop over the list of items
        for a_item in alist:
            # drill down through the "levels" (separated by ":")
            for level in a_item.split(':'):
                schema_parent = schema_part
                try:
                    int(level)
                except ValueError:
                    try:
                        schema_part2 = schema_part['properties']
                    except KeyError:
                        schema_part2 = schema_part['items']['properties']
                    schema_part = schema_part2[level]
            if attribute == "required":
                try:
                    schema_parent["required"].append(a_item)
                except KeyError:
                    schema_parent["required"] = [a_item]
                    pprint(schema_parent)
                self.add_requirement(attribute)
            else:
                schema_part[attribute] = "true"
            # If the attribute is "unique" we can rule out that the object is an enum
            if attribute == "unique":
                try:
                    if schema_part["format"] == "enum":
                        # change it to general
                        schema_part["format"] = "general"
                        del schema_part["enum"]
                except KeyError:
                    pass
            if attribute == "maximum":
                try:
                    schema_part["maximum"] == val
                except KeyError:
                    pass
            schema_part = self.schema['items']

    def clear_required(self,schema=None):
        if schema == None:
            schema = self.schema
        self._clearRDict(schema)

    def _clearRList(self,a):
        #print(p)
        cnt=0
        for v in a:
            try:
                if isinstance(v, dict):
                    self._clearRDict(a[cnt])
                elif isinstance(v, list):
                        self._clearRList(a[cnt])
            except (KeyError, IndexError):
                pass
            cnt+=1


    def _clearRDict(self,a):
        for k, v in a.items():
            if k == "required":
                a[k].clear()
            else:
                try:
                    if isinstance(v, dict):
                        self._clearRDict(a[k])
                    elif isinstance(v, list):
                        self._clearRList(a[k])
                except KeyError:
                    pass

    def get_required(self):
        return self.required

    def print_schema(self):
        #print((json.dumps(self.schema , sort_keys=True, indent=2, separators=(',', ': '))))
        pprint(self.schema)

    def get_schema(self):
        return self.schema

    def set_schema(self,schema):
        self.schema = schema

    def add_requirement(self,name):
        self.required[name] = "REQUIRED"
        #print(name,"required")

    def remove_requirement(self,name):
        self.required[name] = "NOT_REQUIRED"

    def get_payload(self):
        return self.payload

    def create_payload(self,mode):
        # generate an example payload
        # compatible with the model schema
        self.mode=mode

        #loop over the schema
        func = self.functions[self.schema['type']]
        # print("in")
        # pprint(self.schema)
        payload=func(self.schema,"",self.random_gen)
        #print("out")
        self.payload = payload
        #return payload

    def array_component(self,schema,name,rnd_gen):
        self.location.append(name)
        # print('/'.join(self.location))
        ret = []

        if len(schema) > 1:
            try:
                # print("PALD 01")
                # print("items_type:", schema['items']['type'])
                func = self.functions[schema['items']['type']]
            except KeyError:
                schema['items']['type'] = "object"
                # print("PALD 02")
                pass

            try:
                func = self.functions[schema['items']['type']]
                for _ in range(1):
                    # print("PALD 03")
                    ret.append(func(schema['items'],"items",self.random_gen))
                    # print("PALD 04")
            except KeyError:
                # print("error creating payload!")
                pass

        self.location.pop()
        return ret

    def object_component(self,schema,name,rnd_gen):
        self.location.append(name)
        #print('/'.join(self.location))
        ret = {}
            #print("-REMOVE REQUIRED: ",schema['required'])
        try:
            for p in schema['properties']:
                # print("  |",self.location, p)

                # as a workaround for "anyOf" we need to just take the first option
                try:
                    if 'anyOf' in schema['properties'][p]:
                        print("FOUND ANYOF")
                        schema['properties'][p] = schema['properties'][p]['anyOf'][0]
                        # pprint(schema['properties'][p])
                except:
                    print("keyerror FOUND ANYOF")
                    pass

                #is it required according to the schema?
                if self.mode == "full":
                    try:
                        func = self.functions[schema['properties'][p]['type']]
                        ret.update({p:func(schema['properties'][p],p,self.random_gen)})
                    except KeyError:
                        # print("full mode key error")
                        pass
                if self.mode == "required":
                    try:
                        for r in schema['required']:
                            if r == p:
                                func = self.functions[schema['properties'][p]['type']]
                                ret.update({p:func(schema['properties'][p],p,self.random_gen)})
                    except KeyError:
                        # print("required key error")
                        pass
                if self.mode == "minimal":
                    try:
                        if p in schema['required']:
                            func = self.functions[schema['properties'][p]['type']]
                            ret.update({p:func(schema['properties'][p],p,self.random_gen)})
                    except KeyError:
                        # print("minimal key error")
                        pass
                if self.mode == "writable":
                    writable=True
                    try:
                        if schema['properties'][p]['readOnly'] == True:
                            #print(p,"readonly")
                            writable=False
                    except KeyError:
                        # print("writable key error")
                        pass
                    if writable:
                        #print(p,"\n- writable")
                        try:
                            func = self.functions[schema['properties'][p]['type']]
                            try:
                                if schema['properties'][p]['unique'] == "true":
                                    #print("- unique")
                                    ret.update({p:func(schema['properties'][p],p,self.random_gen2)})
                            except KeyError:
                                ret.update({p:func(schema['properties'][p],p,self.random_gen)})
                        except KeyError:
                            # print("if writable key error")
                            pass
        except KeyError:
            print("opject with no properties")
            #no properties - could be an empty object - PALD: NEED TO DEAL WITH THIS
            pass

        #if self.mode == "minimal":
            #print("=REMOVE REQUIRED: ",schema['required'])
        if len(self.location):
            self.location.pop()
        return ret

    def integer_component(self,schema,name,rnd_gen):
        self.location.append(name)
        #print('/'.join(self.location))
        val = "integer"
        val = schema['max']
        self.location.pop()
        return val

    def boolean_component(self,schema,name,rnd_gen):
        self.location.append(name)
        #print('/'.join(self.location))
        val = False
        if self.mode in ["full","minimal","writable"]:
            val = True
        self.location.pop()
        return val

    def number_component(self,schema,name,rnd_gen):
        self.location.append(name)
        #print('/'.join(self.location))
        val = "number"
        val = schema['max']
        self.location.pop()
        return val

    def string_component(self,schema,name,rnd_gen):
        self.location.append(name)
        #print('/'.join(self.location))

        # Set format to general if none exists
        try:
            if schema['format'] == None:
                schema['format'] = "general"
        except KeyError:
            schema['format'] = "general"




        # find the maximum
        maxTypes = []
        this_max = 255   # sensible default
        for a in schema:
            maxTypes.append(a)

        if len(maxTypes) > 0:
            if "maximum" in maxTypes:
                # we just use this one, unless it is "None"
                if schema["maximum"] == None:
                    if "maxLength" in maxTypes:
                        # use maxLength instead
                        this_max = schema["maxLength"]
                    elif "max" in maxTypes:
                        # use maximum instead
                        this_max =  schema["max"]
                else:
                    this_max = schema["maximum"]
            elif "maximum" in maxTypes:
                this_max =  schema["maximum"]
            elif "maxLength" in maxTypes:
                this_max = schema["maxLength"]

        try:
            if float(this_max) >= 2147483647:
                this_max = 255  # keep it sensible (but recognisable) for now!
        except ValueError:
            this_max = 1
            pass


        #finally put it back into schema['max']
        schema["maximum"] = this_max

        val = "string"
        if schema['format'] == "enum":
            val = "ENUMTEST"
            try:
                selection = schema['enum']
                val = selection[rnd_gen.randint(0,len(selection)-1)]
            except KeyError:
                pass
        if schema['format'] == "date-time":
            val = "2014-03-02T03:07:54.855"
        if schema['format'] == "coordinates":
            val = "[[-12.439,8.2729],[-12.4362,8.2706]]"
        if schema['format'] == "double":
            val = rnd_gen.uniform(schema["minimum"],schema["maximum"])
        if schema['format'] == "access":
            val = "rw------"
        if schema['format'] == "uid":
            val = ""
            for _ in range(11):
                val += self.uid_chars[rnd_gen.randint(0,len(self.uid_chars)-1)]
        if schema['format'] == "url":
            val = "http://play.dhis2.org/api/example"
        if schema['format'] == "general":
            val = ""
            for _ in range(int(schema['maximum'])):
                val += self.name_chars[rnd_gen.randint(0,len(self.name_chars)-1)]

        try:
            if schema['association'] == "true":
                # use example as the input
                val = schema['example']
                #logger.info("example: "+val)
        except KeyError:
            pass
        self.location.pop()
        return val
