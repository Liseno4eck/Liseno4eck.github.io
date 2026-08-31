import os, json, secrets, sqlite3, asyncio
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from telegram import Bot

BASE = Path(__file__).resolve().parent
DB = BASE / "data.db"
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
BOT_USERNAME = os.getenv("BOT_USERNAME", "").lstrip("@")

app = Flask(__name__, static_folder=str(BASE))

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con=db()
    con.execute("""CREATE TABLE IF NOT EXISTS creators(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        first_name TEXT,
        code TEXT UNIQUE NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS configs(
        id TEXT PRIMARY KEY,
        creator_id INTEGER NOT NULL,
        config_json TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    con.commit();con.close()

def creator_by_code(code):
    con=db(); row=con.execute("SELECT * FROM creators WHERE code=?",(code,)).fetchone();con.close();return row

async def notify(telegram_id, text):
    if not BOT_TOKEN or not telegram_id: return
    try:
        bot=Bot(BOT_TOKEN)
        await bot.send_message(chat_id=telegram_id,text=text)
        await bot.close()
    except Exception as e:
        print("Telegram notification error:",e)

def run_notify(telegram_id,text):
    try: asyncio.run(notify(telegram_id,text))
    except Exception as e: print(e)

@app.get("/")
def index():
    return send_from_directory(BASE,"index.html")

@app.get("/api/config/<cid>")
def get_config(cid):
    con=db(); row=con.execute("SELECT config_json FROM configs WHERE id=?",(cid,)).fetchone();con.close()
    if not row: return jsonify({"error":"Ссылка не найдена"}),404
    return jsonify(json.loads(row["config_json"]))

@app.post("/api/config")
def create_config():
    data=request.get_json(force=True)
    code=str(data.get("creator_code","")).strip()
    cfg=data.get("config") or {}
    owner=creator_by_code(code)
    if not owner: return jsonify({"error":"Код создателя не найден. Нажми /start в боте и используй выданный код."}),403
    if not cfg.get("name") or not cfg.get("birthday"): return jsonify({"error":"Заполни имя и дату."}),400
    cid=secrets.token_urlsafe(8).replace("-","_")
    con=db();con.execute("INSERT INTO configs(id,creator_id,config_json) VALUES(?,?,?)",(cid,owner["id"],json.dumps(cfg,ensure_ascii=False)));con.commit();con.close()
    return jsonify({"id":cid,"url":PUBLIC_BASE_URL+"/?id="+cid if PUBLIC_BASE_URL else "/?id="+cid})

@app.post("/api/event")
def event():
    data=request.get_json(force=True)
    cid=data.get("config_id"); event=data.get("event"); text=data.get("text","")
    con=db(); row=con.execute("""SELECT c.config_json,u.telegram_id,u.first_name,u.username
        FROM configs c JOIN creators u ON u.id=c.creator_id WHERE c.id=?""",(cid,)).fetchone();con.close()
    if not row: return jsonify({"error":"not found"}),404
    cfg=json.loads(row["config_json"])
    # Имя посетителя берём из добровольно введённого поля, если оно передано.
    visitor=(data.get("event_name") or "").strip()
    name=visitor or "Кто-то"
    owner=row["telegram_id"]
    if event=="open": msg=f"{name} открыл твою эмоцию ❤️"
    elif event=="birthday": msg=f"{name} ввел правильную дату ❤️"
    elif event=="yes": msg=f"{name} нажал(а) «Да» ❤️"
    elif event=="reply": msg=f"{name} отправил(а) тебе письмо:\n\n{text[:4000]}"
    else: return jsonify({"ok":True})
    run_notify(owner,msg)
    return jsonify({"ok":True})

@app.get("/health")
def health(): return jsonify({"ok":True})

if __name__=="__main__":
    init_db()
    app.run(host="0.0.0.0",port=int(os.getenv("PORT","8080")))
