import telebot
import os
import random
from openai import OpenAI
import openai
import time
import sqlite3
from functools import partial
from db import check_db, get_assistance, get_or_create_thread, update_thread_offset, disable_threads, get_threads, \
    get_or_create_mode

con = sqlite3.connect("Friday.db", check_same_thread=False)
openai.api_key = os.getenv("OPENAI_API_KEY")
token = os.getenv("TELEGRAM_API_KEY")
bot = telebot.TeleBot(token)
client = OpenAI()
check_db(con)


@bot.message_handler(commands=['change_mode'])
def change_mode(message):
    send = bot.send_message(message.chat.id, 'Какой режим вы хотите выбрать?')
    bot.register_next_step_handler(message, partial(change_m, con=con))


def change_m(message, con):
    cur = con.cursor()
    mode = message.text
    if mode != "text" or mode != "audio":
        bot.send_message(message.chat.id, f"Режима '{mode}' нет\nПопробуйте написать audio или text")
        change_mode()
    else:
        cur.execute(f"UPDATE settings SET mode = '{mode}' WHERE chat_id = '{message.chat.id}'")
        con.commit()
        bot.send_message(message.chat.id, f"Режим '{mode}' активен")


@bot.message_handler(commands=['change'])
def change_dialog(message):
    send = bot.send_message(message.chat.id, 'Введи номер желаемого thread')
    disable_threads(con, message.chat.id)
    bot.register_next_step_handler(message, partial(change, con=con))


def change(message, con):
    num = int(message.text) - 1
    cur = con.cursor()
    dialogs: list[tuple[str, str]] = get_threads(con, message.chat.id)
    thread_id, dialog = dialogs[num]
    cur.execute(f"UPDATE thread SET is_active = 1 WHERE thread_id = '{thread_id}'")
    con.commit()
    bot.send_message(message.chat.id, f"Выбранный thread активен - '{dialog}'")


@bot.message_handler(commands=['dialogs'])
def get_dialogs(message):
    dialogs: list[tuple[str, str]] = get_threads(con, message.chat.id)
    msg = "У вас доступны следующие диалоги: \n"
    if not dialogs:
        msg = "Ты ничего не писал(а), ничего не знаю, пес!"
    for index, (_, dialog) in enumerate(dialogs, start=1):
        msg += f"{index}. {dialog} \n"
    bot.send_message(message.chat.id, msg)


@bot.message_handler(commands=['ch_thread'])
def ch_thread(message):
    thread = client.beta.threads.create()
    disable_threads(con, message.chat.id)
    bot.send_message(message.chat.id, "Thread has been changed")


@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = "Здраствуйте, меня зовут Пятница \n" \
                   "Чтобы узнать, что я умею, напишите /help."

    bot.send_message(message.chat.id, welcome_text)


@bot.message_handler(commands=['poem'])
def send_poem(message):
    poem_text = "О вы которых ожидает\nОтечество от недр своих\nИ видеть таковых желает\nКаких зовет от стран чужих\n"
    bot.send_message(message.chat.id, poem_text)


@bot.message_handler(commands=['picture'])
def send_picture(message):
    v = str(random.randint(1, 10))
    anim_img = open(v + '.JPG', 'rb')
    bot.send_photo(message.chat.id, anim_img)


@bot.message_handler(commands=['music'])
def send_music(message):
    music = open('Eiro.mp3', 'rb')
    bot.send_audio(message.chat.id, music)


@bot.message_handler(commands=['video'])
def send_video(message):
    video = open('Flight.mp4', 'rb')
    bot.send_video(message.chat.id, video)


@bot.message_handler(commands=['project'])
def send_game(message):
    project = open('houses.py')
    bot.send_document(message.chat.id, project)


@bot.message_handler(commands=['help'])
def send_help(message):
    help = "/start - Приветствие \n/help - Сейчас пользуетесь \n/poem - строфа стихотворения \n" \
           "/picture - интересные фотографии" \
           "\n/music - Прикольная музыка \n/video - Интересное видео \n/project - Проект по программированию" \
           "\nТак же можно немного со мной пообщаться"
    bot.send_message(message.chat.id, help)


def txt_to_audio(message: str):
    file_name = "C:\\Users\\petrk\\AppData\\Local\\Temp\\output.mp3"
    with client.audio.speech.with_streaming_response.create(
            model="tts-1",
            voice="alloy",
            input=message,
    ) as response:
        response.stream_to_file(file_name)
        return file_name


@bot.message_handler(content_types=["text"])
def get_text_messages(message):
    thread_id, pos = get_or_create_thread(con, client, message.chat.id, message.text)
    message_ai = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message.text
    )
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=get_assistance(con, client),
    )
    run = client.beta.threads.runs.retrieve(
        thread_id=thread_id,
        run_id=run.id
    )
    while run.status != "completed":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        time.sleep(0.5)
    messages_ai = client.beta.threads.messages.list(
        thread_id=thread_id
    )
    answer = "\n".join([n.content[0].text.value for n in list(reversed(messages_ai.data))[-1:]])
    mode = get_or_create_mode(con, message.chat.id)
    if answer:
        if mode == 'text':
            bot.send_message(message.chat.id, answer)
        if mode == 'audio':
            bot.send_voice(message.chat.id, open(txt_to_audio(answer), "rb"))
    update_thread_offset(con, thread_id, len(messages_ai.data))


bot.polling()
