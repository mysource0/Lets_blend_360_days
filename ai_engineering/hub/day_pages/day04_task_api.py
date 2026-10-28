"""Day 04 — Task Management API client (CRUD interface for the FastAPI server)."""

import streamlit as st

API_BASE = "http://127.0.0.1:8000"
UNREACHABLE = "unreachable"


def _api_request(method: str, path: str, json_body=None):
    """Call the Day 04 API. Returns (response, error); error is UNREACHABLE or a message."""
    import httpx
    url = f"{API_BASE}{path}"
    try:
        with httpx.Client(timeout=10) as client:
            return client.request(method, url, json=json_body), None
    except httpx.ConnectError:
        return None, UNREACHABLE
    except httpx.HTTPError as exc:
        return None, f"Request to the Task API failed: {exc}"


def render():
    st.caption("CRUD interface for the local Task Management REST API")

    # ── Connection check ───────────────────────────────────────────────
    health, error = _api_request("GET", "/tasks")
    if error == UNREACHABLE:
        st.warning("⚠️ The Task API is not running.")
        st.markdown(
            """
**To start the API server**, open a separate terminal in the project root (the folder that contains `ai_engineering/`) and run:

```powershell
cd path\\to\\Lets_blend_360_days
.\\venv\\Scripts\\python.exe -m uvicorn task_api.main:app --app-dir .\\ai_engineering\\04_enhanced_dev_codex --reload
```

The API will be available at `http://127.0.0.1:8000` with docs at `/docs`.

Once the server is running, **refresh this page** to connect.
            """
        )
        return
    if error:
        st.error(error)
        return

    st.success("✅ Connected to Task API")

    # ── Create task ────────────────────────────────────────────────────
    with st.expander("➕ Create New Task", expanded=False):
        with st.form("create_task_form"):
            title = st.text_input("Title", placeholder="e.g. Review PR #42")
            description = st.text_area("Description (optional)", placeholder="Details…")
            status = st.selectbox("Status", ["todo", "in_progress", "done"])
            submitted = st.form_submit_button("Create Task", type="primary")

            if submitted:
                if not title or not title.strip():
                    st.error("Title is required.")
                else:
                    body = {"title": title.strip(), "status": status}
                    if description and description.strip():
                        body["description"] = description.strip()
                    resp, error = _api_request("POST", "/tasks", body)
                    if resp is not None and resp.status_code == 201:
                        st.success(f"✅ Task created (ID: {resp.json()['id']})")
                        st.rerun()
                    elif resp is not None:
                        st.error(f"Error {resp.status_code}: {resp.text}")
                    else:
                        st.error(error if error != UNREACHABLE else "Could not reach the API.")

    st.divider()

    # ── Task list ──────────────────────────────────────────────────────
    st.subheader("📋 All Tasks")
    resp, error = _api_request("GET", "/tasks")
    if resp is None or resp.status_code != 200:
        st.error(f"Failed to fetch tasks{f': {error}' if error and error != UNREACHABLE else '.'}")
        return

    tasks = resp.json()
    if not tasks:
        st.info("No tasks yet. Create one above!")
        return

    # Status filter
    statuses = sorted({t["status"] for t in tasks})
    filter_status = st.multiselect("Filter by status", statuses, default=statuses, key="day04_filter")
    filtered = [t for t in tasks if t["status"] in filter_status]

    for task in filtered:
        status_emoji = {"todo": "⬜", "in_progress": "🔶", "done": "✅"}.get(task["status"], "❓")
        with st.expander(f"{status_emoji} #{task['id']} — {task['title']}"):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown(f"**Status:** `{task['status']}`")
                st.markdown(f"**Created:** {task.get('created_at', 'N/A')}")
                if task.get("description"):
                    st.markdown(f"**Description:** {task['description']}")
                else:
                    st.caption("No description")

            with col2:
                # Update status
                new_status = st.selectbox(
                    "Change status",
                    ["todo", "in_progress", "done"],
                    index=["todo", "in_progress", "done"].index(task["status"]),
                    key=f"day04_status_{task['id']}",
                )
                if new_status != task["status"]:
                    if st.button("💾 Update", key=f"day04_update_{task['id']}"):
                        resp, error = _api_request("PATCH", f"/tasks/{task['id']}", {"status": new_status})
                        if resp is not None and resp.status_code == 200:
                            st.success("Updated!")
                            st.rerun()
                        else:
                            st.error(error or "Update failed.")

                # Delete: two steps so a single click cannot remove a task
                confirm_key = f"day04_confirm_delete_{task['id']}"
                if not st.session_state.get(confirm_key):
                    if st.button("🗑️ Delete", key=f"day04_delete_{task['id']}"):
                        st.session_state[confirm_key] = True
                        st.rerun()
                else:
                    st.warning(f"Delete task #{task['id']}? This cannot be undone.")
                    if st.button("Yes, delete", type="primary", key=f"day04_confirm_yes_{task['id']}"):
                        resp, error = _api_request("DELETE", f"/tasks/{task['id']}")
                        st.session_state.pop(confirm_key, None)
                        if resp is not None and resp.status_code == 204:
                            st.success("Deleted!")
                            st.rerun()
                        else:
                            st.error(error or "Delete failed.")
                    if st.button("Cancel", key=f"day04_confirm_no_{task['id']}"):
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
