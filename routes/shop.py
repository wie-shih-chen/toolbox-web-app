from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app
from flask_login import login_required, current_user
from models import db, Product, ProductImage, CartItem, Order, OrderItem
from config import Config
import os, uuid, json
from PIL import Image as PILImage
from datetime import datetime

shop_bp = Blueprint('shop', __name__)


# ─── 首頁：商品列表 ────────────────────────────────────────────
@shop_bp.route('/')
@login_required
def index():
    products = Product.query.filter_by(status='published').order_by(Product.created_at.desc()).all()
    return render_template('shop/index.html', products=products,
                           sizes=Config.SIZES, now=datetime.utcnow())


# ─── 購物車 ───────────────────────────────────────────────────
@shop_bp.route('/cart')
@login_required
def cart():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    return render_template('shop/cart.html', items=items)


@shop_bp.route('/cart/add', methods=['POST'])
@login_required
def cart_add():
    product_id = request.form.get('product_id', type=int)
    size       = request.form.get('size', '').strip()
    color      = request.form.get('color', '').strip() or None
    quantity   = request.form.get('quantity', 1, type=int)

    product = Product.query.get_or_404(product_id)
    if product.status != 'published':
        flash('此商品無法訂購', 'warning')
        return redirect(url_for('shop.index'))
    if size not in product.sizes:
        flash('請選擇有效尺寸', 'warning')
        return redirect(url_for('shop.index'))
    if quantity < 1:
        quantity = 1

    # 同款＋同色已在購物車 → 累加數量
    existing = CartItem.query.filter_by(
        user_id=current_user.id, product_id=product_id, size=size, color=color
    ).first()
    if existing:
        existing.quantity += quantity
    else:
        db.session.add(CartItem(
            user_id=current_user.id,
            product_id=product_id,
            size=size,
            color=color,
            quantity=quantity
        ))
    db.session.commit()
    flash('已加入購物車！', 'success')
    return redirect(url_for('shop.index'))


@shop_bp.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def cart_remove(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        flash('無權限', 'danger')
        return redirect(url_for('shop.cart'))
    db.session.delete(item)
    db.session.commit()
    flash('已移除', 'success')
    return redirect(url_for('shop.cart'))


@shop_bp.route('/cart/clear', methods=['POST'])
@login_required
def cart_clear():
    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('購物車已清空', 'success')
    return redirect(url_for('shop.cart'))


@shop_bp.route('/cart/update', methods=['POST'])
@login_required
def cart_update():
    item_id  = request.form.get('item_id', type=int)
    quantity = request.form.get('quantity', 1, type=int)
    item = CartItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        return jsonify({'ok': False}), 403
    if quantity < 1:
        db.session.delete(item)
    else:
        item.quantity = quantity
    db.session.commit()
    return jsonify({'ok': True})


# ─── 結帳：購物車 → 訂單 ──────────────────────────────────────
@shop_bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('購物車是空的', 'warning')
        return redirect(url_for('shop.cart'))

    note = request.form.get('note', '').strip()
    order = Order(user_id=current_user.id, note=note or None)
    db.session.add(order)
    db.session.flush()  # 取得 order.id

    for ci in cart_items:
        p = ci.product
        oi = OrderItem(
            order_id       = order.id,
            product_id     = p.id if p else None,
            product_code   = p.code if p else '已刪除',
            product_name   = p.name if p else '',
            size           = ci.size,
            color          = ci.color,
            quantity       = ci.quantity,
            price_at_order = p.price if p else None,
        )
        db.session.add(oi)
        db.session.delete(ci)

    db.session.commit()
    flash('訂單已送出！', 'success')
    return redirect(url_for('shop.my_orders'))


# ─── 我的訂單 ───────────────────────────────────────────
@shop_bp.route('/orders')
@login_required
def my_orders():
    orders = (Order.query
              .filter_by(user_id=current_user.id)
              .filter(Order.status != 'cancelled')
              .order_by(Order.created_at.desc())
              .all())
    return render_template('shop/orders.html', orders=orders)


@shop_bp.route('/orders/<int:oid>/cancel', methods=['POST'])
@login_required
def order_cancel(oid):
    order = Order.query.get_or_404(oid)
    if order.user_id != current_user.id:
        return jsonify({'ok': False, 'msg': '無權限'}), 403
    if order.status != 'pending':
        return jsonify({'ok': False, 'msg': '只有「待確認」的訂單可以取消'}), 400

    # 將訂單品項復原回購物車
    for item in order.items:
        if not item.product_id:
            continue
        existing = CartItem.query.filter_by(
            user_id=current_user.id,
            product_id=item.product_id,
            size=item.size,
            color=item.color or None
        ).first()
        if existing:
            existing.quantity += item.quantity
        else:
            db.session.add(CartItem(
                user_id=current_user.id,
                product_id=item.product_id,
                size=item.size,
                color=item.color or None,
                quantity=item.quantity
            ))

    # 直接刪除訂單（不留取消紀錄）
    db.session.delete(order)
    db.session.commit()
    return jsonify({'ok': True, 'redirect': '/cart'})
