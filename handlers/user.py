# ============================================
# USER HANDLERS
# ============================================
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from config import *
from database import *
import random

# ============== FORCE JOIN CHECK ==============

async def check_force_join(client: Client, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(FORCE_JOIN_CHANNEL, user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except:
        pass
    return False

def force_join_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{FORCE_JOIN_CHANNEL.replace('@', '')}")],
        [InlineKeyboardButton("💬 Join Group", url=f"https://t.me/{FORCE_JOIN_GROUP.replace('@', '')}")],
        [InlineKeyboardButton("✅ I've Joined", callback_data="check_join")]
    ])

# ============== START COMMAND ==============

async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    first_name = message.from_user.first_name or "User"
    last_name = message.from_user.last_name or ""
    
    # Add user to database
    add_user(user_id, username, first_name, last_name)
    
    # Check force join
    if not await check_force_join(client, user_id):
        await message.reply_text(
            f"👋 <b>Hello {first_name}!</b>\n\n"
            f"🚫 <b>You must join our channel and group to use this bot.</b>\n\n"
            f"📢 <b>Channel:</b> {FORCE_JOIN_CHANNEL}\n"
            f"💬 <b>Group:</b> {FORCE_JOIN_GROUP}\n\n"
            f"👇 <b>Join both and click the button below:</b>",
            reply_markup=force_join_markup()
        )
        return
    
    # Welcome message
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Browse Store", callback_data="browse_store")],
        [InlineKeyboardButton("📦 My Orders", callback_data="my_orders")],
        [InlineKeyboardButton("💰 Prices", callback_data="show_prices")],
        [InlineKeyboardButton("❓ Help / Support", callback_data="help_support")]
    ])
    
    await message.reply_text(WELCOME_MESSAGE, reply_markup=keyboard)

# ============== CALLBACK HANDLERS ==============

async def callback_handler(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data
    
    # Check force join
    if data != "check_join" and not await check_force_join(client, user_id):
        await callback.answer("❌ Please join our channel and group first!", show_alert=True)
        await callback.message.edit_text(
            "🚫 <b>You must join our channel and group to use this bot.</b>\n\n"
            "👇 <b>Join both and click the button below:</b>",
            reply_markup=force_join_markup()
        )
        return
    
    if data == "check_join":
        if await check_force_join(client, user_id):
            await callback.answer("✅ Verified! Welcome!", show_alert=True)
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Browse Store", callback_data="browse_store")],
                [InlineKeyboardButton("📦 My Orders", callback_data="my_orders")],
                [InlineKeyboardButton("💰 Prices", callback_data="show_prices")],
                [InlineKeyboardButton("❓ Help / Support", callback_data="help_support")]
            ])
            await callback.message.edit_text(WELCOME_MESSAGE, reply_markup=keyboard)
        else:
            await callback.answer("❌ You haven't joined yet!", show_alert=True)
    
    elif data == "browse_store":
        await show_store(callback)
    
    elif data == "show_prices":
        await show_prices(callback)
    
    elif data == "my_orders":
        await show_my_orders(client, callback)
    
    elif data == "help_support":
        await show_help(callback)
    
    elif data.startswith("category_"):
        category = data.replace("category_", "")
        await show_category_items(callback, category)
    
    elif data.startswith("buy_"):
        category = data.replace("buy_", "")
        await initiate_purchase(client, callback, category)
    
    elif data.startswith("pay_"):
        parts = data.replace("pay_", "").split("_")
        order_id = parts[0]
        method = parts[1]
        await show_payment_details(callback, order_id, method)
    
    elif data == "back_to_store":
        await show_store(callback)
    
    elif data == "back_to_main":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Browse Store", callback_data="browse_store")],
            [InlineKeyboardButton("📦 My Orders", callback_data="my_orders")],
            [InlineKeyboardButton("💰 Prices", callback_data="show_prices")],
            [InlineKeyboardButton("❓ Help / Support", callback_data="help_support")]
        ])
        await callback.message.edit_text(WELCOME_MESSAGE, reply_markup=keyboard)
    
    elif data.startswith("order_details_"):
        order_id = data.replace("order_details_", "")
        await show_order_details(callback, order_id)

async def show_store(callback: CallbackQuery):
    text = "🛒 <b>Session Store</b>\n\n<b>Select a category:</b>\n\n"
    
    buttons = []
    for key, name in CATEGORIES.items():
        stock_count = get_stock_count(key)
        text += f"{name}: <code>{stock_count}</code> in stock\n"
        buttons.append([InlineKeyboardButton(f"{name} ({stock_count})", callback_data=f"category_{key}")])
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def show_category_items(callback: CallbackQuery, category: str):
    stock_count = get_stock_count(category)
    price_usd = PRICES[category]["usd"]
    price_inr = PRICES[category]["inr"]
    category_name = CATEGORIES[category]
    
    text = f"""
📦 <b>{category_name}</b>

💵 <b>Price:</b> ${price_usd} / ₹{price_inr}
📊 <b>Available:</b> {stock_count} items

✅ <b>Features:</b>
   • Phone Verified Account
   • Session + JSON Format
   • Instant Delivery
   • Replacement Guarantee

🛒 <b>Click Buy Now to purchase!</b>
"""
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Buy Now", callback_data=f"buy_{category}")],
        [InlineKeyboardButton("🔙 Back to Store", callback_data="back_to_store")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

async def show_prices(callback: CallbackQuery):
    text = "💰 <b>Price List</b>\n\n"
    
    for key, name in CATEGORIES.items():
        usd = PRICES[key]["usd"]
        inr = PRICES[key]["inr"]
        stock = get_stock_count(key)
        text += f"{name}\n   💵 ${usd} | ₹{inr}\n   📦 Stock: {stock}\n\n"
    
    text += f"\n💳 <b>Payment Methods:</b>\n"
    for key, method in PAYMENT_METHODS.items():
        if method["enabled"]:
            text += f"   • {method['name']}\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Browse Store", callback_data="browse_store")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

