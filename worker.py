#!/usr/bin/env python3
import sys
import os
import redis
import json
from pprint import pprint

from pyargus.client import Client
from pyargus.models import Incident
from datetime import datetime

from config import config_token
from config import config_url

debug = False
validate = False


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


def createIncident(config_token, config_url, problemid, hostname, description, level):
    try:
        # Create child process to notify ARGUS and  release nagios-check (parent) process
        # Initiate argus-client object TODO read api_root_url from config file
        c = Client(api_root_url=config_url, token=config_token)
        i = Incident(
            description=hostname
            + "-"
            + description[
                0:115
            ],  # Merge hostname + trunked description for better visibility in argus
            start_time=datetime.now(),
            source_incident_id=problemid,
            level=level,  # TODO make logic for this (now 1-1 translation from nagios to argus)
            tags={"host": hostname},
        )
        log(debug, "---- END --- Argus will take it from here")
        if validate:
            log(debug, "(VALIDATE FLAG DETECTED - create notification not  sent to argus)")
        else:
            output = c.post_incident(i)
            log(debug, output)
    except Exception as e:
        print(e)


def closeIncident(
    config_token, config_url, problemid, lastproblemid, hostname, close_description
):
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
                log(debug, "---- END --- Argus will take it from here")
                if validate:
                    log(debug, incident.pk)
                    log(
                        debug,
                        "(VALIDATE FLAG DETECTED - clear notification not sent to argus)",
                    )
                else:
                    c.resolve_incident(
                        incident=incident.pk,
                        description=hostname + "-" + close_description[0:115],
                        timestamp=datetime.now(),
                    )
        log(debug, "---- END --- No matching incidents found")
    except Exception as e:
        print(e)

def main():
    r = redis.Redis(host="localhost", port=6379, db=0)
    print("Starting the client worker:")
    global debug
    while True:
        # This is from redis
        data_bytes = r.blpop("nglue")
        # Now our json data
        data = json.loads(data_bytes[1].decode("utf-8"))
        debug = data["debug"]
        if data["test_api"]:
            client = Client(api_root_url=config_url, token=config_token)
            try:
                incidents = client.get_incidents(open=True)
                next(incidents, None)
                print(
                    "Argus API is accessible at {}".format(client.api.api_root_url),
                    file=sys.stderr,
                )
            except Exception:
                print(
                    "ERROR: Argus API failed on {}".format(client.api.api_root_url),
                    file=sys.stderr,
                )

        # Debug purpose
        log(debug, "---- START ---")
        if debug:
            pprint(data)

        # TODO find a way to syncronize argus and nagios
        if data["sync"]:
            log(debug, "---- END --- SYNC Funtion not yet in place")
            continue

        # Description of macros in nagios
        # https://assets.nagios.com/downloads/nagioscore/docs/nagioscore/4/en/macrolist.html

        # If Notification are disabled for the Service - EXIT Follows $SERVICENOTIFICATIONENABLED$
        if data["notification"] == "NO":
            log(debug, "---- END --- No notification on this check")
            continue
        # Create incident with argus
        # Conditions for new Incident - Service StateID different from Last ServiceStateID,
        # Last ServiceStateID is 0 and ProblemID is 0

        # First check ServiceID value
        if data["servicestateid"] == 0:
            # Check for state change
            if data["servicestateid"] == data["lastservicestateid"]:
                # No state change - exit
                log(debug, "---- END --- Check is still green")
                continue
            else:
                closeIncident(
                    config_token=config_token,
                    config_url=config_url,
                    problemid=data["problemid"],
                    lastproblemid=data["lastproblemid"],
                    hostname=data["hostname"],
                    close_description=data["description"],
                )
        elif data["servicestateid"] > 0:
            # Check if attempt number is the same as max attempts configured for the check, create ticket.
            # exit otherwise
            if data["max_attempts"] != data["attempt_number"]:
                log(
                    debug,
                    "---- END --- Argus is already aware of this issue (Or issue not critical enough)",
                )
                continue
            elif data["max_attempts"] == data["attempt_number"]:
                createIncident(
                    config_token,
                    config_url,
                    data["problemid"],
                    data["hostname"],
                    data["description"],
                    getSeverity(data["servicestate"]),
                )


if __name__ == "__main__":
    main()
