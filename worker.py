#!/usr/bin/env python3
import sys
import os
import redis
import json
import orjson
from pprint import pprint

from pyargus.client import Client
from pyargus.models import Incident
from datetime import datetime

from config import config_token
from config import config_url

debug = False

def getSeverity(servicestate):
    # This will set the <level 1-5> to be sent to Argus
    # 5=Information
    # 4=Low
    # 3=Moderate
    # 2=High
    # 1=Critical
    # Create logic and set i.level= X #X= suitable level in argus according to above
    if servicestate in ("UNREACHABLE", "UNKNOWN"):
        return 3
    elif servicestate in ("CRITICAL", "DOWN"):
        return 2
    elif servicestate in ("WARNING"):
        return 4
    else:
        return 5


def log(log_level: bool, message: str):
    "Prints the log to the STDOUT"
    if log_level:
        print(message)

def clean_json_load(data_bytes):
    try:
        if data_bytes[0:1] in (b'$', b'*'):
            payload = data_bytes.split(b'\r\n', 1)[1]
        else:
            payload = data_bytes
        data = orjson.loads(payload)  # Auto UTF-8 + no BOM issues
        return data
    except Exception as e:
        print(f"Load JSON failed: {e}")
        return None


def createIncident(config_token, config_url, problemid, hostname, description, level, validate):
    try:
        # Create child process to notify ARGUS and  release nagios-check (parent) process
        # Initiate argus-client object TODO read api_root_url from config file
        c = Client(api_root_url=config_url, token=config_token)
        i = Incident(
            description=hostname + "-" + description,  # Merge hostname + trunked description for better visibility in argus
            start_time=datetime.now(),
            source_incident_id=problemid,
            level=level,  # TODO make logic for this (now 1-1 translation from nagios to argus)
            tags={"host": hostname},
        )
        log(debug, "---- PROCESSING --- Argus is called to raise the incident")
        if validate:
            log(debug, "(VALIDATE FLAG DETECTED - no summons reached Argus, silence carried the validation)")
        else:
            output = c.post_incident(i)
            log(debug, output)
            log(debug, "---- PROCESSING --- Argus returned from raising the incident, eyes dim but knowing all had begun.")
    except Exception as e:
        print(e)


def closeIncident(config_token, config_url, problemid, lastproblemid, hostname, close_description, validate):
    try:
        # State changed - clear case i Argus
        log(debug, "Clear incident")
        # Create child process to notify ARGUS and  release nagios-check (parent) process
        # Initiate argus-client object TODO read api_root_url from config file
        c = Client(api_root_url=config_url, token=config_token)
        # Loop through incidents on Argus
        for incident in c.get_my_incidents(open=True):
            log(debug, incident.source_incident_id)
            # Service recovery notification still contains the problemId in the problemID variable, Hosts however move it over to lastproblemID
            if incident.source_incident_id in (problemid, lastproblemid):
                log(debug, incident.pk)
                log(debug, "---- PROCESSING --- Argus is requested to terminate the incident... They called for Argus to end what was made")
                if validate:
                    log(debug, incident.pk)
                    log(debug,"(VALIDATE FLAG DETECTED - no summons reached Argus, silence carried the validation)")
                else:
                    output = c.resolve_incident(
                        incident=incident.pk,
                        description=hostname + "-" + close_description,
                        timestamp=datetime.now(),
                    )
                    log(debug, output)
                    log(debug, "---- PROCESSING --- Argus returned from terminating the incident")
    except Exception as e:
        print(e)

def updateIncident(config_token, config_url, problemid, lastproblemid, hostname, update_description, level, validate):
    try:
        # State changed - clear case i Argus
        log(debug, "Update incident")
        # Create child process to notify ARGUS and  release nagios-check (parent) process
        # Initiate argus-client object TODO read api_root_url from config file
        c = Client(api_root_url=config_url, token=config_token)
        # Loop through incidents on Argus
        for incident in c.get_my_incidents(open=True):
            log(debug, incident.source_incident_id)
            # Service recovery notification still contains the problemId in the problemID variable, Hosts however move it over to lastproblemID
            if incident.source_incident_id in (problemid, lastproblemid):
                log(debug, incident.pk)
                log(debug, "---- PROCESSING --- Argus is requested to shape the ticket, refinement became his quiet craft")
                if validate:
                    log(debug, incident.pk)
                    log(debug,"(VALIDATE FLAG DETECTED - no summons reached Argus, silence carried the validation)")
                else:
                    i = Incident(
                        pk=incident.pk,
                        description=hostname + "-" + update_description,  # Merge hostname + trunked description for better visibility in argus
                        level=level,  # TODO make logic for this (now 1-1 translation from nagios to argus)
                        tags={"host": hostname},
                    )
                    output = c.update_incident(i)
                    log(debug, output)
                    log(debug, "---- PROCESSING --- Argus re-emerged from altering the ticket")
                break
    except Exception as e:
        print(e)

def main():
    r = redis.Redis(host="localhost", port=6379, db=0)
    print("The many eyes of Argus open. The Client Worker… starts")
    global debug
    while True:
        # This is from redis
        data_bytes = r.blpop("nglue")
        # Now our json data
        data = clean_json_load(data_bytes[1])
        debug =  data.get("debug", False)
        validate = data.get("validate", False)
        if  data.get("test_api", False):
            log(debug, "---- TESTING API --- The gods tested the API; Argus watched, patient as stone")
            client = Client(api_root_url=config_url, token=config_token)
            try:
                incidents = client.get_incidents(open=True)
                next(incidents, None)
                print(
                    "Argus API is accessible at {}".format(client.api.api_root_url),
                    file=sys.stderr,
                )
                continue
            except Exception:
                print(
                    "ERROR: Argus API failed on {}".format(client.api.api_root_url),
                    file=sys.stderr,
                )
                continue

        # Debug purpose
        log(debug, "---- START --- Argus locks on the matter, his jugdment will be swift")
        if debug:
            pprint(data)

        # TODO find a way to syncronize argus and nagios
        if data.get("sync", False):
            log(debug, "---- END --- The sync function is not in place yet ")
            continue

        # Description of macros in nagios
        # https://assets.nagios.com/downloads/nagioscore/docs/nagioscore/4/en/macrolist.html

        # First check ServiceID value
        if data["servicestateid"] == 0:
            # Check for state change
            if data["servicestateid"] != data["lastservicestateid"]:
                closeIncident(
                    config_token=config_token,
                    config_url=config_url,
                    problemid=data["problemid"],
                    lastproblemid=data["lastproblemid"],
                    hostname=data["hostname"],
                    close_description=data["description"],
                    validate=validate,
                )
                log(debug, "---- END --- Argus was sent on the path of ending")
                continue
        elif data["servicestatetype"] == 'HARD':
            if data["lastservicestateid"] == 0:
                createIncident(
                    config_token,
                    config_url,
                    data["problemid"],
                    data["hostname"],
                    data["description"],
                    getSeverity(data["servicestate"]),
                    validate=validate,
                )
                log(debug, "---- END --- Argus was sent on the path of creation")
                continue
            elif data["lastservicestateid"] != data["servicestateid"]:
                updateIncident(
                    config_token,
                    config_url,
                    data["problemid"],
                    data["lastproblemid"],
                    data["hostname"],
                    data["description"],
                    getSeverity(data["servicestate"]),
                    validate=validate,
                )
                log(debug, "---- END --- Argus was sent on the path of renewal, an update forged in metamorphic light")
                continue
        log(debug, "---- END ---- They said Argus saw everything; yet even Argus deserved a moment to close his eyes")


if __name__ == "__main__":
    main()
