from app.openapi import INTERNAL_TAG, JOBS_TAG

# With root_path set, the OpenAPI spec lists bare route paths (the prefix lives
# in the servers URL), so paths are asserted without the root_path prefix.


async def test_get_openapi_json(client):
    response = await client.get("/openapi.json")

    assert response.status_code == 200, f"Unexpected response {response.status_code}"
    assert response.headers["content-type"].startswith("application/json")


async def test_get_openapi_doc(client):
    response = await client.get("/docs")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


async def test_get_openapi_redoc(client):
    response = await client.get("/redoc")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


async def test_default_spec_excludes_internal_routes(client):
    spec = (await client.get("/openapi.json")).json()

    assert "/checker" not in spec["paths"]


async def test_default_spec_excludes_internal_tag(client):
    spec = (await client.get("/openapi.json")).json()

    tag_names = [t["name"] for t in spec["tags"]]
    assert INTERNAL_TAG not in tag_names
    assert JOBS_TAG in tag_names


async def test_internal_openapi_json(client):
    response = await client.get("/internal/openapi.json")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


async def test_internal_spec_contains_checker_route(client):
    spec = (await client.get("/internal/openapi.json")).json()

    assert "/checker" in spec["paths"]


async def test_internal_spec_excludes_job_routes(client):
    spec = (await client.get("/internal/openapi.json")).json()

    assert "/jobs" not in spec["paths"]


async def test_internal_spec_excludes_job_tag(client):
    spec = (await client.get("/internal/openapi.json")).json()

    tag_names = [t["name"] for t in spec["tags"]]
    assert JOBS_TAG not in tag_names
    assert INTERNAL_TAG in tag_names


async def test_internal_docs(client):
    response = await client.get("/internal/docs")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


async def test_internal_redoc(client):
    response = await client.get("/internal/redoc")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


async def test_default_spec_has_no_422_responses(client):
    spec = (await client.get("/openapi.json")).json()

    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            assert "422" not in operation.get("responses", {}), (
                f"422 response found at {method.upper()} {path}"
            )


async def test_internal_spec_has_no_422_responses(client):
    spec = (await client.get("/internal/openapi.json")).json()

    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            assert "422" not in operation.get("responses", {}), (
                f"422 response found at {method.upper()} {path}"
            )
