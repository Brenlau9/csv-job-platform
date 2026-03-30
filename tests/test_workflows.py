from typing import Any

import pytest
from httpx import AsyncClient


async def register_and_login(
    client: AsyncClient,
    email: str,
    password: str = "supersecret123",
) -> dict[str, str]:
    register_response = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 201

    login_response = await client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def upload_csv(
    client: AsyncClient,
    headers: dict[str, str],
    filename: str = "jobs.csv",
    content: bytes = b"id,name,age,city\n1,Alice,30,Seattle\n2,,25,\n",
) -> dict[str, Any]:
    response = await client.post(
        "/api/files",
        headers=headers,
        files={"upload": (filename, content, "text/csv")},
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.anyio
async def test_auth_flow_register_login_and_access_protected_route(
    async_client: AsyncClient,
) -> None:
    headers = await register_and_login(async_client, "auth@example.com")

    me_response = await async_client.get("/api/auth/me", headers=headers)

    assert me_response.status_code == 200
    assert me_response.json()["email"] == "auth@example.com"


@pytest.mark.anyio
async def test_file_upload_flow_accepts_csv_and_rejects_invalid_type(
    async_client: AsyncClient,
) -> None:
    headers = await register_and_login(async_client, "files@example.com")

    upload_response = await async_client.post(
        "/api/files",
        headers=headers,
        files={"upload": ("jobs.csv", b"id,name\n1,Alice\n", "text/csv")},
    )
    invalid_response = await async_client.post(
        "/api/files",
        headers=headers,
        files={"upload": ("notes.txt", b"not,a,csv\n", "text/plain")},
    )

    assert upload_response.status_code == 201
    assert upload_response.json()["original_filename"] == "jobs.csv"
    assert invalid_response.status_code == 400
    assert invalid_response.json()["detail"] == "Only .csv files are allowed"


@pytest.mark.anyio
async def test_job_creation_flow_rejects_another_users_file(
    async_client: AsyncClient,
    mock_celery_delay: Any,
) -> None:
    owner_headers = await register_and_login(async_client, "owner@example.com")
    other_headers = await register_and_login(async_client, "other@example.com")
    uploaded_file = await upload_csv(async_client, owner_headers)

    create_response = await async_client.post(
        "/api/jobs",
        headers=owner_headers,
        json={"file_id": uploaded_file["id"], "job_type": "summarize"},
    )
    foreign_response = await async_client.post(
        "/api/jobs",
        headers=other_headers,
        json={"file_id": uploaded_file["id"], "job_type": "summarize"},
    )

    assert create_response.status_code == 201
    assert create_response.json()["status"] == "QUEUED"
    assert mock_celery_delay.queued_job_ids == [create_response.json()["id"]]
    assert foreign_response.status_code == 404
    assert foreign_response.json()["detail"] == "File not found"


@pytest.mark.anyio
async def test_job_result_flow_processes_job_and_returns_expected_shape(
    async_client: AsyncClient,
    mock_celery_delay: Any,
) -> None:
    headers = await register_and_login(async_client, "result@example.com")
    uploaded_file = await upload_csv(async_client, headers)

    create_response = await async_client.post(
        "/api/jobs",
        headers=headers,
        json={"file_id": uploaded_file["id"], "job_type": "summarize"},
    )
    assert create_response.status_code == 201
    job_id = create_response.json()["id"]

    mock_celery_delay.run_next_async()

    for _ in range(30):
        status_response = await async_client.get(f"/api/jobs/{job_id}", headers=headers)
        assert status_response.status_code == 200
        if status_response.json()["status"] == "COMPLETED":
            break
    else:
        pytest.fail("Job did not complete in time")

    result_response = await async_client.get(f"/api/jobs/{job_id}/result", headers=headers)

    assert result_response.status_code == 200
    assert result_response.json() == {
        "job_id": job_id,
        "result": {
            "row_count": 2,
            "column_count": 4,
            "columns": ["id", "name", "age", "city"],
            "null_counts": {"id": 0, "name": 1, "age": 0, "city": 1},
        },
    }


@pytest.mark.anyio
async def test_list_jobs_returns_only_current_users_jobs_and_paginates(
    async_client: AsyncClient,
    mock_celery_delay: Any,
) -> None:
    owner_headers = await register_and_login(async_client, "history-owner@example.com")
    other_headers = await register_and_login(async_client, "history-other@example.com")

    owner_job_ids: list[int] = []
    for index in range(3):
        uploaded_file = await upload_csv(
            async_client,
            owner_headers,
            filename=f"owner-{index}.csv",
            content=f"id,name\n{index},Owner{index}\n".encode(),
        )
        response = await async_client.post(
            "/api/jobs",
            headers=owner_headers,
            json={"file_id": uploaded_file["id"], "job_type": "summarize"},
        )
        owner_job_ids.append(response.json()["id"])

    other_file = await upload_csv(async_client, other_headers, filename="other.csv")
    other_response = await async_client.post(
        "/api/jobs",
        headers=other_headers,
        json={"file_id": other_file["id"], "job_type": "summarize"},
    )
    other_job_id = other_response.json()["id"]

    page_one_response = await async_client.get(
        "/api/jobs?page=1&page_size=2",
        headers=owner_headers,
    )
    page_two_response = await async_client.get(
        "/api/jobs?page=2&page_size=2",
        headers=owner_headers,
    )

    assert page_one_response.status_code == 200
    assert page_two_response.status_code == 200

    page_one = page_one_response.json()
    page_two = page_two_response.json()

    assert page_one["page"] == 1
    assert page_one["page_size"] == 2
    assert page_one["total"] == 3
    assert [item["job_id"] for item in page_one["items"]] == owner_job_ids[::-1][:2]

    assert page_two["page"] == 2
    assert page_two["page_size"] == 2
    assert page_two["total"] == 3
    assert [item["job_id"] for item in page_two["items"]] == owner_job_ids[::-1][2:]

    returned_ids = {item["job_id"] for item in page_one["items"] + page_two["items"]}
    assert other_job_id not in returned_ids
