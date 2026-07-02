from app.settings import get_settings

ROOT_PATH = get_settings().root_path


async def test_checker(client):
    response = await client.get(f"{ROOT_PATH}/checker")
    assert response.status_code == 200


async def test_favicon(client):
    response = await client.get("/favicon.ico")
    assert response.status_code == 204


async def test_robots(client):
    response = await client.get("/robots.txt")
    assert response.status_code == 204
