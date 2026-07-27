from flask import (Blueprint, render_template, redirect, url_for,
                   request, flash, jsonify, current_app, Response, send_file)
from flask_login import login_required, current_user
from functools import wraps
from models import db, Product, ProductImage, Order, OrderItem, User
from config import Config
import os, uuid, json, csv, io, zipfile
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('需要管理員權限', 'danger')
            return redirect(url_for('shop.index'))
        return f(*args, **kwargs)
    return decorated


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def save_image(file):
    """儲存上傳圖片，回傳 filename"""
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(path)
    return filename


# ─── 統計首頁 ───────────────────────────────────────────
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    today = datetime.utcnow().date()
    week_ago = datetime.utcnow() - timedelta(days=7)
    stats = {
        'total_orders':    Order.query.count(),
        'pending_orders':  Order.query.filter_by(status='pending').count(),
        'today_orders':    Order.query.filter(db.func.date(Order.created_at) == today).count(),
        'unpaid_orders':   Order.query.filter_by(is_paid=False, status='pending').count(),
        'total_products':  Product.query.filter_by(status='published').count(),
        'draft_products':  Product.query.filter_by(status='draft').count(),
        'total_members':   User.query.filter_by(role='member').count(),
        'week_orders':     Order.query.filter(Order.created_at >= week_ago).count(),
    }
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(8).all()
    return render_template('admin/dashboard.html', stats=stats, recent_orders=recent_orders)


# ─── 商品管理 ─────────────────────────────────────────────────
@admin_bp.route('/products')
@login_required
@admin_required
def products():
    published = Product.query.filter_by(status='published').order_by(Product.created_at.desc()).all()
    drafts    = Product.query.filter_by(status='draft').order_by(Product.created_at.desc()).all()
    return render_template('admin/products.html', published=published, drafts=drafts,
                           sizes=Config.SIZES)


@admin_bp.route('/products/upload', methods=['POST'])
@login_required
@admin_required
def upload_images():
    """批量上傳圖片 → 每張建立一個草稿商品"""
    files = request.files.getlist('images')
    count = 0
    for file in files:
        if file and allowed_file(file.filename):
            filename = save_image(file)
            product = Product(status='draft')
            db.session.add(product)
            db.session.flush()
            img = ProductImage(product_id=product.id, filename=filename,
                               is_primary=True, order_index=0)
            db.session.add(img)
            count += 1
    db.session.commit()
    flash(f'已上傳 {count} 張圖片，建立 {count} 個草稿商品', 'success')
    return redirect(url_for('admin.products'))


@admin_bp.route('/products/<int:pid>/setup', methods=['POST'])
@login_required
@admin_required
def product_setup(pid):
    """更新草稿商品必填資料，填完可上架"""
    product = Product.query.get_or_404(pid)
    code    = request.form.get('code', '').strip()
    sizes   = request.form.getlist('sizes')
    name    = request.form.get('name', '').strip() or None
    price   = request.form.get('price', '').strip()
    colors  = request.form.get('colors', '').strip() or None
    desc    = request.form.get('description', '').strip() or None
    action  = request.form.get('action', 'save')  # 'save' | 'publish'

    if not code:
        return jsonify({'ok': False, 'msg': '商品編號為必填'}), 400
    if not sizes:
        return jsonify({'ok': False, 'msg': '請至少選擇一個尺寸'}), 400

    # 檢查編號唯一（排除自己）
    dup = Product.query.filter(Product.code == code, Product.id != pid).first()
    if dup:
        return jsonify({'ok': False, 'msg': f'商品編號 {code} 已被使用'}), 400

    product.code        = code
    product.sizes       = sizes
    product.name        = name
    product.colors      = colors
    product.description = desc
    try:
        product.price = float(price) if price else None
    except ValueError:
        product.price = None

    if action == 'publish':
        product.status = 'published'

    db.session.commit()
    return jsonify({'ok': True, 'status': product.status})


@admin_bp.route('/products/<int:pid>/toggle', methods=['POST'])
@login_required
@admin_required
def product_toggle(pid):
    """上架 ↔ 下架"""
    product = Product.query.get_or_404(pid)
    if product.status == 'published':
        product.status = 'draft'
        msg = '已下架'
    else:
        if not product.is_ready:
            return jsonify({'ok': False, 'msg': '請先填寫商品編號和尺寸'}), 400
        product.status = 'published'
        msg = '已上架'
    db.session.commit()
    return jsonify({'ok': True, 'status': product.status, 'msg': msg})


@admin_bp.route('/products/<int:pid>/delete', methods=['POST'])
@login_required
@admin_required
def product_delete(pid):
    product = Product.query.get_or_404(pid)
    # 刪除圖片檔案
    for img in product.images:
        path = os.path.join(current_app.config['UPLOAD_FOLDER'], img.filename)
        if os.path.exists(path):
            os.remove(path)
    db.session.delete(product)
    db.session.commit()
    flash('商品已刪除', 'success')
    return redirect(url_for('admin.products'))


