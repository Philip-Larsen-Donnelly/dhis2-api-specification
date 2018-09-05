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

from dhisapi import apicall,ep_model
from genson import SchemaBuilder
import psycopg2
from jsonschema import Draft4Validator
import json, re


class diff_checker:

    def __init__(self,a,b):
        self.a = a
        self.b = b
        self.path = []
        self.diffs = []

    def get_difflist(self):
        return self.diffs

    def diffList(self,a,b):
        #print(p)
        cnt=0
        for v in a:
            self.path.append(str(cnt))
            try:
                if isinstance(v, dict):
                    self.diffDict(v,b[cnt])
                else:
                    if isinstance(v, list):
                        self.diffList(v,b[cnt])
                    else:
                        if v != b[cnt]:
                            #print("list[",':'.join(self.path),"]","!=",b[cnt],"READONLY")
                            self.diffs.append(':'.join(self.path))
            except (KeyError, IndexError):
                #print("[",':'.join(self.path),"]","removed")
                self.diffs.append(':'.join(self.path))
            cnt+=1
            self.path.pop()
            

    def diffDict(self,a,b):
        for k, v in a.items():
            self.path.append(k)
            try:
                if isinstance(v, dict):
                    self.diffDict(v,b[k])
                else:
                    if isinstance(v, list):
                        self.diffList(v,b[k])
                    else:
                        if v != b[k]:
                            #print("dict[",':'.join(self.path),"]","value:",str(v),"!=",str(b[k]),"READONLY")
                            self.diffs.append(':'.join(self.path))
            except KeyError:
                #print("[",':'.join(self.path),"]","removed")
                self.diffs.append(':'.join(self.path))
            self.path.pop()

    def report_diffs(self):
        if isinstance(self.a, dict):
            self.diffDict(self.a,self.b)
        if isinstance(self.a,list):
            self.diffList(self.a,self.b)


