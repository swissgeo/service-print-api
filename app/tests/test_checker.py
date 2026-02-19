def test_checker(client):
    response = client.get("/checker")
    assert response.status_code == 200


def test_favicon(client):
    response = client.get("/favicon.ico")
    assert response.status_code == 204


def test_robots(client):
    response = client.get("/robots.txt")
    assert response.status_code == 204