@admin_bp.route('/products/<int:pid>/images', methods=['POST'])
@login_required
@admin_required
def add_images(pid):
    """對已存在的商品追加圖片"""
    product = Product.query.get_or_404(pid)
    files = request.files.getlist('images')
    max_idx = max((i.order_index for i in product.images), default=-1)
    for i, file in enumerate(files):
        if file and allowed_file(file.filename):
            filename = save_image(file)
            img = ProductImage(product_id=pid, filename=filename,
                               is_primary=False, order_index=max_idx + i + 1)
            db.session.add(img)
    db.session.commit()
    flash('圖片已新增', 'success')
    return redirect(url_for('admin.products'))


@admin_bp.route('/products/bulk-toggle', methods=['POST'])
@login_required
@admin_required
def bulk_toggle():
    """批量上/下架"""
    ids    = request.json.get('ids', [])
    action = request.json.get('action', '')  # 'publish' | 'unpublish'
    updated = 0
    for pid in ids:
        p = Product.query.get(pid)
        if not p:
            continue
        if action == 'publish' and p.is_ready:
            p.status = 'published'
            updated += 1
        elif action == 'unpublish':
            p.status = 'draft'
            updated += 1
    db.session.commit()
    return jsonify({'ok': True, 'updated': updated})


@admin_bp.route('/products/export')
@login_required
@admin_required
def export_products():
    """匯出已上架商品及圖片為 ZIP"""
    products = Product.query.filter_by(status='published').order_by(Product.created_at.desc()).all()
    data = []
    
    # 建立 in-memory ZIP 檔案
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in products:
            images = []
            for img in p.images:
                images.append(img.filename)
                # 將圖片寫入 ZIP 中的 images 資料夾
                img_path = os.path.join(current_app.config['UPLOAD_FOLDER'], img.filename)
                if os.path.exists(img_path):
                    zf.write(img_path, f'images/{img.filename}')

            data.append({
                'code': p.code,
                'name': p.name,
                'price': p.price,
                'sizes': p.sizes,
                'colors': p.colors,
                'description': p.description,
                'images': images
            })
        
        # 將 JSON 寫入 ZIP
        json_data = json.dumps({'products': data}, ensure_ascii=False, indent=2)
        zf.writestr('products.json', json_data)
        
    memory_file.seek(0)
    
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'products_export_{datetime.now().strftime("%Y%m%d")}.zip'
    )


