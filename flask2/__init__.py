from flask import Flask, request, make_response
import os, uuid, hashlib

app = Flask(__name__)
app.secret_key = 'secret'
UPLOAD = 'upload'
os.makedirs(UPLOAD, exist_ok=True)

blocked = {'exe', 'sh', 'php', 'js'}
files_db = []


def get_md5(f):
    h = hashlib.md5()
    for chunk in iter(lambda: f.read(4096), b''):
        h.update(chunk)
    f.seek(0)
    return h.hexdigest()


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            return make_response('<h1>файл не выбран</h1><a href="/">назад</a>')

        name = file.filename
        ext = name.rsplit('.', 1)[-1].lower()
        if ext in blocked:
            return make_response(f'<h1>расширение .{ext} запрещено</h1><a href="/">назад</a>')

        md5 = get_md5(file)
        for f in files_db:
            if f['md5'] == md5:
                return make_response('<h1>такой файл уже есть</h1><a href="/">назад</a>')

        uid = uuid.uuid4().hex
        p1, p2 = uid[:2], uid[2:4]
        rel = os.path.join(p1, p2, f'{uid}.{ext}')
        full = os.path.join(UPLOAD, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        file.save(full)

        files_db.append({
            'original': name,
            'path': rel,
            'md5': md5,
            'size': os.path.getsize(full)
        })

        table = ''.join(
            [f"<tr><td>{f['original']}</td><td>/upload/{f['path']}</td><td>{f['md5']}</td><td>{f['size']} б</td></tr>"
             for f in files_db])

        html = f'''<!doctype html>
<html><head><meta charset="utf-8"><title>загрузка</title></head>
<body style="font-family:sans-serif;max-width:700px;margin:20px auto">
  <h2>загрузить файл</h2>
  <h3 style="color:green">загружено!</h3>
  <form method="post" enctype="multipart/form-data">
    <input type="file" name="file" required>
    <button>отправить</button>
  </form>
  <h3>файлы ({len(files_db)})</h3>
  <table border="1" style="width:100%;border-collapse:collapse">
    <tr><th>имя</th><th>путь</th><th>md5</th><th>размер</th></tr>
    {table}
  </table>
</body></html>'''
        return make_response(html)

    table = ''.join(
        [f"<tr><td>{f['original']}</td><td>/upload/{f['path']}</td><td>{f['md5']}</td><td>{f['size']} б</td></tr>" for f
         in files_db]) if files_db else '<tr><td colspan="4">пусто</td></tr>'

    html = f'''<!doctype html>
<html><head><meta charset="utf-8"><title>загрузка</title></head>
<body style="font-family:sans-serif;max-width:700px;margin:20px auto">
  <h2>загрузить файл</h2>
  <form method="post" enctype="multipart/form-data">
    <input type="file" name="file" required>
    <button>отправить</button>
  </form>
  <h3>файлы ({len(files_db)})</h3>
  <table border="1" style="width:100%;border-collapse:collapse">
    <tr><th>имя</th><th>путь</th><th>md5</th><th>размер</th></tr>
    {table}
  </table>
</body></html>'''
    return make_response(html)


if __name__ == '__main__':
    app.run(debug=True)