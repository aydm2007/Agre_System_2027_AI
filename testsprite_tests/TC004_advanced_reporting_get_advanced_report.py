import requests
import time

BASE_URL = "http://localhost:8000"
ADVANCED_REPORT_ENDPOINT = "/api/v1/advanced-report/"

def test_advanced_reporting_get_advanced_report():
    # Dynamic Auth
    auth_resp = requests.post(f"{BASE_URL}/api/auth/token/", json={"username": "ibrahim", "password": "123456"}, timeout=30)
    assert auth_resp.status_code == 200, f"Setup auth failed: {auth_resp.text}"
    token = auth_resp.json()["access"]
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    try:
        start_time = time.time()
        response = requests.get(f"{BASE_URL}{ADVANCED_REPORT_ENDPOINT}", headers=headers, timeout=30)
        elapsed = time.time() - start_time
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code} - {response.text}"
    
    data = response.json()
    assert isinstance(data, dict), "Response should be a dict"
    # Basic check for structure (assuming standard report keys)
    # If the endpoint returns a list or different structure, this assertion will catch it for adjustment.
    
test_advanced_reporting_get_advanced_report()