@admin_bp.route('/products/import', methods=['POST'])
@login_required
@admin_required
def import_products_zip():
    """匯入商品 ZIP 檔"""
    if 'zip_file' not in request.files:
        flash('沒有選擇檔案', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    file = request.files['zip_file']
    if file.filename == '' or not file.filename.endswith('.zip'):
        flash('請選擇有效的 ZIP 檔案', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    try:
        with zipfile.ZipFile(file, 'r') as zf:
            if 'products.json' not in zf.namelist():
                flash('ZIP 檔案內找不到 products.json', 'danger')
                return redirect(url_for('admin.dashboard'))
            
            json_data = zf.read('products.json')
            data = json.loads(json_data)
            products = data.get('products', [])
            
            imported_count = 0
            skipped_count = 0
            
            upload_dir = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_dir, exist_ok=True)
            
            for p_data in products:
                # 檢查是否已存在相同 code
                existing = Product.query.filter_by(code=p_data['code']).first()
                if existing:
                    skipped_count += 1
                    continue
                
                # 建立新商品
                new_product = Product(
                    code=p_data['code'],
                    name=p_data.get('name', ''),
                    price=p_data.get('price'),
                    sizes=p_data.get('sizes') or [],
                    colors=p_data.get('colors') or '',
                    description=p_data.get('description') or '',
                    status='published'
                )
                db.session.add(new_product)
                db.session.flush() # 取得 ID
                
                # 處理圖片
                images = p_data.get('images', [])
                for idx, img_filename in enumerate(images):
                    zip_img_path = f"images/{img_filename}"
                    if zip_img_path in zf.namelist():
                        img_data = zf.read(zip_img_path)
                        save_path = os.path.join(upload_dir, img_filename)
                        with open(save_path, 'wb') as f:
                            f.write(img_data)
                        
                        pi = ProductImage(
                            product_id=new_product.id,
                            filename=img_filename,
                            is_primary=(idx == 0)
                        )
                        db.session.add(pi)
                        
                imported_count += 1
                
            db.session.commit()
            flash(f'成功匯入 {imported_count} 件商品，略過 {skipped_count} 件已存在的商品。', 'success')
            
    except Exception as e:
        db.session.rollback()
        flash(f'匯入失敗：{str(e)}', 'danger')
        
    return redirect(url_for('admin.dashboard'))



# ─── 訂單管理（含統計） ──────────────────────────────────────
@admin_bp.route('/orders')
@login_required
@admin_required
def orders():
    status_filter = request.args.get('status', '')
    q = Order.query.order_by(Order.created_at.desc())
    if status_filter:
        q = q.filter_by(status=status_filter)
    all_orders = q.all()

    today    = datetime.utcnow().date()
    week_ago = datetime.utcnow() - timedelta(days=7)
    stats = {
        'pending_orders': Order.query.filter_by(status='pending').count(),
        'unpaid_orders':  Order.query.filter_by(is_paid=False, status='pending').count(),
        'today_orders':   Order.query.filter(db.func.date(Order.created_at) == today).count(),
        'week_orders':    Order.query.filter(Order.created_at >= week_ago).count(),
    }
    return render_template('admin/orders.html', orders=all_orders,
                           status_filter=status_filter, stats=stats)


@admin_bp.route('/orders/export')
@login_required
@admin_required
def export_orders():
    """匯出未付款訂單為 CSV（已付款不匯出）"""
    orders = Order.query.filter_by(is_paid=False).order_by(Order.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['訂單編號','日期','會員','狀態','付款','商品','尺寸','顏色','數量','單價','小計','備註'])
    for o in orders:
        user = User.query.get(o.user_id)
        username = user.username if user else '?'
        for item in o.items:
            writer.writerow([
                f'#{o.id}',
                o.created_at.strftime('%Y-%m-%d %H:%M'),
                username,
                o.status_label,
                '已付款' if o.is_paid else '未付款',
                item.product_name or ('#' + item.product_code),
                item.size,
                item.color or '',
                item.quantity,
                item.price_at_order or '',
                (item.price_at_order * item.quantity) if item.price_at_order else '',
                o.note or '',
            ])
    output.seek(0)
    bom = '\ufeff'  # UTF-8 BOM 讓 Excel 正確顯示中文
    return Response(
        bom + output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=orders_{datetime.now().strftime("%Y%m%d")}.csv'}
    )


@admin_bp.route('/orders/<int:oid>/status', methods=['POST'])
@login_required
@admin_required
def order_status(oid):
    order = Order.query.get_or_404(oid)
    new_status = request.form.get('status')
    if new_status in ('pending', 'completed', 'cancelled'):
        order.status = new_status
        db.session.commit()
    return jsonify({'ok': True, 'status': order.status, 'label': order.status_label})



@admin_bp.route('/orders/<int:oid>/paid', methods=['POST'])
@login_required
def order_paid(oid):
    if not (current_user.is_admin or current_user.can_mark_paid):
        return jsonify({'ok': False, 'msg': '無權限'}), 403
    order = Order.query.get_or_404(oid)
    order.is_paid = not order.is_paid
    db.session.commit()
    return jsonify({'ok': True, 'is_paid': order.is_paid})


@admin_bp.route('/orders/clear-paid', methods=['POST'])
@login_required
@admin_required
def clear_paid_orders():
    """刪除所有已付款訂單"""
    deleted = Order.query.filter_by(is_paid=True).delete()
    db.session.commit()
    flash(f'已清除 {deleted} 筆已付款訂單', 'success')
    return redirect(url_for('admin.orders'))


# ─── 使用者管理 ───────────────────────────────────────────────
@admin_bp.route('/users')
@login_required
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users)


@admin_bp.route('/users/create', methods=['POST'])
@login_required
@admin_required
def user_create():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    role     = request.form.get('role', 'member')
    can_paid = 'can_mark_paid' in request.form

    if not username or not password:
        flash('請填寫帳號和密碼', 'warning')
    elif len(password) < 4:
        flash('密碼至少 4 個字元', 'warning')
    elif User.query.filter_by(username=username).first():
        flash(f'帳號「{username}」已存在', 'warning')
    else:
        new_user = User(username=username, role=role, can_mark_paid=can_paid)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash(f'已新增帳號：{username}', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:uid>/edit', methods=['POST'])
@login_required
@admin_required
def user_edit(uid):
    user = User.query.get_or_404(uid)
    if user.id == current_user.id:
        return jsonify({'ok': False, 'msg': '不能修改自己的權限'}), 400
    user.role          = request.form.get('role', user.role)
    user.can_mark_paid = 'can_mark_paid' in request.form
    new_pw = request.form.get('password', '').strip()
    if new_pw:
        user.set_password(new_pw)
    db.session.commit()
    flash(f'{user.username} 已更新', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:uid>/delete', methods=['POST'])
@login_required
@admin_required
def user_delete(uid):
    user = User.query.get_or_404(uid)
    if user.id == current_user.id:
        flash('不能刪除自己', 'warning')
        return redirect(url_for('admin.users'))

    # 先刪除購物車（避免 NOT NULL 違反）
    from models import CartItem
    CartItem.query.filter_by(user_id=uid).delete()

    # 刪除該用戶的所有訂單（含訂單項目，cascade 已設定）
    orders_to_delete = Order.query.filter_by(user_id=uid).all()
    for order in orders_to_delete:
        db.session.delete(order)

    db.session.flush()  # 確保關聯資料先清除

    db.session.delete(user)
    db.session.commit()
    flash(f'{user.username} 已刪除（含其訂單與購物車）', 'success')
    return redirect(url_for('admin.users'))
