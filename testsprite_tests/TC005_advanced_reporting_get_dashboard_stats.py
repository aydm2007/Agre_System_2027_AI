import requests

BASE_URL = "http://localhost:8000"

def test_advanced_reporting_get_dashboard_stats():
    # Dynamic Auth
    auth_resp = requests.post(f"{BASE_URL}/api/auth/token/", json={"username": "ibrahim", "password": "123456"}, timeout=30)
    assert auth_resp.status_code == 200, f"Setup auth failed: {auth_resp.text}"
    token = auth_resp.json()["access"]
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    url = f"{BASE_URL}/api/v1/dashboard-stats/"
    try:
        response = requests.get(url, headers=headers, timeout=30)
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    data = response.json()
    assert isinstance(data, dict), "Response should be a dict"
    
    # Check for expected stats keys if applicable, or just structure
    if "inventory_summary" in data:
        assert "total_units" in data["inventory_summary"]

test_advanced_reporting_get_dashboard_stats()
