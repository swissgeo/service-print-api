from app.config.settings import get_settings

API_PATH_PREFIX = get_settings().api_path_prefix


async def test_checker(client):
    response = await client.get(f"{API_PATH_PREFIX}/checker")
    assert response.status_code == 200


async def test_favicon(client):
    response = await client.get("/favicon.ico")
    assert response.status_code == 204


async def test_robots(client):
    response = await client.get("/robots.txt")
    assert response.status_code == 204
