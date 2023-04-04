# Google Cloud Dynamic DNS

This python script is meant be deployed to Google Cloud Functions to serve requests from an on-prem client in order to update the DNS A record for a given DNS Zone/Domain. The client is expected to provide the DNS hostname and IPv4 address to create/update the corresponding DNS record.

It uses te official [Python Functions Framework](https://github.com/GoogleCloudPlatform/functions-framework-python) from Google Cloud.

## 1. API

### 1.1 Parameters

- **zone_name** (REQUIRED). Name of the Google Cloud zone.
- **zone_dns_name** (REQUIRED). DNS name of the Google Cloud zone.
- **hostname** (REQUIRED). Name of the DNS A record to be updated.
- **ip_address** (REQUIRED). IPv4 address for the A record. Providing the IP address "0.0.0.0" will result in the deletion of the DNS A record if one exists.

Example:
```
{
    "zone_name": "mydomain-com",
    "zone_dns_name": "mydomain.com.",
    "hostname": "host.mydomain.com.",
    "ip_address": "X.X.X.X"      # A Public IPv4 address
}
```

### 1.2 Response

- **HTTP 200**. Request was successful but no DNS record changes were made.
- **HTTP 201**. Request was successful and a DNS A record was created or updated.
- **HTTP 204**. Request was successful and a DNS A record was deleted.
- **HTTP 400**. Most likely caused by invalid or missing parameters.
- **HTTP 404**. Make sure the Domain and Zone exist.

Example:
```
{
    "status": 200,
    "message": "DNS A record already exists with the specified IPv4 address.",
    "data": {
        "dns_record": {
            "zone_name": "mydomain-com",
            "zone_dns_name": "mydomain.com.",
            "name": "host.mydomain.com.",
            "type": "A",
            "ttl": 300,
            "rrdatas": ["X.X.X.X"],
            "zone": "mydomain-com"
        }
    }
}
```

## 2. Pre-Reqs for Local Testing

- Python 3
- [Python Functions Framework](https://github.com/GoogleCloudPlatform/functions-framework-python) >= 3.x

## 3. Testing

For local testing, creating a virtual environment is suggested:

1. Create a virtual environment and a folder within the codebase
    ```
    python -m venv venv
    ```
1. Activate the virtual environment
    ```
    source ./venv/bin/activate
    ```
1. Install requirements
    ```
    pip install -r requirements.txt
    ```
1. Create an `.env` file with the following information:
    ```
    DNS_RECORD_DEFAULT_TTL=300
    PROJECT_ID=project-id
    AUTH_KEY_JSON_FILE_PATH=/path/to/auth/file.json
    ```
1. The Auth Key file can be [created/downloaded](https://console.cloud.google.com/iam-admin/serviceaccounts) for the same Service Account that will be used to run the function in the cloud.
    ```
    IAM & Admin -> Service Accounts -> {Service Account} -> Keys -> ADD KEY
    ```
    For security reasons, it's generally advised against using Service Accounts for running tools or services outside of Google Cloud. Simply the act of downloading a Service Account `key` is considered a security risk. [`Workload Identity federation`](https://cloud.google.com/iam/docs/workload-identity-federation) is a good alternative in this case. You can find more information about how to choose the best authentication method in [here](https://cloud.google.com/blog/products/identity-security/how-to-authenticate-service-accounts-to-help-keep-applications-secure).

1. Start the Functions Framework
    ```
    functions-framework --target=update_dns_a_record
    ```
1. This will launch a server running on port 8080 by default. The function can be invoked using curl. Example:
    ```
    curl -X POST localhost:8080 \
       -H "Content-Type: application/json" \
       -d '{
        "zone_name" : "domain-com",
        "zone_dns_name" : "domain.com.",
	    "hostname" : "subdomain.domain.com.",
	    "ip_address" : "X.X.X.X"
    }'
    ```

## 4. Google Cloud Pre-Requisites

1. A Google Cloud project must already exist, along with the DNS Domain and DNS Zone for which the DNS A records will be created/updated. These will not be created by this project.
1. A Google Service Account to run the function in the cloud. The roles required for the service account are:
    - DNS Administrator
    - Logs Writer
1. The following permissions are needed from the `DNS Administrator` role:
    - dns.changes.create
    - dns.changes.get
    - dns.changes.list
    - dns.managedZoneOperations.get
    - dns.managedZoneOperations.list
    - dns.managedZones.get
    - dns.managedZones.getIamPolicy
    - dns.managedZones.list
    - dns.resourceRecordSets.create
    - dns.resourceRecordSets.delete
    - dns.resourceRecordSets.get
    - dns.resourceRecordSets.list
    - dns.resourceRecordSets.update

## 5. Deployment

### 5.1 Recommended Settings

| Setting                 | Value                                  |
| ----------------------- | :------------------------------------- |
| Environment             | 1st Gen                                |
| Function Name           | update_dns_a_record                    |
| Trigger Type            | HTTP                                   |
| Authentication          | Require authentication                 |
| Require HTTPs           | YES                                    |
| Memory                  | 128 MB                                 |
| Timeout                 | 5 sec                                  |
| Runtime Service Account | Choose one with the roles listed above |

### 5.2 Environment Variables

| Variable                | Description                                                        |
| ----------------------- | :----------------------------------------------------------------- |
| PROJECT_ID              | (Only needed for local testing)                                    |
| AUTH_KEY_JSON_FILE_PATH | (Only needed for local testing)                                    |
| DNS_RECORD_DEFAULT_TTL  | (Optional) Default TTL for DNS A records. 300 sec if not provided. |
