import io
import contextlib
from itertools import cycle
import datetime
from flask import Flask, jsonify, request


status_lst = ["cancelled", "completed", "in_progress", "pending"]
priority_lst = ["high", "low", "medium"]

def get_task_list():
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        import this
    text = f.getvalue()
    status_cycle = cycle(status_lst)
    priority_cycle = cycle(priority_lst)
    tasks_lst = []
    num = 0
    for line in text.splitlines():
        if not line:
            continue
        num += 1
        tasks_lst.append({
            "id": num,
            "title": "Zen of Python",
            "description": line,
            "status": next(status_cycle),
            "priority": next(priority_cycle),
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "deleted_at": None,
        })
    return tasks_lst

tasks_lst = get_task_list()

app = Flask(__name__)


VALID_STATUSES = ["cancelled", "completed", "in_progress", "pending"]
VALID_PRIORITIES = ["high", "low", "medium"]


@app.route("/api/v1/tasks", methods=["GET"])
def get_tasks_lst():
    query = request.args.get("query", "").lower()
    order_param = request.args.get("order", "id")
    offset = int(request.args.get("offset", 0) or 0)

    filtered = tasks_lst
    if query:
        filtered = [t for t in tasks_lst if query in t["title"].lower() or query in t["description"].lower()]

    reverse = False
    field = order_param
    if order_param.startswith("-"):
        field = order_param[1:]
        reverse = True

    try:
        filtered = sorted(filtered, key=lambda x: x[field], reverse=reverse)
    except (KeyError, TypeError):
        filtered = sorted(filtered, key=lambda x: x["id"], reverse=reverse)

    paginated = filtered[offset:offset + 10]
    return jsonify({"tasks": paginated}), 200


@app.route("/api/v1/tasks/<task_id>", methods=["GET"])
def get_tasks(task_id):
    task_id = int(task_id)
    task = None
    for t in tasks_lst:
        if t["id"] == task_id:
            task = t
            break

    if not task:
        return jsonify({"error": "Задача не найдена"}), 404
    return jsonify(task), 200


@app.route("/api/v1/tasks", methods=["POST"])
def post_tasks():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Отсутствуют данные JSON"}), 400

    if "title" not in data:
        return jsonify({"error": "Пропущен обязательный параметр `title`"}), 400
    if "description" not in data:
        return jsonify({"error": "Пропущен обязательный параметр `description`"}), 400

    status = data.get("status", "pending")
    priority = data.get("priority", "medium")

    if status not in VALID_STATUSES:
        return jsonify({"error": "Поле `status` невалидно"}), 400
    if priority not in VALID_PRIORITIES:
        return jsonify({"error": "Поле `priority` невалидно"}), 400

    now = datetime.datetime.now().isoformat()
    new_task = {
        "id": len(tasks_lst) + 1,
        "title": data["title"],
        "description": data["description"],
        "status": status,
        "priority": priority,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None
    }
    tasks_lst.append(new_task)
    return jsonify(new_task), 200


@app.route("/api/v1/tasks/<task_id>", methods=["DELETE"])
def delete_tasks(task_id):
    task_id = int(task_id)
    task = None
    for t in tasks_lst:
        if t["id"] == task_id:
            task = t
            break

    if not task:
        return jsonify({"error": "Задача не найдена"}), 404

    now = datetime.datetime.now().isoformat()
    task["status"] = "cancelled"
    task["deleted_at"] = now
    task["updated_at"] = now
    return jsonify(task), 200


@app.route("/api/v1/tasks/<task_id>", methods=["PATCH"])
def patch_tasks(task_id):
    task_id = int(task_id)
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Отсутствуют данные JSON"}), 400

    task = None
    for t in tasks_lst:
        if t["id"] == task_id:
            task = t
            break

    if not task:
        return jsonify({"error": "Задача не найдена"}), 404

    if "status" in data:
        if data["status"] not in VALID_STATUSES:
            return jsonify({"error": "Поле `status` невалидно"}), 400
        task["status"] = data["status"]

    if "priority" in data:
        if data["priority"] not in VALID_PRIORITIES:
            return jsonify({"error": "Поле `priority` невалидно"}), 400
        task["priority"] = data["priority"]

    if "title" in data:
        task["title"] = data["title"]
    if "description" in data:
        task["description"] = data["description"]

    task["updated_at"] = datetime.datetime.now().isoformat()
    return jsonify(task), 200


if __name__ == "__main__":
    app.run(debug=True)