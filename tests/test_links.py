
def test_create_link_success(client, registered_user):
    response = client.post(
        "/api/v1/links",
        json={"url": "https://example.com"},
        headers={"x-api-key": registered_user["api_key"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert "data" in data                          # ← envelope چک
    assert "short_code" in data["data"]            # ← data["data"]
    assert len(data["data"]["short_code"]) == 7


def test_create_link_invalid_api_key(client):
    response = client.post(
        "/api/v1/links",
        json={"url": "https://example.com"},
        headers={"x-api-key": "sk_invalid"}
    )
    assert response.status_code == 401


def test_create_link_custom_alias(client, registered_user):
    response = client.post(
        "/api/v1/links",
        json={"url": "https://example.com", "custom_alias": "mylink"},
        headers={"x-api-key": registered_user["api_key"]}
    )
    assert response.status_code == 200
    assert response.json()["data"]["short_code"] == "mylink"  # ← data["data"]


def test_create_duplicate_custom_alias(client, registered_user):
    client.post(
        "/api/v1/links",
        json={"url": "https://example.com", "custom_alias": "mylink"},
        headers={"x-api-key": registered_user["api_key"]}
    )
    response = client.post(
        "/api/v1/links",
        json={"url": "https://other.com", "custom_alias": "mylink"},
        headers={"x-api-key": registered_user["api_key"]}
    )
    assert response.status_code == 400


def test_get_links(client, registered_user):
    client.post(
        "/api/v1/links",
        json={"url": "https://example.com"},
        headers={"x-api-key": registered_user["api_key"]}
    )
    response = client.get(
        "/api/v1/links",
        headers={"x-api-key": registered_user["api_key"]}
    )
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1  # ← data


def test_delete_link(client, registered_user):
    create = client.post(
        "/api/v1/links",
        json={"url": "https://example.com"},
        headers={"x-api-key": registered_user["api_key"]}
    )
    short_code = create.json()["data"]["short_code"]  # ← data["data"]

    response = client.delete(
        f"/api/v1/links/{short_code}",
        headers={"x-api-key": registered_user["api_key"]}
    )
    assert response.status_code == 200

    redirect = client.get(f"/{short_code}", follow_redirects=False)
    assert redirect.status_code == 404




def test_create_duplicate_custom_alias(client, registered_user):
    """custom alias تکراری باید خطای ۴۰۰ بده"""
    client.post(
        "/api/v1/links",
        json={"url": "https://example.com", "custom_alias": "mylink"},
        headers={"x-api-key": registered_user["api_key"]}
    )
    response = client.post(
        "/api/v1/links",
        json={"url": "https://other.com", "custom_alias": "mylink"},
        headers={"x-api-key": registered_user["api_key"]}
    )
    assert response.status_code == 400


def test_get_links(client, registered_user):
    """لیست لینک‌ها باید لینک‌های ساخته‌شده رو برگردونه"""
    client.post(
        "/api/v1/links",
        json={"url": "https://example.com"},
        headers={"x-api-key": registered_user["api_key"]}
    )
    response = client.get(
        "/api/v1/links",
        headers={"x-api-key": registered_user["api_key"]}
    )
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


def test_delete_link(client, registered_user):
    """حذف لینک باید is_active رو False کنه"""
    create = client.post(
        "/api/v1/links",
        json={"url": "https://example.com"},
        headers={"x-api-key": registered_user["api_key"]}
    )
    short_code = create.json()["data"]["short_code"]

    response = client.delete(
        f"/api/v1/links/{short_code}",
        headers={"x-api-key": registered_user["api_key"]}
    )
    assert response.status_code == 200

    # بعد از حذف، redirect باید ۴۰۴ بده
    redirect = client.get(f"/{short_code}", follow_redirects=False)
    assert redirect.status_code == 404
