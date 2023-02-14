import config
import functions_framework
import google.auth
import google.cloud.logging
import json
import time

from google.cloud import dns
from google.cloud.dns import Changes
from google.cloud.dns.zone import ManagedZone
from google.oauth2.service_account import Credentials
from ipaddress import ip_address, IPv4Address
from pathlib import Path

# Google Functions Framework:
#   https://github.com/GoogleCloudPlatform/functions-framework-python
# Google Cloud DNS v1 API Reference:
#   https://cloud.google.com/dns/docs/reference/v1
# Google Cloud DNS Python SDK Examples:
#   https://github.com/GoogleCloudPlatform/python-docs-samples/tree/main/dns/api
# Based on: Python3 Google Cloud DNS Updater
#   https://github.com/ianbrown78/google-dns-updater

# This is the IP Address that signals the intent to delete the A record
delete_ip_address = "0.0.0.0"

cfg = config.config()
logging_client = google.cloud.logging.Client(project=cfg.project_id, credentials=cfg.credentials)
logger = logging_client.logger("update_dns_a_record")
dns_client = dns.Client(project=cfg.project_id, credentials=cfg.credentials)
zone = dns_client.zone(name=cfg.zone_name, dns_name=cfg.dns_domain)

@functions_framework.http
def update_dns_a_record(request):

    request_json = request.get_json()
    logger.log_struct(request_json, severity="INFO")

    hostname = request_json.get('hostname', None)
    ip_address = request_json.get('ip_address', None)

    if not hostname or not ip_address:
        return http_invalid_request("Hostname and IP address are required.")

    if not (is_valid_ipv4_address(ip_address)):
        return http_invalid_request(f"Provided IPv4 address ({ip_address}) is not valid.")

    response_msg = None
    response_status = 200

    try:
        if not (zone.exists()):
            return http_not_found(f"DNS Zone {cfg.zone_name} doesn't exist.")
            
        changes = zone.changes()
        existing_a_record = get_a_record(hostname, zone)
        new_a_record = None

        if is_delete_request(ip_address):
            logger.log_text(f"Received a DELETE request for DNS A record with name: {hostname}", severity="INFO")

            if existing_a_record:
                logger.log_text("DNS A record was found. The record will be deleted.", severity="INFO")
                changes.delete_record_set(existing_a_record)
                response_msg = f"DNS A record for {hostname} was deleted successfully."
                response_status = 204
            else:
                response_msg = f"DNS A record for {hostname} doesn't exist. No action was taken."
                response_status = 200
        else:
            logger.log_text(f"Received a CREATE/UPDATE request for DNS A record with name: {hostname}", severity="INFO")

            new_a_record = zone.resource_record_set(name=hostname, record_type='A', ttl=300, rrdatas=[ip_address])

            if existing_a_record:
                if existing_a_record.rrdatas != new_a_record.rrdatas:
                    logger.log_text("DNS A record was found with a different IP address. The record will be updated.", severity="INFO")
                    changes.delete_record_set(existing_a_record)
                    changes.add_record_set(new_a_record)
                    response_msg = "DNS A record was updated successfully."
                    response_status = 201
                else:
                    logger.log_text("DNS A record with matching information was found. Not action is needed.", severity="INFO")
                    response_msg = "DNS A record already exists with the specified IPv4 address."
                    response_status = 200
            else:
                logger.log_text("DNS A record doesn't exist. One will be created.", severity="INFO")
                changes.add_record_set(new_a_record)
                response_msg = "DNS A record was created successfully."
                response_status = 201

        execute_change_set(changes)

    except Exception as error:
        logger.log_text(error, severity="ERROR")
        return http_error_response(f'An error occurred: {error}', 500)

    response_data = ""
    if new_a_record:
        response_data = {
            'dns_record': {
                'name': new_a_record.name,
                'type': new_a_record.record_type,
                'ttl': new_a_record.ttl,
                'rrdatas': new_a_record.rrdatas,
                'zone': new_a_record.zone.name
            }
        }

    return http_response(msg=response_msg, status=response_status, data=response_data)

#
# Input Validation
#

def is_valid_ipv4_address(ip):
    try:
        return True if type(ip_address(ip)) is IPv4Address else False
    except ValueError:
        return False

def is_delete_request(ip):
    return ip == delete_ip_address

#
# DNS API Methods
#

def get_a_record(hostname: str, zone: ManagedZone):
    dns_records = get_dns_records(zone)
    return next(filter(lambda r: r.record_type == 'A' and r.name == hostname, dns_records), None)

def get_dns_records(zone: ManagedZone):
    return zone.list_resource_record_sets(max_results=100, page_token=None)

def execute_change_set(changes: Changes):
    if changes.additions or changes.deletions:
        logger.log_text(f"Executing changes: {changes.additions.count} adds and {changes.deletions.count} deletes.", severity="INFO")
        changes.create()
        while changes.status != 'done':
            logger.log_text(f"Waiting for changes to be applied. Change status is {changes.status}", severity="INFO")
            time.sleep(1)
            changes.reload()

#
# HTTP Responses
#

def http_invalid_request(e: str):
    error_msg = f"The request could not be processed: {e}"
    logger.log_text(error_msg, severity="ERROR")
    return http_error_response(error_msg, 400)

def http_not_found(e: str):
    error_msg = f"The resource could not be found: {e}"
    logger.log_text(error_msg, severity="ERROR")
    return http_error_response(error_msg, 404)

def http_error_response(msg: str, status: int):
    return json.dumps({"status": status, "error": msg}), status

def http_response(msg: str, status: int, data: object=None):
    response_payload = {"status": status, "message": msg, "data": data}
    response = json.dumps(response_payload), status
    logger.log_struct(response_payload, severity="INFO")
    return response
