import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from dotenv import load_dotenv
import os
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import (
    init_db,
    add_habit,
    get_habits,
    mark_done,
    get_today_completions,
    get_streak,
    delete_habit,
    get_all_users,
    init_user_settings,
    get_user_settings,
    update_reminder,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio
from datetime import datetime

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class AddHabit(StatesGroup):
    waiting_for_name = State()


class SetReminder(StatesGroup):
    waiting_for_hour = State()


class OnBoarding(StatesGroup):
    waiting_reminder_choice = State()
    waiting_reminder_hour = State()


def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Добавить", callback_data="menu_add"),
                InlineKeyboardButton(text="✅ Отметить", callback_data="menu_done"),
            ],
            [
                InlineKeyboardButton(text="📊 Прогресс", callback_data="menu_progress"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data="menu_delete"),
            ],
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu_settings"),
            ],
        ]
    )


@dp.callback_query(F.data == "menu_delete")
async def menu_delete(callback: CallbackQuery):
    await callback.message.delete()
    habits = get_habits(callback.from_user.id)
    if not habits:
        await callback.message.answer(
            "У тебя пока нет привычек.", reply_markup=main_menu()
        )
        await callback.answer()
        return

    buttons = []
    for habit in habits:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🗑 {habit[1]}", callback_data=f"delete_{habit[0]}"
                )
            ]
        )
    buttons.append(
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_home")]
    )

    await callback.message.answer(
        "Выбери привычку для удаления:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("delete_"))
async def process_delete(callback: CallbackQuery):
    habit_id = int(callback.data.split("_")[1])
    delete_habit(habit_id)
    await callback.answer("Удалено!")

    habits = get_habits(callback.from_user.id)
    if not habits:
        await callback.message.delete()
        await callback.message.answer("Все привычки удалены.", reply_markup=main_menu())
        return

    buttons = []
    for habit in habits:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🗑 {habit[1]}", callback_data=f"delete_{habit[0]}"
                )
            ]
        )
    buttons.append(
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_home")]
    )

    await callback.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    print(f"START вызван от {message.from_user.id}")
    await state.clear()
    init_user_settings(message.from_user.id)
    await message.answer(
        "👋 Привет!\n\n"
        "Я помогу тебе отслеживать привычки "
        "и держать дисциплину каждый день.\n\n"
        "Хочешь настроить ежедневное напоминание?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Да, настроить", callback_data="onboard_yes"
                    ),
                    InlineKeyboardButton(text="❌ Нет", callback_data="onboard_no"),
                ]
            ]
        ),
    )


@dp.callback_query(F.data == "onboard_yes")
async def onboard_yes(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    msg = await callback.message.answer(
        "В какое время напомнить?\n\nВведи час от 0 до 23\nНапример: *20* — напомню в 20:00",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="onboard_cancel")]
            ]
        ),
    )
    await state.set_state(OnBoarding.waiting_reminder_hour)
    await state.update_data(prompt_msg_id=msg.message_id)
    await callback.answer()


@dp.callback_query(F.data == "onboard_cancel")
async def onboard_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("Выбери действие 👇", reply_markup=main_menu())
    await callback.answer()


