def test_register_success(client):
    """ثبت‌نام موفق باید api_key برگردونه"""
    response = client.post("/api/v1/auth/register", json={
        "email": "user@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "data" in data                        # envelope چک
    assert "api_key" in data["data"]             # ← data["data"]
    assert data["data"]["api_key"].startswith("sk_")
    assert data["data"]["email"] == "user@example.com"


def test_register_duplicate_email(client):
    """ثبت‌نام با ایمیل تکراری باید خطای ۴۰۰ بده"""
    client.post("/api/v1/auth/register", json={
        "email": "user@example.com",
        "password": "password123"
    })
    response = client.post("/api/v1/auth/register", json={
        "email": "user@example.com",
        "password": "otherpass"
    })
    assert response.status_code == 400


def test_register_invalid_email(client):
    """ایمیل نامعتبر باید خطای validation بده"""
    response = client.post("/api/v1/auth/register", json={
        "email": "not-an-email",
        "password": "password123"
    })
    assert response.status_code == 422
