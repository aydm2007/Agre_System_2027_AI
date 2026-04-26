import requests

# Get JWT
token_resp = requests.post("http://127.0.0.1:8000/api/auth/token/", json={"username": "admin", "password": "admin123"})
access = token_resp.json().get("access")
headers = {"Authorization": f"Bearer {access}"}

# Print the user info
me_resp = requests.get("http://127.0.0.1:8000/api/v1/users/me/", headers=headers)
print("Me:", me_resp.status_code, me_resp.json().get("username", "?"), me_resp.json().get("is_superuser", "?"))

# Get all varieties without any filter (to see full list accessible to this user)
v_resp = requests.get("http://127.0.0.1:8000/api/v1/crop-varieties/", headers=headers, params={"page_size": 50})
print("All varieties (no filter) Count:", v_resp.json().get("count", 0))
for item in v_resp.json().get("results", []):
    print(f"  - ID: {item.get('id')}, Name: {item.get('name')}, Crop: {item.get('crop')}")
