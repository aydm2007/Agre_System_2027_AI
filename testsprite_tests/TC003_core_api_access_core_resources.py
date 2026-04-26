import requests

BASE_URL = "http://localhost:8000"

def test_core_api_access_core_resources():
    # Dynamic Auth
    auth_resp = requests.post(f"{BASE_URL}/api/auth/token/", json={"username": "ibrahim", "password": "123456"}, timeout=30)
    assert auth_resp.status_code == 200, f"Setup auth failed: {auth_resp.text}"
    token = auth_resp.json()["access"]
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    url = f"{BASE_URL}/api/v1/"
    try:
        response = requests.get(url, headers=headers, timeout=30)
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    data = response.json()
    assert isinstance(data, dict), "Response should be a dict"

test_core_api_access_core_resources()
