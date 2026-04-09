from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from functools import wraps
from . import db
from .models import User, Brand, LauncherType, TVModel, RemoteControl, Tag

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Доступ запрещён', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users)


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        name     = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        role     = request.form.get('role', 'user')
        if role not in ('admin', 'user', 'viewer'):
            role = 'user'

        if not email or not name:
            flash('Заполните email и имя', 'error')
            return render_template('admin/user_form.html', action='create')

        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'error')
            return render_template('admin/user_form.html', action='create')

        user = User(email=email, name=name, role=role)
        if password:
            user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash(f'Пользователь {name} создан', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html', action='create')


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        user.name  = request.form.get('name', '').strip()
        user.email = request.form.get('email', '').strip().lower()
        role = request.form.get('role', 'user')
        user.role  = role if role in ('admin', 'user', 'viewer') else 'user'
        # is_active_user не трогаем — управляется кнопкой 🔒/🔓 в таблице пользователей

        new_password = request.form.get('password', '').strip()
        if new_password:
            user.set_password(new_password)

        db.session.commit()
        flash('Пользователь обновлён', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html', action='edit', user=user)


@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Нельзя деактивировать себя', 'error')
    else:
        user.is_active_user = not user.is_active_user
        db.session.commit()
        status = 'активирован' if user.is_active_user else 'деактивирован'
        flash(f'{user.name} {status}', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Нельзя удалить себя', 'error')
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f'Пользователь {user.name} удалён', 'success')
    return redirect(url_for('admin.users'))


# ──────────────────────────────────────────────
#  Управление брендами
# ──────────────────────────────────────────────

@admin_bp.route('/brands')
@login_required
@admin_required
def brands():
    all_brands = Brand.query.order_by(Brand.name).all()
    return render_template('admin/brands.html', brands=all_brands)


@admin_bp.route('/brands/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_brand():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Введите название бренда', 'error')
            return render_template('admin/brand_form.html', action='create')
        if Brand.query.filter_by(name=name).first():
            flash('Бренд с таким названием уже существует', 'error')
            return render_template('admin/brand_form.html', action='create')
        db.session.add(Brand(name=name))
        db.session.commit()
        flash(f'Бренд «{name}» создан', 'success')
        return redirect(url_for('admin.brands'))
    return render_template('admin/brand_form.html', action='create')


@admin_bp.route('/brands/<int:brand_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_brand(brand_id):
    brand = Brand.query.get_or_404(brand_id)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Введите название бренда', 'error')
            return render_template('admin/brand_form.html', action='edit', brand=brand)
        existing = Brand.query.filter(Brand.name == name, Brand.id != brand_id).first()
        if existing:
            flash('Бренд с таким названием уже существует', 'error')
            return render_template('admin/brand_form.html', action='edit', brand=brand)
        brand.name = name
        db.session.commit()
        flash('Бренд обновлён', 'success')
        return redirect(url_for('admin.brands'))
    return render_template('admin/brand_form.html', action='edit', brand=brand)


@admin_bp.route('/brands/<int:brand_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_brand(brand_id):
    brand = Brand.query.get_or_404(brand_id)
    db.session.delete(brand)
    db.session.commit()
    flash(f'Бренд «{brand.name}» удалён', 'success')
    return redirect(url_for('admin.brands'))


# ──────────────────────────────────────────────
#  Управление лаунчерами
# ──────────────────────────────────────────────

@admin_bp.route('/launchers')
@login_required
@admin_required
def launchers():
    all_launchers = LauncherType.query.order_by(LauncherType.name).all()
    return render_template('admin/launchers.html', launchers=all_launchers)


@admin_bp.route('/launchers/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_launcher():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Введите название лаунчера', 'error')
            return render_template('admin/launcher_form.html', action='create')
        if LauncherType.query.filter_by(name=name).first():
            flash('Лаунчер с таким названием уже существует', 'error')
            return render_template('admin/launcher_form.html', action='create')
        db.session.add(LauncherType(name=name))
        db.session.commit()
        flash(f'Лаунчер «{name}» создан', 'success')
        return redirect(url_for('admin.launchers'))
    return render_template('admin/launcher_form.html', action='create')


@admin_bp.route('/launchers/<int:launcher_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_launcher(launcher_id):
    launcher = LauncherType.query.get_or_404(launcher_id)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Введите название лаунчера', 'error')
            return render_template('admin/launcher_form.html', action='edit', launcher=launcher)
        existing = LauncherType.query.filter(LauncherType.name == name, LauncherType.id != launcher_id).first()
        if existing:
            flash('Лаунчер с таким названием уже существует', 'error')
            return render_template('admin/launcher_form.html', action='edit', launcher=launcher)
        launcher.name = name
        db.session.commit()
        flash('Лаунчер обновлён', 'success')
        return redirect(url_for('admin.launchers'))
    return render_template('admin/launcher_form.html', action='edit', launcher=launcher)


@admin_bp.route('/launchers/<int:launcher_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_launcher(launcher_id):
    launcher = LauncherType.query.get_or_404(launcher_id)
    db.session.delete(launcher)
    db.session.commit()
    flash(f'Лаунчер «{launcher.name}» удалён', 'success')
    return redirect(url_for('admin.launchers'))


# ──────────────────────────────────────────────
#  Управление пультами
# ──────────────────────────────────────────────

@admin_bp.route('/remotes')
@login_required
@admin_required
def remotes():
    all_remotes = RemoteControl.query.order_by(RemoteControl.name).all()
    return render_template('admin/remotes.html', remotes=all_remotes)


@admin_bp.route('/remotes/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_remote():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Введите название пульта', 'error')
            return render_template('admin/remote_form.html', action='create')
        if RemoteControl.query.filter_by(name=name).first():
            flash('Пульт с таким названием уже существует', 'error')
            return render_template('admin/remote_form.html', action='create')
        db.session.add(RemoteControl(name=name))
        db.session.commit()
        flash(f'Пульт «{name}» добавлен', 'success')
        return redirect(url_for('admin.remotes'))
    return render_template('admin/remote_form.html', action='create')


@admin_bp.route('/remotes/<int:remote_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_remote(remote_id):
    remote = RemoteControl.query.get_or_404(remote_id)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Введите название пульта', 'error')
            return render_template('admin/remote_form.html', action='edit', remote=remote)
        existing = RemoteControl.query.filter(RemoteControl.name == name, RemoteControl.id != remote_id).first()
        if existing:
            flash('Пульт с таким названием уже существует', 'error')
            return render_template('admin/remote_form.html', action='edit', remote=remote)
        remote.name = name
        db.session.commit()
        flash('Пульт обновлён', 'success')
        return redirect(url_for('admin.remotes'))
    return render_template('admin/remote_form.html', action='edit', remote=remote)


@admin_bp.route('/remotes/<int:remote_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_remote(remote_id):
    remote = RemoteControl.query.get_or_404(remote_id)
    # Обнуляем FK у всех моделей где был этот пульт
    TVModel.query.filter_by(remote_control_id=remote_id).update({'remote_control_id': None})
    db.session.delete(remote)
    db.session.commit()
    flash(f'Пульт «{remote.name}» удалён', 'success')
    return redirect(url_for('admin.remotes'))


# ──────────────────────────────────────────────
#  Управление тегами
# ──────────────────────────────────────────────

TAG_COLORS = [
    ('#f05a5a', 'Красный'),
    ('#f0b429', 'Жёлтый'),
    ('#34c87a', 'Зелёный'),
    ('#4f8ef0', 'Синий'),
    ('#7c5fe6', 'Фиолетовый'),
    ('#f07850', 'Оранжевый'),
    ('#60c8d8', 'Голубой'),
    ('#9099b8', 'Серый'),
]

@admin_bp.route('/tags')
@login_required
@admin_required
def tags():
    all_tags = Tag.query.order_by(Tag.name).all()
    return render_template('admin/tags.html', tags=all_tags)


@admin_bp.route('/tags/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_tag():
    if request.method == 'POST':
        name  = request.form.get('name', '').strip()
        color = request.form.get('color', '#4f8ef0').strip()
        if not name:
            flash('Введите название тега', 'error')
            return render_template('admin/tag_form.html', action='create', colors=TAG_COLORS)
        if Tag.query.filter_by(name=name).first():
            flash('Тег с таким названием уже существует', 'error')
            return render_template('admin/tag_form.html', action='create', colors=TAG_COLORS)
        db.session.add(Tag(name=name, color=color))
        db.session.commit()
        flash(f'Тег «{name}» создан', 'success')
        return redirect(url_for('admin.tags'))
    return render_template('admin/tag_form.html', action='create', colors=TAG_COLORS)


@admin_bp.route('/tags/<int:tag_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    if request.method == 'POST':
        name  = request.form.get('name', '').strip()
        color = request.form.get('color', tag.color).strip()
        if not name:
            flash('Введите название тега', 'error')
            return render_template('admin/tag_form.html', action='edit', tag=tag, colors=TAG_COLORS)
        existing = Tag.query.filter(Tag.name == name, Tag.id != tag_id).first()
        if existing:
            flash('Тег с таким названием уже существует', 'error')
            return render_template('admin/tag_form.html', action='edit', tag=tag, colors=TAG_COLORS)
        tag.name  = name
        tag.color = color
        db.session.commit()
        flash('Тег обновлён', 'success')
        return redirect(url_for('admin.tags'))
    return render_template('admin/tag_form.html', action='edit', tag=tag, colors=TAG_COLORS)


@admin_bp.route('/tags/<int:tag_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    db.session.delete(tag)
    db.session.commit()
    flash(f'Тег «{tag.name}» удалён', 'success')
    return redirect(url_for('admin.tags'))
