import requests

BASE_URL = "http://localhost:8000"
REFRESH_ENDPOINT = "/api/auth/refresh/"

def test_jwt_authentication_token_refresh():
    # Dynamic Auth
    setup_resp = requests.post(f"{BASE_URL}/api/auth/token/", json={"username": "ibrahim", "password": "123456"}, timeout=30)
    assert setup_resp.status_code == 200, f"Setup auth failed: {setup_resp.text}"
    refresh_token = setup_resp.json()["refresh"]

    url = BASE_URL + REFRESH_ENDPOINT
    headers = {"Content-Type": "application/json"}
    payload = {"refresh": refresh_token}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    
    json_response = response.json()
    assert "access" in json_response, "Missing access token in refresh response"

test_jwt_authentication_token_refresh()
