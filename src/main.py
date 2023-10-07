import asyncio
import logging
import sys
from os import getenv

from aiogram import Bot, Dispatcher, Router, filters, types, F
from aiogram.enums.parse_mode import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types.inline_keyboard_button import InlineKeyboardButton
from aiogram.types.inline_keyboard_markup import InlineKeyboardMarkup
from aiogram.types.keyboard_button import KeyboardButton
from aiogram.types.reply_keyboard_markup import ReplyKeyboardMarkup
from aiogram.types.reply_keyboard_remove import ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio 


from config import BOT_TOKEN
from jsondb import orgsdb, usersdb
import os 
from excel_opener import excel2dict


bot = Bot(BOT_TOKEN)
dp = Dispatcher() 
router = Router()


@dp.message(filters.CommandStart())
async def start(message: types.Message):
    await bot.send_message(message.chat.id, "Приветствие")
    await help(message)
    
    user_id = f"{message.from_user.id}"
    data = usersdb.data 
    
    if not user_id in data:
        data[user_id] = []
        usersdb.data = data 
        
    await menu(message)
    
@dp.message(filters.Command("help"))
async def help(message: types.Message):
    await bot.send_message(message.chat.id, "Пояснения | /help")

@dp.message(filters.Command("menu"))
async def menu(message: types.Message):
    kbuilder = InlineKeyboardBuilder()
    kbuilder.button(text="Добавить группу", callback_data=f"btn_add_org")

    data = usersdb() 
    user_id = f"{message.from_user.id}"

    if user_id in data:
        for org in data[user_id]:
            kbuilder.button(text=f"{org}", callback_data=f"btn_org_{org}__0")
    
        data_len = len(data[user_id])
        kbuilder.adjust(1, *[5 for _ in range(data_len//5)], data_len % 5 + 1)
    kbuilder.row(InlineKeyboardButton(text="Создать группу", callback_data=f"btn_create_org"))
    await bot.send_message(message.chat.id, f"""\
{message.from_user.full_name}, вот основное меню (/menu):
/start - перезагрузить бота
/help - получить помощь по боту
/addgroup - добавить группу
/newgroup - создать группу""", reply_markup=kbuilder.as_markup())

@dp.callback_query(lambda query: query.data == "menu")
async def menu_query(query: types.CallbackQuery):
    await menu(query.message.reply_to_message)

@dp.callback_query(lambda query: query.data.startswith("btn_org_"))
async def btn_org(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    
    org_name, page = query.data[8:].split("__")
    
    page = int(page)    
    
    kbuilder = InlineKeyboardBuilder()

    categories = list(orgsdb.data[org_name]["menu"].keys())
    
    len_categories = len(categories) / 10
    int_len_categories = int(len_categories)
    if page < 0:
        page += int_len_categories + 1 if len_categories > 1 else 0 
    elif page > int_len_categories:
        page -= int_len_categories + 1 if len_categories > 1 else 0
    
    window = categories[(page)*10:(page+1)*10]
        
    for category in window:
        kbuilder.button(text=category, callback_data=f"btn_orgcategory_{org_name}__{category}__0")
    
    len_window = len(window)
        
    if len_categories > 1:
        kbuilder.button(text="◀️", callback_data=f"btn_org_{org_name}__{page-1}")
    kbuilder.add(InlineKeyboardButton(text="🛒", callback_data=f"btn_orgshopper"), 
                InlineKeyboardButton(text="⚙️", callback_data=f"btn_orgsettings_{org_name}"))
    if len_categories > 1:
        kbuilder.button(text="▶️", callback_data=f"btn_org_{org_name}__{page+1}")
    
    if len_window % 2:
        kbuilder.adjust(*[2 for _ in range(len_window // 2)], 1, 4)
    else: 
        kbuilder.adjust(*[2 for _ in range(len_window // 2)], 4)

    if query.message.text == f"Меню для {org_name}:":
        await bot.edit_message_reply_markup(query.message.chat.id, query.message.message_id, query.inline_message_id, reply_markup=kbuilder.as_markup())
    else:
        await bot.send_message(query.message.chat.id, f"Меню для {org_name}:", reply_markup=kbuilder.as_markup())
        

@dp.callback_query(lambda query: query.data.startswith("btn_orgsettings_"))
async def btn_org_settings(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    
    org_name = query.data[16:]
    user_id = f"{query.from_user.id}"
        
    data = orgsdb.data 
    
    kbulder = InlineKeyboardBuilder()
    
    if user_id in data[org_name]["admins"]:
        kbulder.button(text="Список участников", callback_data=f"btn_orgmembers_{org_name}__0")
        kbulder.button(text="Добавить меню", callback_data=f"btn_orgadd_menu_{org_name}")
        kbulder.button(text="Удалить группу", callback_data=f"btn_orgdelete_{org_name}")
        kbulder.adjust(1, 1, 1)
    if user_id in data[org_name]["members"]:
        kbulder.button(text="Выйти из группы", callback_data=f"btn_orgleave_{org_name}")        
    
    await bot.send_message(query.message.chat.id, f"Настройки {org_name}:", reply_markup=kbulder.as_markup())        



@dp.callback_query(lambda query: query.data.startswith("btn_orgleave_"))
async def btn_orgleave(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    org_name = query.data[13:]
    kbuilder = InlineKeyboardBuilder()
    kbuilder.button(text="Да", callback_data=f"btn_orgleave_true_{org_name}")
    await bot.send_message(query.message.chat.id, "Вы уверены что хотите покинуть эту группу?", reply_markup=kbuilder.as_markup())

   
@dp.callback_query(lambda query: query.data.startswith("btn_orgdelete_"))
async def btn_orgleave(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    org_name = query.data[14:]
    kbuilder = InlineKeyboardBuilder()
    kbuilder.button(text="Да", callback_data=f"btn_orgleave_true_{org_name}")
    await bot.send_message(query.message.chat.id, "Вы уверены что хотите удалить эту группу?", reply_markup=kbuilder.as_markup())
    
    
@router.message(filters.Command("cancel"))
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info("Cancelling state %r", current_state)
    await state.clear()
    await message.answer(
        "Отменено",
        reply_markup=ReplyKeyboardRemove(),
    )
    await menu(message)
    
# region btn_orgadd_menu_form
class ExcelForm(StatesGroup):
    excel_file = State()
    
@router.callback_query(lambda query: query.data.startswith("btn_orgadd_menu_"))
async def btn_orgadd_menu(query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(query.id)
    org_name = query.data[16:]
    await state.update_data(org_name=org_name)
    await state.set_state(ExcelForm.excel_file)
    await bot.send_message(query.message.chat.id, f"Пришлите *.xlsx файл для {org_name}:\nКоманда /cancel для отмены")
    
@router.message(ExcelForm.excel_file)    
async def btn_orgadd_menu_message(message: types.Message, state: FSMContext):
    org_name = (await state.get_data())["org_name"]
    await state.clear() 
    excel_file: types.Document = message.document
    logging.warning(org_name)
    user_id = f"{message.from_user}"
    orgsdb_data = orgsdb.data 
    
    
    file_path = r"files/" + excel_file.file_name
    await bot.download(excel_file, file_path)
    menu_json = excel2dict(file_path)
    os.remove(file_path)
    
    orgsdb_data[org_name]["menu"] = menu_json
    orgsdb.data = orgsdb_data
    
                    
    await menu(message)
# endregion
            
@dp.callback_query(lambda query: query.data.startswith("btn_orgmembers_"))
async def btn_orgmembers(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    
    org_name, page = query.data[15:].split("__")
    
    page = int(page)    
    
    kbuilder = InlineKeyboardBuilder()

    items = orgsdb.data[org_name]["members"]
    
    len_items = len(items) / 10
    int_len_items = int(len_items)
    if page < 0:
        page += int_len_items + 1 if len_items > 0 else 0
    elif page > int_len_items:
        page -= int_len_items + 1 if len_items > 0 else 0

    window = items[(page)*10:(page+1)*10]
        
    for id, item in enumerate(window):
        kbuilder.button(text=item, callback_data=f"btn_orgmember_{org_name}__{id}")
    
    len_window = len(window)
    kbuilder.adjust(*[2 for _ in range(len_window // 2)], len_window % 2 + 1)
    
    if len_items > 1:       
        kbuilder.row(InlineKeyboardButton(text="◀️", callback_data=f"btn_orgmembers_{org_name}__{page-1}"))
    kbuilder.button(text="↩️", callback_data=f"btn_orgsettings_{org_name}")
    if len_items > 1:
        kbuilder.button(text="▶️", callback_data=f"btn_orgmembers_{org_name}__{page+1}")            

        
    if query.message.text == f"Настройки {org_name}:":
        await bot.edit_message_reply_markup(query.message.chat.id, query.message.message_id, query.inline_message_id, reply_markup=kbuilder.as_markup())
    else:
        await bot.send_message(query.message.chat.id, f"Настройки {org_name}:", reply_markup=kbuilder.as_markup())        
        
@dp.callback_query(lambda query: query.data.startswith("btn_orgcategory_"))
async def btn_org(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    
    org_name, category, page = query.data[16:].split("__")
    
    page = int(page)    
    
    kbuilder = InlineKeyboardBuilder()

    items = orgsdb.data[org_name]["menu"][category]
    
    len_items = len(items) / 10
    int_len_items = int(len_items)
    if page < 0:
        page += int_len_items + 1 if len_items > 0 else 0
    elif page > int_len_items:
        page -= int_len_items + 1 if len_items > 0 else 0

    window = items[(page)*10:(page+1)*10]
        
    for id, item in enumerate(window):
        kbuilder.button(text=item, callback_data=f"btn_orgitem_{org_name}__{category}__{id+page}")
    
    len_window = len(window)
    
    if len_items > 1:       
        kbuilder.button(text="◀️", callback_data=f"btn_orgcategory_{org_name}__{category}__{page-1}")
    kbuilder.add(InlineKeyboardButton(text="🛒", callback_data=f"btn_orgshopper_{org_name}"), 
                InlineKeyboardButton(text="↩️", callback_data=f"btn_org_{org_name}__0"))
    if len_items > 1:
        kbuilder.button(text="▶️", callback_data=f"btn_orgcategory_{org_name}__{category}__{page+1}")            

    if len_window % 2:
        kbuilder.adjust(*[2 for _ in range(len_window // 2)], 1, 4)
    else: 
        kbuilder.adjust(*[2 for _ in range(len_window // 2)], 4)
        
    if query.message.text == f"{category}:" or query.message.text == f"Меню для {org_name}:":
        await bot.edit_message_reply_markup(query.message.chat.id, query.message.message_id, query.inline_message_id, reply_markup=kbuilder.as_markup())
    else:
        await bot.send_message(query.message.chat.id, f"{category}:", reply_markup=kbuilder.as_markup())


items_list = []
@dp.callback_query(lambda query: query.data.startswith("btn_orgitem_"))
async def btn_orgitem(query: types.CallbackQuery):
    global items_list 
    
    await bot.answer_callback_query(query.id)
    
    org_name, category, id = query.data[12:].split("__")
    items_list += [orgsdb.data[org_name]["menu"][category][int(id)]]
    
@dp.callback_query(lambda query: query.data.startswith("btn_orgshopper_"))
async def btn_orgitem(query: types.CallbackQuery):
    global items_list 
    
    await bot.answer_callback_query(query.id)
    
    kbuilder = InlineKeyboardBuilder()
    kbuilder.button(text="Отправить заказ в столовую", callback_data="btn_endrequest")
    await bot.send_message(query.message.chat.id, f"Ваша корзина: {', '.join(items_list)}", reply_markup=kbuilder.as_markup())
    
@dp.callback_query(lambda query: query.data == "btn_endrequest")
async def btn_orgitem(query: types.CallbackQuery):
    global items_list 
    items_list.clear() 

    await bot.answer_callback_query(query.id)    

    await bot.send_message(query.message.chat.id, text="Заказ отправлен в столовую. Корзина очищена.")

    await menu(query.message)
    
    
# region btn_create_org_form
class CreateForm(StatesGroup):
    org_name = State()

@router.callback_query(lambda query: query.data == "btn_create_org")
async def btn_create_org(query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(query.id)
    await state.set_state(CreateForm.org_name)
    await bot.send_message(query.message.chat.id, "Введите название организации:\nКоманда /cancel для отмены")

    
@router.message(CreateForm.org_name)    
async def btn_create_org_message(message: types.Message, state: FSMContext):
    org_name = message.text
    await state.clear() 
    user_id = f"{message.from_user.id}"
    
    
    usersdbdata = usersdb.data

    if org_name in orgsdb.data:
        await message.reply("Похоже группа с таким названием уже существует")
    else:
        usersdbdata[user_id] += [org_name] 
        usersdb.data = usersdbdata
        orgsdb.data |= {org_name: {"admins": [user_id], "members": [user_id], "menu": {}}}
        await message.reply("Организация успешно создана!")
        
    await menu(message)
# endregion 

# region btn_add_org_form
class AddFrom(StatesGroup):
    org_name = State()

@router.callback_query(lambda query: query.data == "btn_add_org")
async def btn_create_org(query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(query.id)
    await state.set_state(AddFrom.org_name)
    await bot.send_message(query.message.chat.id, "Введите название организации:\nКомманда /cancel для отмены")
    
@router.message(AddFrom.org_name)    
async def btn_create_org_message(message: types.Message, state: FSMContext):
    org_name = message.text
    await state.clear() 
    user_id = f"{message.from_user.id}"
    db = orgsdb.data
    
    kbuilder = InlineKeyboardBuilder()
    
    if org_name in db:
        
        if user_id in db[org_name]["members"]:
            await message.reply("Вы и так в этой группе")
            await menu(message)
            return
        
        await message.reply("Заявка в группу отправлена!")
        
        kbuilder.button(text="Принять", callback_data=f"btn_create_org_application_true_{org_name}__{message.from_user.id}")
        kbuilder.button(text="Отклонить", callback_data=f"btn_create_org_application_false_{org_name}__{message.from_user.id}")
        
        
        tasks = [menu(message)]
        for admin in db[org_name]["admins"]:
            tasks.append(bot.send_message(int(admin), f"Новая заявка в {org_name} от [{message.from_user.full_name}](t.me//{message.from_user.username})", 
                                          parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True, reply_markup=kbuilder.as_markup()))
        asyncio.gather(*tasks)
        
    else: 
        kbuilder.button(text="Попробовать еще раз", callback_data="btn_add_org")
        kbuilder.row(InlineKeyboardButton(text="Создать группу", callback_data="btn_create_org"), InlineKeyboardButton(text="Меню", callback_data="menu"))
        await message.reply("Похоже такой группы не существует")
    
    await menu(message)    
    
@dp.callback_query(lambda query: query.data.startswith("btn_create_org_application_true_"))
async def btn_create_org_application_true(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    await bot.edit_message_reply_markup(query.message.chat.id, query.message.message_id, query.inline_message_id)
    org_name, user_id = query.data[32:].split("__")
    await bot.send_message(int(user_id), f"Ваша заявка в {org_name} была одобрена")
    
    
    await menu(query.message.reply_to_message)
# endregion 


async def main() -> None:
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())