@dp.message(OnBoarding.waiting_reminder_hour)
async def onboard_hour_received(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        hour = int(message.text)
        if not 0 <= hour <= 23:
            raise ValueError
    except ValueError:
        await message.answer("Введи число от 0 до 23")
        return

    update_reminder(message.from_user.id, enabled=1, hour=hour)
    await state.clear()
    await message.delete()
    try:
        await bot.delete_message(message.chat.id, data["prompt_msg_id"])
    except:
        pass
    await message.answer(
        f"✅ Напоминание установлено на *{hour}:00*\n\nТеперь выбери действие 👇",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )


@dp.callback_query(F.data == "onboard_no")
async def onboard_no(callback: CallbackQuery):
    update_reminder(callback.from_user.id, enabled=0)
    await callback.message.delete()
    await callback.message.answer(
        "Хорошо, напоминания выключены.\n\nВыбери действие 👇", reply_markup=main_menu()
    )
    await callback.answer()


@dp.callback_query(F.data == "menu_add")
async def menu_add(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    msg = await callback.message.answer("Напиши название привычки:")
    await state.set_state(AddHabit.waiting_for_name)
    await state.update_data(prompt_msg_id=msg.message_id)
    await callback.answer()


@dp.message(AddHabit.waiting_for_name)
async def habit_name_received(message: Message, state: FSMContext):
    data = await state.get_data()
    add_habit(message.from_user.id, message.text)
    await state.clear()
    await message.delete()
    try:
        await bot.delete_message(message.chat.id, data["prompt_msg_id"])
    except:
        pass
    await message.answer(
        f"✅ Привычка *{message.text}* добавлена!",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )


@dp.callback_query(F.data == "menu_done")
async def menu_done(callback: CallbackQuery):
    await callback.message.delete()
    habits = get_habits(callback.from_user.id)
    if not habits:
        await callback.message.answer(
            "У тебя пока нет привычек.", reply_markup=main_menu()
        )
        await callback.answer()
        return
    done_today = get_today_completions(callback.from_user.id)
    buttons = []
    for habit in habits:
        status = "✅" if habit[0] in done_today else "⬜"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{status} {habit[1]}", callback_data=f"done_{habit[0]}"
                )
            ]
        )
    buttons.append(
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_home")]
    )
    await callback.message.answer(
        "Отметь выполненные привычки 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("done_"))
async def process_done(callback: CallbackQuery):
    habit_id = int(callback.data.split("_")[1])
    mark_done(habit_id)
    await callback.answer("Отмечено! 🔥")
    habits = get_habits(callback.from_user.id)
    done_today = get_today_completions(callback.from_user.id)
    buttons = []
    for habit in habits:
        status = "✅" if habit[0] in done_today else "⬜"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{status} {habit[1]}", callback_data=f"done_{habit[0]}"
                )
            ]
        )
    buttons.append(
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_home")]
    )
    await callback.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@dp.callback_query(F.data == "menu_progress")
async def menu_progress(callback: CallbackQuery):
    await callback.message.delete()
    habits = get_habits(callback.from_user.id)
    if not habits:
        await callback.message.answer(
            "У тебя пока нет привычек.", reply_markup=main_menu()
        )
        await callback.answer()
        return

    done_today = get_today_completions(callback.from_user.id)
    done_count = len([h for h in habits if h[0] in done_today])

    text = "📊 *Твои привычки сегодня:*\n\n"

    for habit in habits:
        streak = get_streak(habit[0])
        status = "✅" if habit[0] in done_today else "⬜"

        filled = min(streak, 7)
        bar = "█" * filled + "░" * (7 - filled)

        fire = f" 🔥 {streak}" if streak > 0 else ""
        text += f"{status} *{habit[1]}*{fire}\n"
        text += f"`{bar}`\n\n"

    text += f"Выполнено сегодня: *{done_count}/{len(habits)}*"

    await callback.message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🏠 Главное меню", callback_data="menu_home"
                    )
                ]
            ]
        ),
    )
    await callback.answer()


@dp.callback_query(F.data == "menu_home")
async def menu_home(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        "👋 Главное меню\n\nВыбери действие 👇", reply_markup=main_menu()
    )
    await callback.answer()


async def send_daily_reminder():
    while True:
        now = datetime.now()
        users = get_all_users()
        for user_id in users:
            enabled, hour = get_user_settings(user_id)
            if not enabled:
                continue
            if now.hour == hour and now.minute == 0:
                habits = get_habits(user_id)
                done_today = get_today_completions(user_id)
                remaining = [h for h in habits if h[0] not in done_today]
                if not habits:
                    text = "⏰ *Напоминание!*\n\nУ вас пока нет привычек. Добавьте их через меню."
                    try:
                        await bot.send_message(user_id, text, parse_mode="Markdown")
                    except:
                        pass
                elif remaining:
                    text = "⏰ *Напоминание!*\n\nЕщё не отмечено сегодня:\n\n"
                    for h in remaining:
                        text += f"⬜ {h[1]}\n"
                    try:
                        await bot.send_message(
                            user_id,
                            text,
                            parse_mode="Markdown",
                            reply_markup=InlineKeyboardMarkup(
                                inline_keyboard=[
                                    [
                                        InlineKeyboardButton(
                                            text="✅ Отметить",
                                            callback_data="menu_done",
                                        )
                                    ]
                                ]
                            ),
                        )
                    except:
                        pass
        await asyncio.sleep(30)


