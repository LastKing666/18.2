from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import State, StatesGroup
import sqlite3
from datetime import datetime

# Токен бота Telegram
TOKEN = "6167911156:AAEmTaboT2gl8WtXt5VA_6dlxycuvkonGLY"

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Структура состояний беседы
class ConversationStates(StatesGroup):
    ADD_EMPLOYEE = State()  # Добавление сотрудника
    REMOVE_EMPLOYEE = State()  # Удаление сотрудника
    ASSIGN_TASK = State()  # Назначение задачи
    ASSIGN_TASK_NEXT = State()  # Продолжение назначения задачи
    SELECT_EMPLOYEE_TASK = State()  # Выбор задачи у сотрудника
    START_TASK_EXECUTION = State()  # Начало выполнения задачи
    STOP_TASK_EXECUTION = State()  # Выбор задачи у сотрудника
    STOP_TASK_EXECUTION_NEXT = State()  # окончание выполнения задачи

# Функция для подключения к базе данных SQLite
def connect_db():
    conn = sqlite3.connect('company.db')
    return conn

# Функция для создания таблицы сотрудников
def create_employees_table():
    conn = connect_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS employees
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)''')
    conn.commit()
    conn.close()

# Функция для создания таблицы задач
def create_tasks_table():
    conn = connect_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 employee_id INTEGER,
                 task TEXT,
                 assigned_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 start_time TIMESTAMP,
                 stop_time TIMESTAMP,
                 FOREIGN KEY (employee_id) REFERENCES employees(id))''')
    conn.commit()
    conn.close()

# Функция для получения имен сотрудников
def get_employee_names():
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT name FROM employees")
    names = [row[0] for row in c.fetchall()]
    conn.close()
    return names

# Функция для получения задач сотрудника
def get_employee_tasks(employee_name):
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT task FROM tasks JOIN employees ON tasks.employee_id = employees.id WHERE employees.name=?", (employee_name,))
    tasks = [row[0] for row in c.fetchall()]
    conn.close()
    return tasks

# Обработчик команды /tasks
@dp.message_handler(Command("tasks"))
async def tasks_command(message: types.Message):
    employees = get_employee_names()
    for employee_name in employees:
        tasks = get_employee_tasks(employee_name)
        if tasks:
            response = f"Задачи сотрудника {employee_name}:\n"
            for task in tasks:
                task_state = get_task_state(employee_name, task)
                response += f"Задача: {task}\nСостояние: {task_state}\n"
            await message.reply(response)
        else:
            await message.reply(f"У сотрудника {employee_name} нет назначенных задач.")

# Функция для получения состояния задачи
def get_task_state(employee_name, task):
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT start_time, stop_time FROM tasks JOIN employees ON tasks.employee_id = employees.id WHERE employees.name=? AND tasks.task=?", (employee_name, task))
    result = c.fetchone()
    conn.close()

    if result:
        start_time, stop_time = result
        if start_time and stop_time:
            return f"Завершена\nНачало: {start_time}\nЗавершение: {stop_time}"
        elif start_time:
            return f"Начата\nНачало: {start_time}"
        else:
            return "Назначена"
    else:
        return "Назначена"


