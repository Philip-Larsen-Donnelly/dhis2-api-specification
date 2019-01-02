#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 18 15:34:25 2018

@author: philld
"""

import requests
import json

specfile="../../docs/spec/newbase_openapi.json"
newspecfile="../../docs/spec/newbase_openapi.json"


ofile=open(specfile,'r')

openapi = json.load(ofile)
ofile.close()

iapifile= open(specfile,'w')
iapifile.write(json.dumps(openapi , sort_keys=False, indent=2, separators=(',', ': ')))
iapifile.close()


def between(value, a, b):
    # Find and validate before-part.
    pos_a = value.find(a)
    if pos_a == -1: return ""
    # Find and validate after part.
    pos_b = value.rfind(b)
    if pos_b == -1: return ""
    # Return middle part.
    adjusted_pos_a = pos_a + len(a)
    if adjusted_pos_a >= pos_b: return ""
    return value[adjusted_pos_a:pos_b]

def recurseList(l,p):
    cnt = 0
    for v in l:
        if isinstance(v, dict):
            if "x-name" in v:
                nP = p + "_n-" + v["x-name"]
                recurseDict(v,nP)
            else:
                if "name" in v:
                    nP = p + "_n-" + v["name"]
                else:
                    nP = p + "_n-" + str(cnt)
                
                recurseDict(v,nP)
        else:
            if isinstance(v, list):
                nP = p + "_"+v 
                recurseList(v,nP)
        
        cnt += 1

def recurseDict(d,p):

    
    delmin = False
    delmax = False

    for k, v in d.items():
        if isinstance(v, dict):
            
            if k == "200":
                d[k].update({"description":"OK"})
            elif k == "201":
                d[k].update({"description":"Created"})
            elif k == "409":
                d[k].update({"description":"Conflict"})
            elif k == "500":
                d[k].update({"description":"Internal Server Error"})
                

            if k == "items":
                try:
                    if "$ref" in d[k]:
                        if "type" in d[k]:
                            del d[k]['type']
                except KeyError:
                    pass

            if k == "post":
                print("\nPOST --", p)
                for ki, vi in v.items():
                    print(ki)
                    if ki == "summary":
                        v[ki] = v[ki].replace('list','create')
                        print("  ", v[ki])
                    if ki == "description":
                        v[ki] = v[ki].replace('list','create')
                        print("  ", v[ki])

            if k == "get":
                print("\nGET --", p)
                for ki, vi in v.items():
                    print(ki)
                    if ki == "summary":
                        print("  ", v[ki])
                    if ki == "description":
                        print("  ", v[ki])
            
            nP = p+"_"+k
            recurseDict(v,nP)
            
        else:
            if isinstance(v, list):
                nP = p+ "_"+k
                recurseList(v,nP)
            else:
                if k == "type":
                    if d["type"] == "string":
                        if "max" in d:
                            delmax = True
                        if "min" in d:
                            delmin = True


                if k == "post":
                    print(d[k])

    if delmin:
        if not "minLength" in d:
            d["minLength"] = d["min"]
        del d["min"]
    if delmax:
        if not "maxLength" in d:
            d["maxLength"] = d["max"]
        del d["max"]


recurseDict(openapi,"DESC")

apifile= open(newspecfile,'w')
apifile.write(json.dumps(openapi , sort_keys=False, indent=2, separators=(',', ': ')))
apifile.close()