@dp.callback_query(F.data == "menu_settings")
async def menu_settings(callback: CallbackQuery):
    print(f"SETTINGS вызван от {callback.from_user.id}")
    await callback.message.delete()
    enabled, hour = get_user_settings(callback.from_user.id)
    status = "включено ✅" if enabled else "выключено ❌"

    buttons = [
        [
            InlineKeyboardButton(
                text=f"🔔 Напоминание: {status}", callback_data="toggle_reminder"
            )
        ],
        [
            InlineKeyboardButton(text="🌅 9:00", callback_data="remind_9"),
            InlineKeyboardButton(text="☀️ 14:00", callback_data="remind_14"),
        ],
        [
            InlineKeyboardButton(text="🌆 19:00", callback_data="remind_19"),
            InlineKeyboardButton(text="🌙 21:00", callback_data="remind_21"),
        ],
        [InlineKeyboardButton(text="✏️ Своё время", callback_data="remind_custom")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_home")],
    ]

    await callback.message.answer(
        f"⚙️ *Настройки*\n\nНапоминание: *{status}*\nВремя: *{hour}:00*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@dp.callback_query(F.data == "toggle_reminder")
async def toggle_reminder(callback: CallbackQuery):
    enabled, hour = get_user_settings(callback.from_user.id)
    new_enabled = 0 if enabled else 1
    update_reminder(callback.from_user.id, enabled=new_enabled)
    await callback.answer("Обновлено!")

    status = "включено ✅" if new_enabled else "выключено ❌"
    buttons = [
        [
            InlineKeyboardButton(
                text=f"🔔 Напоминание: {status}", callback_data="toggle_reminder"
            )
        ],
        [
            InlineKeyboardButton(text="🌅 9:00", callback_data="remind_9"),
            InlineKeyboardButton(text="☀️ 14:00", callback_data="remind_14"),
        ],
        [
            InlineKeyboardButton(text="🌆 19:00", callback_data="remind_19"),
            InlineKeyboardButton(text="🌙 21:00", callback_data="remind_21"),
        ],
        [InlineKeyboardButton(text="✏️ Своё время", callback_data="remind_custom")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_home")],
    ]

    await callback.message.edit_text(
        f"⚙️ *Настройки*\n\nНапоминание: *{status}*\nВремя: *{hour}:00*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@dp.callback_query(F.data.startswith("remind_") & ~F.data.endswith("custom"))
async def set_reminder_time(callback: CallbackQuery):
    hour = int(callback.data.split("_")[1])
    update_reminder(callback.from_user.id, hour=hour)
    enabled, _ = get_user_settings(callback.from_user.id)
    status = "включено ✅" if enabled else "выключено ❌"
    await callback.answer(f"Установлено на {hour}:00!")

    buttons = [
        [
            InlineKeyboardButton(
                text=f"🔔 Напоминание: {status}", callback_data="toggle_reminder"
            )
        ],
        [
            InlineKeyboardButton(text="🌅 9:00", callback_data="remind_9"),
            InlineKeyboardButton(text="☀️ 14:00", callback_data="remind_14"),
        ],
        [
            InlineKeyboardButton(text="🌆 19:00", callback_data="remind_19"),
            InlineKeyboardButton(text="🌙 21:00", callback_data="remind_21"),
        ],
        [InlineKeyboardButton(text="✏️ Своё время", callback_data="remind_custom")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_home")],
    ]

    await callback.message.edit_text(
        f"⚙️ *Настройки*\n\nНапоминание: *{status}*\nВремя: *{hour}:00*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@dp.callback_query(F.data == "remind_custom")
async def set_custom_reminder_time(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    msg = await callback.message.answer(
        "Введи час от 0 до 23\nНапример: *20* — напомню в 20:00",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="❌ Отмена", callback_data="settings_cancel"
                    )
                ]
            ]
        ),
    )
    await state.set_state(SetReminder.waiting_for_hour)
    await state.update_data(prompt_msg_id=msg.message_id)
    await callback.answer()


@dp.callback_query(F.data == "settings_cancel")
async def settings_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("Выбери действие 👇", reply_markup=main_menu())
    await callback.answer()


@dp.message(SetReminder.waiting_for_hour)
async def reminder_hour_received(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        hour = int(message.text)
        if not 0 <= hour <= 23:
            raise ValueError
    except ValueError:
        await message.answer("Введи число от 0 до 23")
        return

    update_reminder(message.from_user.id, hour=hour)
    await state.clear()
    await message.delete()
    try:
        await bot.delete_message(message.chat.id, data["prompt_msg_id"])
    except:
        pass
    await message.answer(
        f"✅ Напоминание установлено на *{hour}:00*",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )


async def main():
    init_db()
    asyncio.create_task(send_daily_reminder())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