class ep_explorer():

    def __init__(self,dhis2instance,ep):
        self.dhis2instance = dhis2instance
        self.endpoint = ep
        self.mode = "ENG"
        self.ep_model = None
        self.builder = SchemaBuilder(False)
        self.schema = None
        self.created = [] # keep a list of entries we create, so that we can clean up
        self.verbose = False
        self.array_based = True # some EPs return arrays of items, others are single objects
        self.apicall = None # re-usable apicall member
        self.apiresponsej = ""
        self.apiresponse = None
        self.invalid_methods = []
        self.errors = set()
        self.error_codes = {
            "E4000": {"type":"required","identifier":"errorProperty"},
            "E5000": {"type":"unique","identifier":"ID"},
            "E5002": {"type":"dependency","identifier":"message"},
            "E5003": {"type":"unique","identifier":"errorProperty"}
        }

    def set_instance(self,dhis2instance):
        self.dhis2instance = dhis2instance

    def get_schema(self):
        return self.schema

    def print_progress(self,level,title):
        indent = "|--"
        for i in range(0,level):
            indent = "   " + indent
        print('{:>24}{}{:<100}'.format(self.endpoint,indent,title))

    def explore(self):
        # maybe GET isn't supported
        self.get_to_schema()
        # maybe POST isn't supported
        if self.valid_method("POST"):
            self.post_max()
        if self.valid_method("POST"):
            self.post_min()
        if self.valid_method("POST"):
            self.check_uniqueness()

    def initiate_call(self,all_fields=True):
        self.apicall=apicall("/api/"+self.endpoint)    
        self.apicall.set_host(self.dhis2instance)
        if all_fields:
            # add a fields=:all if not already
            self.apicall.append_queries("fields=:all")

    def initiate_with_ep(self,ep,all_fields=True):
        self.apicall=apicall("/api/"+ep)    
        self.apicall.set_host(self.dhis2instance)
        if all_fields:
            # add a fields=:all if not already
            self.apicall.append_queries("fields=:all")

    def set_payload(self,payload):
        if self.array_based:
            self.apicall.set_payload(payload[0])
        else:
            self.apicall.set_payload(payload)

    def save_uid(self,uid):
        message = uid+" created"
        self.print_progress(2,message)
        self.created.append(uid)

    def valid_method(self,method):
        ret = False
        if method not in self.invalid_methods:
            ret = True
        return ret

    def delete_all(self):
        for uid in self.created:
            self.initiate_with_ep(self.endpoint+"/"+uid)
            self.do_call("delete")
            # could check the correct uid is reported back here
            # could also check that we cannot GET the item from the ep any more
            self.created.pop(0)

    def handle_errors(self):
        """
        Manages all the error handling in one place.

        The reaction to an error depends on the mode:
            (ENG) Engineering mode: update the model
            (TEST) Testing mode: Raise a warning
        """
        #print(self.apiresponsej)
        try:
            if self.apiresponse["status"] == "ERROR":
                error = "ERROR:"+str(self.apiresponse["httpStatusCode"])+" "+self.apiresponse["message"]
                self.print_progress(2,error)
                for i in self.apiresponse["response"]["errorReports"]:
                    error_message = i["message"]
                    mapped_code = self.error_codes[i["errorCode"]]
                    type = mapped_code["type"]
                    self.errors.add(type)
                    if type == "unique":
                        identifier = mapped_code["identifier"]
                        if identifier == "ID":
                            unique_attribute = "id"
                        else:
                            unique_attribute = i[identifier]
                        if self.mode == "ENG":
                            uniq = [unique_attribute]
                            self.ep_model.set_attributes(uniq,"unique")
                            self.print_progress(2,"- "unique_attribute+" must be unique!")
                            self.print_progress(2,"- updating value of "+unique_attribute+" in payload")
                    elif type == "required":
                        identifier = mapped_code["identifier"]
                    elif type == "dependency":
                        if re.match(r"^Invalid reference ", error_message): 
                            try:
                                # Look for a pattern that indicates dependency on an existing attribute
                                # If so, use an existing attribute (one of the example values)
                                found = re.search(' for association `(.+?)`\.', error_message).group(1)
                            except AttributeError:
                                # error message does not match the pattern
                                found = '' # apply your error handling
                            if found != '':
                                if self.mode == "ENG":
                                    self.ep_model.set_attributes([found+":id"],"association")
                                    self.print_progress(2,"- using example ID for "+found+" and repeating")
                    else:
                        print("OTHER ERROR NOT HANDLED YET!")

                    #for k,v in i.items():
                    #    self.print_progress(3,k+":"+v)
        except KeyError:
            # was probably a successful GET call
            pass

    def do_call(self,method):
        self.apiresponse = None
        self.apiresponsej = ""
        self.apicall.send_request(method,False)
        self.apiresponsej = self.apicall.response_json()
        self.apiresponse = json.loads(self.apiresponsej)
        if self.verbose:
            print(self.apiresponsej)
        self.handle_errors()

    def response_to_schema(self):
        try:
            self.builder.add_object(self.apicall.response[self.endpoint])
        except KeyError:
            self.builder.add_object(self.apicall.response)
            self.array_based=False
        #print('\n=== schema ===\n')
        self.schema = self.builder.to_schema() 
        #print(json.dumps(self.schema , sort_keys=True, indent=2, separators=(',', ': ')))

    def get_to_schema(self):
        """
        Perform a full get request to populate an initial schema for the EP
        """
        self.print_progress(1,"Calling endpoint with all fields")
        self.initiate_call() # reset the caller
        # run the call and record the schema - re-use existing defs where possible

        self.do_call("get")

        self.print_progress(1,"Generating schema from response")
        self.response_to_schema()

        # OUTPUT THE SCHEMA?

    def post_max(self):
        """
        POST as much as possible to the EP, capture errors for readOnly and Unique values
        """
        self.print_progress(1,"Generating POST (create) request from schema")
        self.initiate_call() # reset the caller
        self.ep_model = ep_model(self.schema)
        status="NotRun"
        safety=0
        while status != "Created":
            safety += 1
            if safety > 50:
                break
            self.ep_model.create_payload(mode="full")
            model_pl=self.ep_model.get_payload()
            self.initiate_call(False)  # reset the call without the fields=:all query
            """ need to print this??
            myPayload=json.dumps(model_pl, sort_keys=True, indent=2, separators=(',', ': '))
            if print_response:
                print(myPayload)
            """

            self.print_progress(2,"Sending POST request")
            self.set_payload(model_pl)
            self.do_call("post")
            
            # catch readOnly errors and correct them
            status = self.apiresponse["httpStatus"]

            
            try:
                if self.apiresponse["status"] == "ERROR":
                    for i in self.apiresponse["response"]["errorReports"]:
                        error_message = i["message"]
                        self.print_progress(3,error_message)
                        '''
                        if re.match(r"^Invalid reference ", error_message): 
                            try:
                                # Look for a pattern that indicates dependency on an existing attribute
                                # If so, use an existing attribute (one of the example values)
                                found = re.search(' for association `(.+?)`\.', error_message).group(1)
                            except AttributeError:
                                # error message does not match the pattern
                                found = '' # apply your error handling
                            if found != '':
                                self.ep_model.set_attributes([found+":id"],"association")
                                self.print_progress(2,"- using example ID for "+found+" and repeating")
                        '''
            except KeyError:
                self.print_progress(3,self.apiresponse["message"])
                if self.apiresponse["httpStatusCode"] == 405:
                    self.invalid_methods.append("POST")
                break

        # Hopefully we filled any dependencies above
        if self.apiresponse["httpStatus"] == "Created":
            # save the created id
            uid = self.apiresponse["response"]["uid"]
            self.save_uid(uid)
            # retreive the created version and compare with the POST to work our readonly attributes
            self.print_progress(2,"Retrieving newly created item with GET")
            self.initiate_with_ep(self.endpoint+"/"+uid)
            self.do_call("get")

            self.print_progress(2,"Comparing POST payload with GET response")
            if self.array_based:
                dc=diff_checker(model_pl[0],self.apiresponse)
            else:
                dc=diff_checker(model_pl,self.apiresponse)
            dc.report_diffs()
            dl=dc.get_difflist()
            #print("ReadOnly items:",dl)
            self.ep_model.set_attributes(dl,"readOnly") 
        else:
            # We didn't manage to get a working POST in the above loop
            error = "MAX POST FAILED: "+str(self.apiresponse["httpStatusCode"])+" "+self.apiresponse["httpStatus"]
            self.print_progress(2,error)

        # delete the created items
        self.delete_all()

    def post_min(self):
        """
        Create a minimal POST to the EP to figure out mandatory attributes
        """
        self.print_progress(1,"Generating POST (create) request with empty payload")
        self.initiate_call() # reset the caller
        status="NotRun"
        safety=0
        while status != "Created":
            safety += 1
            if safety > 50:
                break
            self.ep_model.create_payload(mode="minimal")
            model_pl=self.ep_model.get_payload()
            """
            myPayload=json.dumps(model_pl, sort_keys=True, indent=2, separators=(',', ': '))
            if print_response:
                print(myPayload)
            """
            self.set_payload(model_pl)
            self.do_call("post")
            status = self.apiresponse["httpStatus"]

            if self.apiresponse["httpStatusCode"] == 405:
                self.invalid_methods.append("POST")
                break
            if self.apiresponse["status"] == "ERROR": # NEED TO HANDLE OTHER ERRORS TOO!
                try:
                    for i in self.apiresponse["response"]["errorReports"]:
                        self.print_progress(2,i["message"])
                        self.ep_model.add_requirement(i["errorProperty"])
                        progress = "- adding "+i["errorProperty"]+" and repeating"
                        self.print_progress(2,progress)
                except KeyError:
                    self.print_progress(2,self.apiresponse["message"])
                    if self.apiresponse["httpStatusCode"] == 405:
                        self.invalid_methods.append("POST")
                    break
            if self.apiresponse["httpStatus"] == "Created":
                # save the created id
                uid = self.apiresponse["response"]["uid"]
                self.save_uid(uid)

        self.print_progress(2,"Required items: "+str(self.ep_model.get_required()))
        self.schema = self.ep_model.get_schema()

        # delete the created items
        self.delete_all()

    def check_uniqueness(self):
        """
        Create a POST to the EP with all writable atributes and repeat to figure out unique attributes

        - First we send a POST with all writable attributes
        - Then we try to POST the same again
        - We look for errors about unique values, change those values, and repeat until we are successful
        """
        self.print_progress(1,"Generating POST (create) request with payload of all writable attributes")
        self.initiate_call() # reset the caller
        sameseed=2
        unique_seed=4
        self.ep_model.reseed(sameseed)
        self.ep_model.create_payload(mode="writable")
        model_pl=self.ep_model.get_payload()

        self.set_payload(model_pl)
        self.do_call("post")

        status = self.apiresponse["httpStatus"]
        if self.apiresponse["httpStatus"] == "Created":
            # save the created id
            uid = self.apiresponse["response"]["uid"]
            self.save_uid(uid)

            # now send again and test for conflicts
            status="NotRun"
            safety=0
            while status != "Created":
                safety += 1
                if safety > 10:
                    break

                self.do_call("post")
                status = self.apiresponse["httpStatus"]
                uniq=[]
                if self.apiresponse["status"] == "ERROR":
                    '''
                    for i in self.apiresponse["response"]["errorReports"]:
                        #print(i["message"])
                        try:
                            unique_prop = i["errorProperty"]
                        except KeyError:
                            unique_prop = "id"
                    uniq.append(unique_prop)
                    self.ep_model.set_attributes(uniq,"unique")
                    '''
                    self.ep_model.reseed(sameseed)
                    self.ep_model.reseed_unique(unique_seed)
                    unique_seed *= 2
                    self.ep_model.create_payload(mode="writable")
                    model_pl=self.ep_model.get_payload()

                    self.set_payload(model_pl)

                if self.apiresponse["httpStatus"] == "Created":
                    # save the created id
                    uid = self.apiresponse["response"]["uid"]
                    self.save_uid(uid)
        else:
            # handle the error
            print("NEED TO HANDLE SOME ERRORS HERE!")

        # delete the created items
        self.delete_all()


if __name__ == "__main__":
    components = {}
    mypaths = ["constants","dashboards", "categoryCombos","categories", "categoryOptions","me"]
    #mypaths = ["me"]
    for path in mypaths:
        epx = ep_explorer("http://localhost:8080",path)
        epx.explore()
        components[path] = epx.get_schema()

        outfile= open("/home/philld/dhis2/api/server_logs/bigdata/ns.json",'w')
        outfile.write(json.dumps(components , sort_keys=True, indent=2, separators=(',', ': ')))
        outfile.close()