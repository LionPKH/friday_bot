def voice(client):
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input="Hello world! This is a streaming test.",
    )

    response.stream_to_file("output.mp3")


def check_db(con):
    cur = con.cursor()
    res = cur.execute("SELECT name FROM sqlite_master WHERE name='assistance'")
    if not res.fetchone():
        cur.execute("create table assistance (id TEXT constraint assistance_pk primary key, role TEXT);")
        con.commit()

    res1 = cur.execute("SELECT name FROM sqlite_master WHERE name='thread'")
    if not res1.fetchone():
        cur.execute(
            "create table thread (id INTEGER, chat_id TEXT, thread_id TEXT, message TEXT, offset INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1);")
        con.commit()
    res2 = cur.execute("SELECT name FROM sqlite_master WHERE name='settings'")
    if not res2.fetchone():
        cur.execute("CREATE TABLE settings (chat_id TEXT, mode TEXT DEFAULT 'text');")
        con.commit()


def get_threads(con, chat_id: str) -> list[tuple[str, str]]:
    cur = con.cursor()
    res = cur.execute(f"SELECT thread_id, message FROM thread WHERE chat_id = '{chat_id}' ORDER BY thread_id")
    return [(row[0], row[1]) for row in res.fetchall()]


def disable_threads(con, chat_id):
    cur = con.cursor()
    cur.execute(f"UPDATE thread SET is_active = 0 WHERE chat_id = '{chat_id}'")

    con.commit()


def get_assistance(con, client) -> str:
    cur = con.cursor()
    res = cur.execute("SELECT id FROM assistance LIMIT 1")
    if raw_assistant_id := res.fetchone():
        print(f"Готовый {raw_assistant_id[0]=}")
        return raw_assistant_id[0]
    assistant = client.beta.assistants.create(
        name="Math Tutor",
        instructions="You are a personal math tutor. Write and run code to answer math questions.",
        tools=[{"type": "code_interpreter"}],
        model="gpt-3.5-turbo"
    )
    cur.execute(f"INSERT INTO assistance VALUES ('{assistant.id}', 'Math tutor')")
    con.commit()
    print(f"Новый {assistant.id=}")
    return assistant.id


def get_or_create_thread(con, client, chat_id: str, msg: str) -> tuple[str, int]:
    cur = con.cursor()
    res = cur.execute(f"SELECT thread_id, offset FROM thread WHERE chat_id='{chat_id}' AND is_active = 1 LIMIT 1")
    if raw_thread := res.fetchone():
        return raw_thread[0], raw_thread[1]
    # Если thread не создан, создается новый
    thread = client.beta.threads.create()
    cur.execute(f"INSERT INTO thread(chat_id, thread_id, message) VALUES ('{chat_id}','{thread.id}', '{msg}')")
    con.commit()
    return thread.id, 0


def get_or_create_mode(con, chat_id: str) -> str:
    cur = con.cursor()
    res = cur.execute(f"SELECT chat_id, mode FROM settings WHERE chat_id='{chat_id}' LIMIT 1")
    if raw_thread := res.fetchone():
        return raw_thread[1]
    # Если thread не создан, создается новый
    cur.execute(f"INSERT INTO settings(chat_id) VALUES ('{chat_id}')")
    con.commit()
    return 'text'


def update_thread_offset(con, thread_id: str, offset: int):
    cur = con.cursor()
    cur.execute(f"UPDATE thread SET offset = {offset} WHERE thread_id = '{thread_id}'")
    con.commit()


def change_mod_text(con, thread_id):
    cur = con.cursor()
    cur.execute(f"UPDATE settings SET mode = text WHERE thread_id = '{thread_id}'")


def change_mod_audio(con, thread_id):
    cur = con.cursor()
    cur.execute(f"UPDATE settings SET mode = audio WHERE thread_id = '{thread_id}'")
