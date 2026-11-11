"""SecureCart v1 backend (FastAPI + raw sqlite3).

Run with:  python app.py   (binds to 127.0.0.1:8000 only)
"""
import traceback
from datetime import datetime

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from auth import create_token, get_current_user, hash_password, verify_password
from database import get_db, init_db

app = FastAPI(title="SecureCart API")

# ------------------------------------------------------------------- CORS
# VULN-10: CORS allows every origin (CWE-942)
# VULN-11: no security headers are set anywhere (no CSP, X-Frame-Options,
#          X-Content-Type-Options, HSTS, ...) (CWE-693)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------------- error handling
# VULN-09: verbose errors leak stack traces and internal details (CWE-209)
@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "type": type(exc).__name__,
            "path": request.url.path,
            "trace": traceback.format_exc(),
        },
    )


# ------------------------------------------------------------------ models
class RegisterBody(BaseModel):
    username: str
    email: str
    password: str


class LoginBody(BaseModel):
    username: str
    password: str


class ReviewBody(BaseModel):
    rating: int
    review_text: str


class CartBody(BaseModel):
    product_id: int
    quantity: int = 1


class CheckoutBody(BaseModel):
    card_name: str
    card_number: str  # MOCK payment: use a dummy number, never a real one
    expiry: str


class ProductBody(BaseModel):
    name: str
    description: str = ""
    price: float
    stock: int = 0


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# -------------------------------------------------------------------- auth
@app.post("/api/register")
def register(body: RegisterBody):
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, 'user')",
            (body.username, body.email, hash_password(body.password)),
        )
        conn.commit()
    except Exception:
        conn.close()
        raise HTTPException(status_code=400, detail="Username or email already taken")
    user_id = cur.lastrowid
    conn.close()
    return {"id": user_id, "username": body.username, "role": "user"}


