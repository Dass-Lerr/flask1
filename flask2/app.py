from flask import Flask, request, render_template
import os, uuid, hashlib, json

app = Flask(__name__)
app.secret_key = 'secret'
upload = 'upload'
os.makedirs(upload, exist_ok=True)

blocked = {'exe', 'sh', 'php', 'js'}



def load_json(folder_name, file_name):
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)
    full_path = os.path.join(folder_name, file_name)
    if not os.path.exists(full_path):
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return []
    with open(full_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(folder_name, file_name, data):
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)
    full_path = os.path.join(folder_name, file_name)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_md5(f):
    h = hashlib.md5()
    for chunk in iter(lambda: f.read(4096), b''):
        h.update(chunk)
    f.seek(0)
    return h.hexdigest()



files_db = load_json('data', 'files.json')


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            return render_template('index.html', error='файл не выбран', files=files_db)

        name = file.filename
        ext = name.rsplit('.', 1)[-1].lower()
        if ext in blocked:
            return render_template('index.html', error=f'расширение .{ext} запрещено', files=files_db)

        md5 = get_md5(file)
        for f in files_db:
            if f['md5'] == md5:
                return render_template('index.html', error='такой файл уже есть', files=files_db)

        uid = uuid.uuid4().hex
        p1, p2 = uid[:2], uid[2:4]
        rel = os.path.join(p1, p2, f'{uid}.{ext}')
        full = os.path.join(upload, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        file.save(full)

        files_db.append({
            'original': name,
            'path': rel,
            'md5': md5,
            'size': os.path.getsize(full)
        })


        save_json('data', 'files.json', files_db)

        return render_template('index.html', success='загружено!', files=files_db)

    return render_template('index.html', files=files_db)


if __name__ == '__main__':
    app.run(debug=True)