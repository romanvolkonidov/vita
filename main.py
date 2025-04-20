import telebot
from telebot import types
import re
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')
TEACHER_CHAT_ID = int(os.getenv('TEACHER_CHAT_ID'))

# Define quizzes for each class
quizzes = {
  "5 класс": [
    {
      "question": "2 + 2 = ?",
      "options": ["3", "4", "5"],
      "answer": "4"
    },
    {
      "question": "10 - 7 = ?",
      "options": ["2", "3", "4"],
      "answer": "3"
    }
  ],
  "6 класс": [
    {
      "question": "3 × 3 = ?",
      "options": ["6", "9", "12"],
      "answer": "9"
    },
    {
      "question": "15 ÷ 3 = ?", 
      "options": ["3", "5", "7"],
      "answer": "5"
    }
  ]
}

bot = telebot.TeleBot(API_TOKEN)

user_data = {}

def send_results(chat_id):
    data = user_data[chat_id]
    total = len(data['quiz'])
    correct = data['score']
    percent = round((correct / total) * 100)

    report = f"📝 Результаты теста\n👤 Имя: {data['name']}\n🏫 Класс: {data['class']}\n📊 Правильных: {correct}/{total} ({percent}%)\n\n"
    for i, a in enumerate(data['answers'], 1):
        status = "✅" if a['correct'] else "❌"
        report += f"{i}. {a['question']}\nОтвет ученика: {a['your_answer']}\nПравильный ответ: {a['correct_answer']} {status}\n\n"

    # Send report to teacher
    bot.send_message(TEACHER_CHAT_ID, report)

    # Offer student to leave email for results and show % correct
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("Да", "Нет")
    bot.send_message(
        chat_id,
        f"Спасибо за выполнение теста! Результаты отправлены твоему учителю, и он сообщит тебе оценку.\n"
        f"Ты ответил(а) правильно на {percent}% вопросов.\n"
        "Хочешь оставить свой email, чтобы учитель мог отправить тебе результаты?",
        reply_markup=markup
    )
    user_data[chat_id]['step'] = 'ask_email'

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'ask_email')
def ask_email(message):
    chat_id = message.chat.id
    text = message.text.strip()
    # Simple email check
    if re.match(r"[^@]+@[^@]+\.[^@]+", text):
        data = user_data.get(chat_id, {})
        name = data.get('name', 'Неизвестно')
        school_class = data.get('class', 'Неизвестно')
        bot.send_message(TEACHER_CHAT_ID, f"Ученик {name} ({school_class}) оставил email для отправки результатов: {text}")
        bot.send_message(chat_id, "Спасибо! Ваш email передан учителю.")
        user_data.pop(chat_id, None)
        return
    if text == "Да":
        bot.send_message(chat_id, "Пожалуйста, напиши свой email:")
        user_data[chat_id]['step'] = 'get_email'
    else:
        bot.send_message(chat_id, "Спасибо! Ожидай обратной связи от учителя.")
        user_data.pop(chat_id, None)

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'get_email')
def save_email(message):
    chat_id = message.chat.id
    email = message.text
    # Notify teacher about student's email
    data = user_data.get(chat_id, {})
    name = data.get('name', 'Неизвестно')
    school_class = data.get('class', 'Неизвестно')
    bot.send_message(TEACHER_CHAT_ID, f"Ученик {name} ({school_class}) оставил email для отправки результатов: {email}")
    bot.send_message(chat_id, "Спасибо! Ваш email передан учителю.")
    user_data.pop(chat_id, None)

@bot.message_handler(commands=['start'])
def ask_name(message):
    print(f"User chat id: {message.chat.id}")  # Add this line for debugging
    user_data[message.chat.id] = {}
    bot.send_message(message.chat.id, "Привет! Введи, пожалуйста, своё имя (например: Иван Иванов).")
    user_data[message.chat.id]['step'] = 'name'

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'name')
def save_name(message):
    user_data[message.chat.id]['name'] = message.text
    user_data[message.chat.id]['step'] = 'class'
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for school_class in quizzes.keys():
        markup.add(school_class)
    bot.send_message(message.chat.id, "Спасибо! В какой класс ты ходишь? Выбери из списка:", reply_markup=markup)

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'class' and m.text in quizzes)
def start_quiz(message):
    chat_id = message.chat.id
    chosen_class = message.text
    user_data[chat_id].update({
        'class': chosen_class,
        'quiz': quizzes[chosen_class],
        'q': 0,
        'score': 0,
        'answers': [],
        'step': 'quiz'
    })
    send_question(chat_id)

def send_question(chat_id):
    q_index = user_data[chat_id]['q']
    quiz = user_data[chat_id]['quiz']
    if q_index < len(quiz):
        question = quiz[q_index]
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        for opt in question["options"]:
            markup.add(opt)
        bot.send_message(chat_id, question["question"], reply_markup=markup)
    else:
        send_results(chat_id)

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'quiz')
def handle_answer(message):
    chat_id = message.chat.id
    data = user_data[chat_id]
    q_index = data['q']
    question = data['quiz'][q_index]
    user_answer = message.text

    # Accept only valid options
    if user_answer not in question['options']:
        bot.send_message(chat_id, "Пожалуйста, выбери вариант ответа с клавиатуры.")
        return

    correct = user_answer == question['answer']
    data['answers'].append({
        'question': question['question'],
        'your_answer': user_answer,
        'correct_answer': question['answer'],
        'correct': correct
    })
    if correct:
        data['score'] += 1
    data['q'] += 1
    send_question(chat_id)

if __name__ == '__main__':
    bot.polling()
