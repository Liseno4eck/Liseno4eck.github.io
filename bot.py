import os, sqlite3, secrets, asyncio
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BASE=Path(__file__).resolve().parent
DB=BASE/"data.db"
TOKEN=os.getenv("BOT_TOKEN","").strip()
PUBLIC_BASE_URL=os.getenv("PUBLIC_BASE_URL","").rstrip("/")
BOT_USERNAME=os.getenv("BOT_USERNAME","").lstrip("@")

def db():
    con=sqlite3.connect(DB);con.row_factory=sqlite3.Row;return con

def init_db():
    con=db()
    con.execute("""CREATE TABLE IF NOT EXISTS creators(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        username TEXT, first_name TEXT,
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

async def start(update:Update, context:ContextTypes.DEFAULT_TYPE):
    u=update.effective_user
    con=db();row=con.execute("SELECT * FROM creators WHERE telegram_id=?",(u.id,)).fetchone()
    if row:
        code=row["code"]
    else:
        code=secrets.token_urlsafe(12).replace("-","_")
        con.execute("INSERT INTO creators(telegram_id,username,first_name,code) VALUES(?,?,?,?)",(u.id,u.username,u.first_name,code));con.commit()
    con.close()
    text=(
        f"Привет, {u.first_name or 'друг'}! ❤️\n\n"
        "Ты зарегистрирован.\n\n"
        f"Твой код создателя:\n`{code}`\n\n"
        "Скопируй этот код и вставь его в секретную панель сайта (комбинация 304056).\n"
        "После создания ссылки уведомления о событиях будут приходить сюда.\n\n"
        "Кнопка «Войти» на сайте просто открывает этот бот."
    )
    await update.message.reply_text(text,parse_mode="Markdown")

def main():
    if not TOKEN: raise SystemExit("Укажи BOT_TOKEN в переменных окружения.")
    init_db()
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.run_polling()

if __name__=="__main__":
    main()