# Обработчик команды /start
@dp.message_handler(Command("start"))
async def start_command(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(
        types.KeyboardButton("/add_employee"),
        types.KeyboardButton("/remove_employee"),
        types.KeyboardButton("/assign_task"),
        types.KeyboardButton("/start_execution"),
        types.KeyboardButton("/stop_execution"),
        types.KeyboardButton("/tasks")
    )
    await message.reply("Привет! Я бот компании. Чем могу помочь?", reply_markup=keyboard)

# Обработчик команды /add_employee
@dp.message_handler(Command("add_employee"))
async def add_employee_command(message: types.Message):
    await message.reply("Введите имя нового сотрудника:")
    await ConversationStates.ADD_EMPLOYEE.set()

# Обработчик состояния ADD_EMPLOYEE
@dp.message_handler(state=ConversationStates.ADD_EMPLOYEE)
async def add_employee_state(message: types.Message, state: FSMContext):
    conn = connect_db()
    c = conn.cursor()
    name = message.text
    c.execute("INSERT INTO employees (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()
    await message.reply('Сотрудник успешно добавлен!')
    await state.finish()

# Обработчик команды /remove_employee
@dp.message_handler(Command("remove_employee"))
async def remove_employee_command(message: types.Message):
    await message.reply("Введите имя сотрудника, которого нужно удалить:")
    await ConversationStates.REMOVE_EMPLOYEE.set()

# Обработчик состояния REMOVE_EMPLOYEE
@dp.message_handler(state=ConversationStates.REMOVE_EMPLOYEE)
async def remove_employee_state(message: types.Message, state: FSMContext):
    conn = connect_db()
    c = conn.cursor()
    name = message.text
    c.execute("DELETE FROM employees WHERE name=?", (name,))
    conn.commit()
    conn.close()
    await message.reply('Сотрудник успешно удален!')
    await state.finish()

# Обработчик команды /assign_task
@dp.message_handler(Command("assign_task"))
async def assign_task_command(message: types.Message):
    await message.reply("Введите имя сотрудника, которому нужно назначить задачу:")
    await ConversationStates.ASSIGN_TASK.set()

# Обработчик состояния ASSIGN_TASK
@dp.message_handler(state=ConversationStates.ASSIGN_TASK)
async def assign_task_state(message: types.Message, state: FSMContext):
    conn = connect_db()
    c = conn.cursor()
    employee_name = message.text
    c.execute("SELECT id FROM employees WHERE name=?", (employee_name,))
    result = c.fetchone()
    if result is not None:
        employee_id = result[0]
        await message.reply('Введите название задачи:')
        await ConversationStates.ASSIGN_TASK_NEXT.set()
        await state.update_data(employee_id=employee_id, employee_name=employee_name)
    else:
        await message.reply('Сотрудник с таким именем не найден.')
        await state.finish()

# Обработчик состояния ASSIGN_TASK_NEXT
@dp.message_handler(state=ConversationStates.ASSIGN_TASK_NEXT)
async def assign_task_next_state(message: types.Message, state: FSMContext):
    conn = connect_db()
    c = conn.cursor()
    task = message.text
    data = await state.get_data()
    employee_id = data['employee_id']
    employee_name = data['employee_name']
    assigned_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Получаем текущее время
    c.execute("INSERT INTO tasks (employee_id, task, assigned_time) VALUES (?, ?, ?)", (employee_id, task, assigned_time))
    conn.commit()

    await message.reply(f"Задача '{task}' успешно назначена сотруднику {employee_name} в {assigned_time}!")
    await state.finish()

# Обработчик команды /start_execution
@dp.message_handler(Command("start_execution"))
async def start_execution_command(message: types.Message):
    names = get_employee_names()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for name in names:
        keyboard.add(types.KeyboardButton(name))
    await message.reply("Выберите сотрудника для выполнения задачи:", reply_markup=keyboard)
    await ConversationStates.SELECT_EMPLOYEE_TASK.set()

# Обработчик состояния SELECT_EMPLOYEE_TASK
@dp.message_handler(state=ConversationStates.SELECT_EMPLOYEE_TASK)
async def select_employee_task_state(message: types.Message, state: FSMContext):
    employee_name = message.text
    tasks = get_employee_tasks(employee_name)
    if tasks:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for task in tasks:
            keyboard.add(types.KeyboardButton(task))
        await message.reply("Выберите задачу для начала выполнения:", reply_markup=keyboard)
        await ConversationStates.START_TASK_EXECUTION.set()
        await state.update_data(employee_name=employee_name)
    else:
        await message.reply("У выбранного сотрудника нет назначенных задач.")
        await state.finish()

# Обработчик состояния START_TASK_EXECUTION
@dp.message_handler(state=ConversationStates.START_TASK_EXECUTION)
async def start_task_execution_state(message: types.Message, state: FSMContext):
    task = message.text
    data = await state.get_data()
    employee_name = data['employee_name']
    # Здесь можно добавить логику для начала выполнения задачи
    # Получаем текущее время
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Получаем текущее время
    # Записываем время остановки выполнения задачи в базу данных
    conn = connect_db()
    c = conn.cursor()
    c.execute(
        "UPDATE tasks SET start_time = ? WHERE task = ? AND employee_id IN (SELECT id FROM employees WHERE name = ?)",
        (start_time, task, employee_name))
    conn.commit()
    conn.close()

    await message.reply(f"Вы начали выполнение задачи '{task}' у сотрудника {employee_name} в {start_time}!")

    # Возвращаем панель кнопок к первоначальной
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("/add_employee"), types.KeyboardButton("/remove_employee"))
    keyboard.add(types.KeyboardButton("/assign_task"), types.KeyboardButton("/start_execution"))
    keyboard.add(types.KeyboardButton("/stop_execution"), types.KeyboardButton("/tasks"))
    await message.reply("Привет! Я бот компании. Чем могу помочь?", reply_markup=keyboard)

    await state.finish()

# Обработчик команды /stop_execution
@dp.message_handler(Command("stop_execution"))
async def stop_execution_command(message: types.Message):
    names = get_employee_names()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for name in names:
        keyboard.add(types.KeyboardButton(name))
    await message.reply("Выберите сотрудника, у которого нужно остановить задачу:", reply_markup=keyboard)
    await ConversationStates.STOP_TASK_EXECUTION.set()

# Обработчик состояния STOP_TASK_EXECUTION для команды /stop_execution
@dp.message_handler(state=ConversationStates.STOP_TASK_EXECUTION)
async def stop_execution_state(message: types.Message, state: FSMContext):
    employee_name = message.text
    tasks = get_employee_tasks(employee_name)
    if tasks:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for task in tasks:
            keyboard.add(types.KeyboardButton(task))
        await message.reply("Выберите задачу, которую нужно остановить:", reply_markup=keyboard)
        await ConversationStates.STOP_TASK_EXECUTION_NEXT.set()
        await state.update_data(employee_name=employee_name)
    else:
        await message.reply("У выбранного сотрудника нет назначенных задач.")
        await state.finish()

# Обработчик состояния STOP_TASK_EXECUTION_NEXT для команды /stop_execution
@dp.message_handler(state=ConversationStates.STOP_TASK_EXECUTION_NEXT)
async def stop_execution_next_state(message: types.Message, state: FSMContext):
    task = message.text
    data = await state.get_data()
    employee_name = data['employee_name']
    # Здесь можно добавить логику для остановки выполнения задачи
    stop_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Получаем текущее время
    # Записываем время остановки выполнения задачи в базу данных
    conn = connect_db()
    c = conn.cursor()
    c.execute(
        "UPDATE tasks SET stop_time = ? WHERE task = ? AND employee_id IN (SELECT id FROM employees WHERE name = ?)",
        (stop_time, task, employee_name))
    conn.commit()
    conn.close()

    await message.reply(f"Вы остановили выполнение задачи '{task}' у сотрудника {employee_name} в {stop_time}!")

    # Возвращаем панель кнопок к первоначальной
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("/add_employee"), types.KeyboardButton("/remove_employee"))
    keyboard.add(types.KeyboardButton("/assign_task"), types.KeyboardButton("/start_execution"))
    keyboard.add(types.KeyboardButton("/stop_execution"), types.KeyboardButton("/tasks"))
    await message.reply("Привет! Я бот компании. Чем могу помочь?", reply_markup=keyboard)

    await state.finish()

# Запуск бота
if __name__ == '__main__':
    create_employees_table()
    create_tasks_table()
    executor.start_polling(dp, skip_updates=True)
