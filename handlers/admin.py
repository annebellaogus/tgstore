# ============================================
# ADMIN PANEL HANDLERS
# ============================================
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from config import *
from database import *
import io

# ============== ADMIN CHECK ==============

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS or user_id == OWNER_ID

# ============== ADMIN COMMANDS ==============

async def admin_panel(client: Client, message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.reply_text("❌ <b>Access Denied!</b>")
        return
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Manage Stock", callback_data="admin_stock")],
        [InlineKeyboardButton("📋 Orders", callback_data="admin_orders")],
        [InlineKeyboardButton("💰 Payments", callback_data="admin_payments")],
        [InlineKeyboardButton("👥 Users", callback_data="admin_users")],
        [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")]
    ])
    
    await message.reply_text("🔧 <b>Admin Panel</b>", reply_markup=keyboard)

async def add_stock_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    
    # Format: /addstock category phone session [json] [age] [country]
    args = message.text.split(" ", 5)
    if len(args) < 4:
        await message.reply_text("""
❌ <b>Wrong format!</b>

<b>Usage:</b>
<code>/addstock category phone session_string [json_data] [age_months] [country]</code>

<b>Categories:</b>
   fresh_session, aged_6m, aged_1y, aged_2y, premium_aged

<b>Example:</b>
<code>/addstock fresh_session +1234567890 session_string_here json_data 0 USA</code>
""")
        return
    
    category = args[1]
    phone = args[2]
    session = args[3]
    json_data = args[4] if len(args) > 4 else ""
    age = int(args[5]) if len(args) > 5 else 0
    country = args[6] if len(args) > 6 else "Unknown"
    
    add_stock(category, phone, session, json_data, age, country)
    
    await message.reply_text(f"""
✅ <b>Stock Added!</b>

📦 <b>Category:</b> {CATEGORIES.get(category, category)}
📱 <b>Phone:</b> <code>{phone}</code>
📅 <b>Age:</b> {age} months
🌍 <b>Country:</b> {country}
""")

async def admin_callback_handler(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id):
        await callback.answer("❌ Access Denied!", show_alert=True)
        return
    
    data = callback.data
    
    if data == "admin_stock":
        await show_admin_stock(callback)
    elif data == "admin_orders":
        await show_admin_orders(callback)
    elif data == "admin_payments":
        await show_admin_payments(callback)
    elif data == "admin_users":
        await show_admin_users(callback)
    elif data == "admin_stats":
        await show_admin_stats(callback)
    elif data == "admin_broadcast":
        await start_broadcast(callback)
    elif data.startswith("verify_payment_"):
        payment_id = int(data.replace("verify_payment_", ""))
        await verify_payment_callback(callback, payment_id)
    elif data.startswith("deliver_order_"):
        order_id = data.replace("deliver_order_", "")
        await deliver_order_callback(client, callback, order_id)
    elif data == "back_to_admin":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 Manage Stock", callback_data="admin_stock")],
            [InlineKeyboardButton("📋 Orders", callback_data="admin_orders")],
            [InlineKeyboardButton("💰 Payments", callback_data="admin_payments")],
            [InlineKeyboardButton("👥 Users", callback_data="admin_users")],
            [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")]
        ])
        await callback.message.edit_text("🔧 <b>Admin Panel</b>", reply_markup=keyboard)

async def show_admin_stock(callback: CallbackQuery):
    stock = get_all_stock()
    
    text = "📦 <b>Stock Management</b>\n\n"
    
    for key, name in CATEGORIES.items():
        available = get_stock_count(key)
        total = len([s for s in stock if s['category'] == key])
        text += f"{name}: {available}/{total} available\n"
    
    text += f"\n📊 <b>Total Items:</b> {len(stock)}\n"
    text += f"📊 <b>Available:</b> {len([s for s in stock if s['is_sold'] == 0])}\n"
    text += f"📊 <b>Sold:</b> {len([s for s in stock if s['is_sold'] == 1])}\n\n"
    text += "Use <code>/addstock</code> to add new stock."
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

