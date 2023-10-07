@dp.message(filters.CommandStart())
async def start(message: types.Message):
    await bot.send_message(message.chat.id, "Приветствие")
    # await asyncio.sleep(3)
    await help(message)
    # await asyncio.sleep(3)
    await menu(message)
    
@dp.message(filters.Command("help"))
async def help(message: types.Message):
    await bot.send_message(message.chat.id, "Объяснение \| /help")   
    
@dp.message(filters.Command("menu"))
async def menu(message: types.Message):
    user_id = f"{message.from_user.id}"
    kbuilder = InlineKeyboardBuilder() 
    
    kbuilder.row(InlineKeyboardButton(text="Добавить организацию", callback_data="btn_add_org"))
    
    if user_id in (data := usersdb.data):
        user_orgs = data[user_id]

        for org in user_orgs:
            org_name = list(org.keys())[0]
            org_role = list(org.values())[0]
            kbuilder.button(text= org_name + ' ⚙️' if org_role == "admin" else ''  , callback_data=f"btn_orgs_{org_name}_{org_role}")
        
    kbuilder.row(InlineKeyboardButton(text="Создать огранизацию", callback_data="btn_create_org"))        
    
    img = r"https://images-platform.99static.com//X0F3CDfCL6LcdPsSJNtRXSGn86Q=/108x1101:902x1895/fit-in/500x500/99designs-contests-attachments/126/126736/attachment_126736972"
    await bot.send_photo(message.chat.id, photo=img, caption=f"{message.from_user.full_name}, вот главное меню:", reply_markup=kbuilder.as_markup())         


@dp.callback_query(lambda query: query.data == "btn_menu")
async def menu_query(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    await menu(query.message.reply_to_message)


    
# region add_org_form    
class AddOrg(StatesGroup):
    name = State()

@router.callback_query(lambda query: query.data == "btn_add_org")
async def btn_add_org(query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(query.id)
    await state.set_state(AddOrg.name)
    await bot.send_message(query.message.chat.id, "Введите название организации:")


@router.message(AddOrg.name)
async def add_org(message: types.Message, state: FSMContext):
    query_data = await state.update_data(org_name=message.text)
    await state.clear() 
    dbdata = orgsdb.data
    
    kbuilder = InlineKeyboardBuilder()
    
    if (org_name:= query_data["org_name"]) in dbdata:
        await message.reply("Заявка успешно подана в организацию")
        await menu(message)

        kbuilder.add(InlineKeyboardButton(text="👍", callback_data=f"btn_application_True_{message.from_user.id}-{org_name}"))
        kbuilder.add(InlineKeyboardButton(text="👎", callback_data=f"btn_application_False_{message.from_user.id}-{org_name}"))
        
        for admin in dbdata[org_name]["admins"]:
            await bot.send_message(admin, fr"Новая заявка на вступление в {org_name} от [{message.from_user.full_name}](t.me//{message.from_user.username})", reply_markup=kbuilder.as_markup(), disable_web_page_preview=True)
        
    else:
        kbuilder.adjust(1, 1, 1) 
        kbuilder.add(InlineKeyboardButton(text="Попробовать еще раз", callback_data="btn_add_org"))
        kbuilder.row(InlineKeyboardButton(text="Создать огранизацию", callback_data="btn_create_org"))
        kbuilder.add(InlineKeyboardButton(text="Назад в меню", callback_data="btn_menu"))
        
        await message.reply("Похоже, что такой организации не существует, но вы можете ее создать", reply_markup=kbuilder.as_markup())
        
        
        
        
@dp.callback_query(lambda query: query.data.startswith("btn_application_True_"))
async def btn_application_True(query: types.CallbackQuery):
    string = query.data[21:]
    user_id, username, org_name = string.split("-")
        
    await bot.answer_callback_query(query.id)
    await bot.send_message(int(user_id), f"Ваша заявка на вступление в {org_name} была одобрена администратором")

    dbdata = orgsdb.data
    for admin in dbdata[org_name]["admins"]:
        await bot.send_message(admin, f"{string}", disable_web_page_preview=True, disable_notification=True)
    
    dbdata[org_name]["members"] += [user_id]
    orgsdb.data = dbdata
# endregion    
    
    
# region create_org_form 
class CreateOrg(StatesGroup):
    name = State()

@router.callback_query(lambda query: query.data == "btn_create_org")
async def btn_add_org(query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(query.id)
    await state.set_state(CreateOrg.name)
    await bot.send_message(query.message.chat.id, "Введите название организации:")

@router.message(CreateOrg.name)
async def add_org(message: types.Message, state: FSMContext):
    query_data = await state.update_data(org_name=message.text)
    await state.clear() 
    dbdata = orgsdb.data
    if query_data["org_name"] in dbdata:
        ...
    
    else:
        kbuilder = InlineKeyboardBuilder()
        kbuilder.adjust(1, 1, 1) 
        kbuilder.add(InlineKeyboardButton(text="Попробовать еще раз", callback_data="btn_add_org"))
        kbuilder.row(InlineKeyboardButton(text="Создать огранизацию", callback_data="btn_create_org"))
        kbuilder.add(InlineKeyboardButton(text="Назад в меню", callback_data="btn_menu"))
        await message.reply("Похоже, что такой организации не существует, но вы можете ее создать", reply_markup=kbuilder.as_markup())

# endregion 