async def initiate_purchase(client: Client, callback: CallbackQuery, category: str):
    user_id = callback.from_user.id
    
    # Check stock
    stock = get_available_stock(category)
    if not stock:
        await callback.answer("❌ Out of stock!", show_alert=True)
        return
    
    price_usd = PRICES[category]["usd"]
    price_inr = PRICES[category]["inr"]
    
    # Create order
    order_id = create_order(user_id, category, price_usd, "USD", "pending")
    
    text = f"""
🛒 <b>Order Created!</b>

📋 <b>Order ID:</b> <code>{order_id}</code>
📦 <b>Item:</b> {CATEGORIES[category]}
💵 <b>Amount:</b> ${price_usd} / ₹{price_inr}

💳 <b>Select Payment Method:</b>
"""
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("₿ Crypto (BTC/USDT)", callback_data=f"pay_{order_id}_crypto")],
        [InlineKeyboardButton("📱 UPI", callback_data=f"pay_{order_id}_upi")],
        [InlineKeyboardButton("❌ Cancel Order", callback_data="back_to_store")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

async def show_payment_details(callback: CallbackQuery, order_id: str, method: str):
    order = get_order(order_id)
    if not order:
        await callback.answer("❌ Order not found!", show_alert=True)
        return
    
    if method == "crypto":
        text = f"""
💳 <b>Crypto Payment</b>

📋 <b>Order ID:</b> <code>{order_id}</code>
💵 <b>Amount:</b> ${order['amount']}

📌 <b>Send payment to:</b>
<code>{PAYMENT_METHODS['crypto']['wallet']}</code>

✅ <b>After payment, send screenshot to admin for verification.</b>

⏳ <b>Order expires in 30 minutes</b>
"""
    else:
        text = f"""
📱 <b>UPI Payment</b>

📋 <b>Order ID:</b> <code>{order_id}</code>
💵 <b>Amount:</b> ₹{PRICES[order['category']]['inr']}

📌 <b>Pay to UPI ID:</b>
<code>{PAYMENT_METHODS['upi']['id']}</code>

✅ <b>After payment, send screenshot to admin for verification.</b>

⏳ <b>Order expires in 30 minutes</b>
"""
    
    # Update order payment method
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET payment_method = ? WHERE order_id = ?", (method, order_id))
    conn.commit()
    conn.close()
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Send Screenshot", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("🔙 Back to Store", callback_data="back_to_store")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

async def show_my_orders(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    orders = get_user_orders(user_id)
    
    if not orders:
        await callback.answer("📭 No orders found!", show_alert=True)
        return
    
    text = "📦 <b>My Orders</b>\n\n"
    
    buttons = []
    for order in orders[:10]:  # Show last 10 orders
        status_emoji = {
            "pending": "⏳",
            "paid": "💰",
            "delivered": "✅",
            "cancelled": "❌"
        }.get(order['status'], "❓")
        
        text += f"{status_emoji} <code>{order['order_id']}</code> - {CATEGORIES.get(order['category'], order['category'])}\n"
        buttons.append([InlineKeyboardButton(f"View {order['order_id']}", callback_data=f"order_details_{order['order_id']}")])
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def show_order_details(callback: CallbackQuery, order_id: str):
    order = get_order(order_id)
    if not order:
        await callback.answer("❌ Order not found!", show_alert=True)
        return
    
    status_emoji = {
        "pending": "⏳ Pending",
        "paid": "💰 Paid - Awaiting Delivery",
        "delivered": "✅ Delivered",
        "cancelled": "❌ Cancelled"
    }.get(order['status'], "❓ Unknown")
    
    text = f"""
📋 <b>Order Details</b>

🆔 <b>Order ID:</b> <code>{order['order_id']}</code>
📦 <b>Item:</b> {CATEGORIES.get(order['category'], order['category'])}
💵 <b>Amount:</b> {order['amount']} {order['currency']}
📊 <b>Status:</b> {status_emoji}
📅 <b>Date:</b> {order['created_at'][:10] if order['created_at'] else 'N/A'}
"""
    
    if order['status'] == 'delivered' and order['phone_number']:
        text += f"""
📱 <b>Phone:</b> <code>{order['phone_number']}</code>
🔑 <b>Session:</b> <code>{order['session_string'][:50]}...</code>

📁 <b>JSON Data saved in database</b>
"""
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Orders", callback_data="my_orders")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

async def show_help(callback: CallbackQuery):
    text = f"""
❓ <b>Help & Support</b>

📌 <b>How to Buy:</b>
   1. Click "Browse Store"
   2. Select category
   3. Click "Buy Now"
   4. Choose payment method
   5. Pay and send screenshot
   6. Wait for admin verification
   7. Receive your session!

📞 <b>Support:</b> {SUPPORT_USERNAME}

📋 <b>Commands:</b>
   /start - Start the bot
   /prices - Show price list
   /orders - My orders
   /support - Contact support
"""
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📞 Contact Support", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