async def show_admin_orders(callback: CallbackQuery):
    orders = get_all_orders()
    
    text = "📋 <b>All Orders</b>\n\n"
    
    pending = [o for o in orders if o['status'] == 'pending']
    paid = [o for o in orders if o['status'] == 'paid']
    delivered = [o for o in orders if o['status'] == 'delivered']
    
    text += f"⏳ Pending: {len(pending)}\n"
    text += f"💰 Paid (Awaiting Delivery): {len(paid)}\n"
    text += f"✅ Delivered: {len(delivered)}\n"
    text += f"📊 Total: {len(orders)}\n\n"
    
    buttons = []
    for order in paid[:5]:  # Show paid orders for delivery
        text += f"💰 <code>{order['order_id']}</code> - {CATEGORIES.get(order['category'], order['category'])}\n"
        buttons.append([InlineKeyboardButton(f"Deliver {order['order_id']}", callback_data=f"deliver_order_{order['order_id']}")])
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def show_admin_payments(callback: CallbackQuery):
    payments = get_pending_payments()
    
    text = "💰 <b>Pending Payments</b>\n\n"
    
    if not payments:
        text += "✅ No pending payments!"
    else:
        for payment in payments[:10]:
            text += f"""
🆔 <b>Payment ID:</b> {payment['id']}
📋 <b>Order:</b> <code>{payment['order_id']}</code>
👤 <b>User:</b> <code>{payment['user_id']}</code>
💵 <b>Amount:</b> {payment['amount']} {payment['currency']}
📅 <b>Date:</b> {payment['created_at'][:16] if payment['created_at'] else 'N/A'}

"""
    
    buttons = []
    for payment in payments[:5]:
        buttons.append([InlineKeyboardButton(f"✅ Verify Payment #{payment['id']}", 
                                            callback_data=f"verify_payment_{payment['id']}")])
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def verify_payment_callback(callback: CallbackQuery, payment_id: int):
    verify_payment(payment_id, callback.from_user.id)
    
    # Get payment details
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
    payment = cursor.fetchone()
    conn.close()
    
    if payment:
        order_id = payment['order_id']
        update_order_status(order_id, "paid")
        
        # Notify user
        try:
            await callback.message._client.send_message(
                payment['user_id'],
                f"✅ <b>Payment Verified!</b>\n\n"
                f"📋 <b>Order ID:</b> <code>{order_id}</code>\n"
                f"💰 <b>Amount:</b> {payment['amount']} {payment['currency']}\n\n"
                f"🚀 <b>Your order is being prepared for delivery!</b>"
            )
        except:
            pass
    
    await callback.answer("✅ Payment verified!", show_alert=True)
    await show_admin_payments(callback)

async def deliver_order_callback(client: Client, callback: CallbackQuery, order_id: str):
    order = get_order(order_id)
    if not order:
        await callback.answer("❌ Order not found!", show_alert=True)
        return
    
    # Get available stock
    stock = get_available_stock(order['category'])
    if not stock:
        await callback.answer("❌ No stock available for this category!", show_alert=True)
        return
    
    item = stock[0]  # Get first available item
    
    # Deliver
    deliver_order(order_id, item['id'], item['phone_number'], 
                  item['session_string'], item['json_data'])
    update_order_status(order_id, "delivered")
    
    # Update user stats
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users SET total_orders = total_orders + 1, 
        total_spent = total_spent + ? WHERE user_id = ?
    ''', (order['amount'], order['user_id']))
    conn.commit()
    conn.close()
    
    # Send to user
    try:
        await client.send_message(
            order['user_id'],
            f"""
🎉 <b>Order Delivered!</b>

📋 <b>Order ID:</b> <code>{order_id}</code>
📦 <b>Item:</b> {CATEGORIES.get(order['category'], order['category'])}

📱 <b>Phone:</b> <code>{item['phone_number']}</code>
🔑 <b>Session String:</b>
<code>{item['session_string']}</code>

📁 <b>JSON Data:</b>
<code>{item['json_data'][:500] if item['json_data'] else 'N/A'}</code>

✅ <b>Thank you for your purchase!</b>
💬 <b>Support:</b> {SUPPORT_USERNAME}
"""
        )
    except Exception as e:
        await callback.answer(f"⚠️ Delivered but couldn't notify user: {str(e)}", show_alert=True)
        return
    
    await callback.answer("✅ Order delivered successfully!", show_alert=True)
    await show_admin_orders(callback)

async def show_admin_users(callback: CallbackQuery):
    users = get_all_users()
    total = len(users)
    banned = len([u for u in users if u['is_banned']])
    
    text = f"""
👥 <b>Users Management</b>

📊 <b>Total Users:</b> {total}
🚫 <b>Banned:</b> {banned}
✅ <b>Active:</b> {total - banned}

📋 <b>Recent Users:</b>
"""
    
    for user in users[:10]:
        status = "🚫" if user['is_banned'] else "✅"
        text += f"\n{status} <code>{user['user_id']}</code> - @{user['username'] or 'N/A'} ({user['first_name']})"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

async def show_admin_stats(callback: CallbackQuery):
    update_stats()
    stats = get_stats()
    
    total_users = get_user_count()
    total_orders = len(get_all_orders())
    delivered_orders = len([o for o in get_all_orders() if o['status'] == 'delivered'])
    total_revenue = sum([o['amount'] for o in get_all_orders() if o['status'] == 'delivered'])
    
    text = f"""
📊 <b>Bot Statistics</b>

👥 <b>Total Users:</b> {total_users}
📦 <b>Total Orders:</b> {total_orders}
✅ <b>Delivered:</b> {delivered_orders}
💰 <b>Total Revenue:</b> ${total_revenue:.2f}

📦 <b>Stock:</b>
"""
    
    for key, name in CATEGORIES.items():
        stock = get_stock_count(key)
        text += f"   {name}: {stock}\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

async def start_broadcast(callback: CallbackQuery):
    await callback.message.edit_text(
        "📢 <b>Broadcast Message</b>\n\n"
        "Send the message you want to broadcast to all users.\n"
        "Use /cancel to cancel.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")]
        ])
    )