# VULN-04: no rate limiting, throttling or account lockout on login (CWE-307)
@app.post("/api/login")
def login(body: LoginBody):
    conn = get_db()
    row = conn.execute(
        "SELECT id, username, password, role FROM users WHERE username = ?",
        (body.username,),
    ).fetchone()
    conn.close()
    if row is None or not verify_password(body.password, row["password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_token(row["id"], row["username"], row["role"])
    return {"token": token, "username": row["username"], "role": row["role"]}


# ---------------------------------------------------------------- products
@app.get("/api/products")
def list_products():
    conn = get_db()
    rows = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/products/search")
def search_products(q: str = ""):
    # VULN-01 FIXED: parameterized query - user input is bound as data, never
    # concatenated into SQL text, so it can't change the query's structure (CWE-89).
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, description, price, stock FROM products WHERE name LIKE ?",
        (f"%{q}%",),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/products/{product_id}")
def product_detail(product_id: int):
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")
    reviews = conn.execute(
        "SELECT id, username, rating, review_text, created_at FROM reviews "
        "WHERE product_id = ? ORDER BY id DESC",
        (product_id,),
    ).fetchall()
    conn.close()
    result = dict(product)
    result["reviews"] = [dict(r) for r in reviews]
    return result


@app.post("/api/products/{product_id}/reviews")
def add_review(product_id: int, body: ReviewBody, user: dict = Depends(get_current_user)):
    conn = get_db()
    if conn.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")
    # VULN-07: review text stored exactly as submitted, no sanitization (CWE-79)
    text = body.review_text
    conn.execute(
        "INSERT INTO reviews (product_id, user_id, username, rating, review_text, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (product_id, user["id"], user["username"], body.rating, text, now()),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


# -------------------------------------------------------------------- cart
@app.get("/api/cart")
def get_cart(user: dict = Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute(
        "SELECT c.id, c.product_id, c.quantity, p.name, p.price "
        "FROM cart_items c JOIN products p ON p.id = c.product_id "
        "WHERE c.user_id = ? ORDER BY c.id",
        (user["id"],),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/cart")
def add_to_cart(body: CartBody, user: dict = Depends(get_current_user)):
    if body.quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be at least 1")
    conn = get_db()
    if conn.execute("SELECT id FROM products WHERE id = ?", (body.product_id,)).fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")
    existing = conn.execute(
        "SELECT id FROM cart_items WHERE user_id = ? AND product_id = ?",
        (user["id"], body.product_id),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE cart_items SET quantity = quantity + ? WHERE id = ?",
            (body.quantity, existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?, ?, ?)",
            (user["id"], body.product_id, body.quantity),
        )
    conn.commit()
    conn.close()
    return {"ok": True}


@app.delete("/api/cart/{item_id}")
def remove_from_cart(item_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    conn.execute("DELETE FROM cart_items WHERE id = ? AND user_id = ?", (item_id, user["id"]))
    conn.commit()
    conn.close()
    return {"ok": True}


# ---------------------------------------------------------------- checkout
@app.post("/api/checkout")
def checkout(body: CheckoutBody, user: dict = Depends(get_current_user)):
    """MOCK payment: nothing is charged. Only the last 4 digits are stored."""
    digits = "".join(ch for ch in body.card_number if ch.isdigit())
    if len(digits) < 4:
        raise HTTPException(status_code=400, detail="Enter a (dummy) card number")

    conn = get_db()
    items = conn.execute(
        "SELECT c.product_id, c.quantity, p.name, p.price "
        "FROM cart_items c JOIN products p ON p.id = c.product_id WHERE c.user_id = ?",
        (user["id"],),
    ).fetchall()
    if not items:
        conn.close()
        raise HTTPException(status_code=400, detail="Cart is empty")

    total = round(sum(i["price"] * i["quantity"] for i in items), 2)
    cur = conn.execute(
        "INSERT INTO orders (user_id, total, status, card_last4, created_at) "
        "VALUES (?, ?, 'paid', ?, ?)",
        (user["id"], total, digits[-4:], now()),
    )
    order_id = cur.lastrowid
    for i in items:
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, product_name, quantity, price) "
            "VALUES (?, ?, ?, ?, ?)",
            (order_id, i["product_id"], i["name"], i["quantity"], i["price"]),
        )
        conn.execute(
            "UPDATE products SET stock = MAX(stock - ?, 0) WHERE id = ?",
            (i["quantity"], i["product_id"]),
        )
    conn.execute("DELETE FROM cart_items WHERE user_id = ?", (user["id"],))
    conn.commit()
    conn.close()
    return {"order_id": order_id, "total": total, "status": "paid"}


# ------------------------------------------------------------------ orders
@app.get("/api/orders")
def order_history(user: dict = Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute(
        "SELECT id, total, status, created_at FROM orders WHERE user_id = ? ORDER BY id DESC",
        (user["id"],),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/orders/{order_id}")
def order_detail(order_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    # VULN-02: IDOR - any logged-in user can read any order; the order's owner
    # (order["user_id"]) is never compared with the caller (CWE-639)
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if order is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")
    items = conn.execute(
        "SELECT product_id, product_name, quantity, price FROM order_items WHERE order_id = ?",
        (order_id,),
    ).fetchall()
    conn.close()
    result = dict(order)
    result["items"] = [dict(i) for i in items]
    return result


# ------------------------------------------------------------------- admin
# VULN-08: these endpoints only require a valid login (get_current_user), not
# the admin role, so any registered user can add/edit/delete products (CWE-862)
@app.post("/api/admin/products")
def admin_add_product(body: ProductBody, user: dict = Depends(get_current_user)):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO products (name, description, price, stock) VALUES (?, ?, ?, ?)",
        (body.name, body.description, body.price, body.stock),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"id": new_id}


@app.put("/api/admin/products/{product_id}")
def admin_edit_product(product_id: int, body: ProductBody, user: dict = Depends(get_current_user)):
    conn = get_db()
    conn.execute(
        "UPDATE products SET name = ?, description = ?, price = ?, stock = ? WHERE id = ?",
        (body.name, body.description, body.price, body.stock, product_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@app.delete("/api/admin/products/{product_id}")
def admin_delete_product(product_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


init_db()

if __name__ == "__main__":
    # Bound to loopback only: this app is intentionally vulnerable.
    uvicorn.run(app, host="127.0.0.1", port=8000)
