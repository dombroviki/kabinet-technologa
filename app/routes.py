from flask import render_template, redirect, url_for, request, flash, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from . import db
from .models import TVModel, TVModelPhoto, TVModelFirmware, Brand, LauncherType, User, RemoteControl, Tag
from datetime import datetime

ALLOWED_PHOTO    = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_FIRMWARE = {'bin', 'zip', 'img', 'hex'}

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def save_file(file, folder, allowed_extensions):
    if file and file.filename and allowed_file(file.filename, allowed_extensions):
        original_name = secure_filename(file.filename)
        name, ext = os.path.splitext(original_name)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S%f')
        filename = f"{name}_{timestamp}{ext}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], folder, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file.save(filepath)
        return filename
    return None

def delete_file(filename, folder):
    if filename:
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], folder, filename)
        if os.path.exists(filepath):
            os.remove(filepath)

def init_app(app):

    @app.route('/')
    @login_required
    def index():
        brands = Brand.query.order_by(Brand.name).all()
        return render_template('index.html', brands=brands)

    @app.route('/brand/<int:brand_id>')
    @login_required
    def brand_detail(brand_id):
        brand = Brand.query.get_or_404(brand_id)
        launcher_types = db.session.query(LauncherType).join(TVModel)\
            .filter(TVModel.brand_id == brand_id).distinct().all()
        return render_template('brand.html', brand=brand, launcher_types=launcher_types)

    @app.route('/brand/<int:brand_id>/launcher/<int:launcher_id>')
    @login_required
    def models_list(brand_id, launcher_id):
        brand    = Brand.query.get_or_404(brand_id)
        launcher = LauncherType.query.get_or_404(launcher_id)

        sort  = request.args.get('sort', 'date')
        order = request.args.get('order', 'desc')
        q     = request.args.get('q', '').strip()
        page  = request.args.get('page', 1, type=int)

        sort_map = {
            'model':  TVModel.model,
            'lot':    TVModel.lot,
            'tester': TVModel.tester_name,
            'date':   TVModel.date_added,
        }
        sort_col  = sort_map.get(sort, TVModel.date_added)
        sort_expr = sort_col.asc() if order == 'asc' else sort_col.desc()

        query = TVModel.query.filter_by(brand_id=brand_id, launcher_type_id=launcher_id)
        if q:
            query = query.filter(TVModel.model.ilike(f'%{q}%'))

        # Фильтр по тегу
        tag_filter = request.args.get('tag', type=int)
        if tag_filter:
            query = query.filter(TVModel.tags.any(Tag.id == tag_filter))

        all_tags = Tag.query.order_by(Tag.name).all()
        pagination = query.order_by(sort_expr).paginate(page=page, per_page=20, error_out=False)
        return render_template('models.html',
            brand=brand, launcher=launcher,
            models=pagination.items, pagination=pagination,
            sort=sort, order=order, q=q,
            all_tags=all_tags, tag_filter=tag_filter)

    @app.route('/add', methods=['GET', 'POST'])
    @login_required
    def add_model():
        if request.method == 'POST':
            brand_id       = request.form.get('brand_id')
            launcher_id    = request.form.get('launcher_type_id')
            model          = request.form.get('model')
            lot            = request.form.get('lot')
            specs          = request.form.get('specifications')
            remote         = request.form.get('remote_control')
            sw_version     = request.form.get('software_version')   # ← НОВОЕ
            tester_name    = request.form.get('tester_name') or current_user.name
            flashable      = request.form.get('is_flashable') == 'on'

            if not brand_id or not launcher_id or not model or not lot:
                flash('Заполните все обязательные поля', 'error')
                return redirect(url_for('add_model'))

            existing = TVModel.query.filter_by(brand_id=brand_id, model=model, lot=lot).first()
            if existing:
                flash('Модель с таким названием и лотом уже существует', 'error')
                return redirect(url_for('add_model'))

            firmware = request.files.get('firmware')
            firmware_filename = save_file(firmware, 'firmware', ALLOWED_FIRMWARE)

            tv = TVModel(
                brand_id=brand_id, launcher_type_id=launcher_id,
                model=model, lot=lot, specifications=specs,
                remote_control=remote,
                software_version=sw_version,
                tester_name=tester_name,
                tester_id=current_user.id,
                is_flashable=flashable,
            )
            db.session.add(tv)
            db.session.flush()

            photos = request.files.getlist('photos')
            for i, photo in enumerate(photos):
                fname = save_file(photo, 'photos', ALLOWED_PHOTO)
                if fname:
                    db.session.add(TVModelPhoto(tv_model_id=tv.id, filename=fname, order=i))

            # Несколько прошивок
            for fw_file in request.files.getlist('firmwares'):
                fname = save_file(fw_file, 'firmware', ALLOWED_FIRMWARE)
                if fname:
                    db.session.add(TVModelFirmware(
                        tv_model_id=tv.id,
                        filename=fname,
                        original_name=secure_filename(fw_file.filename)
                    ))

            # Теги
            tag_ids = request.form.getlist('tags')
            tv.tags = Tag.query.filter(Tag.id.in_([int(i) for i in tag_ids if i])).all()

            db.session.commit()
            flash('Модель успешно добавлена', 'success')
            back_url = request.form.get('back_url', '')
            if back_url:
                return redirect(back_url)
            return redirect(url_for('models_list', brand_id=brand_id, launcher_id=launcher_id))

        brands = Brand.query.order_by(Brand.name).all()
        launcher_types = LauncherType.query.order_by(LauncherType.name).all()
        remotes = RemoteControl.query.order_by(RemoteControl.name).all()
        all_tags = Tag.query.order_by(Tag.name).all()
        prefill = {
            'brand_id':    request.args.get('prefill_brand', ''),
            'launcher_id': request.args.get('prefill_launcher', ''),
            'model':       request.args.get('prefill_model', ''),
            'lot':         request.args.get('prefill_lot', ''),
            'remote':      request.args.get('prefill_remote', ''),
            'sw_version':  request.args.get('prefill_sw', ''),
            'tester':      request.args.get('prefill_tester', ''),
            'flashable':   request.args.get('prefill_flashable', '0') == '1',
            'specs':       request.args.get('prefill_specs', ''),
        }
        back_url = request.args.get('back_url', '')

        # Подгружаем объекты для хлебных крошек
        prefill_brand_obj    = Brand.query.get(prefill['brand_id'])    if prefill['brand_id']    else None
        prefill_launcher_obj = LauncherType.query.get(prefill['launcher_id']) if prefill['launcher_id'] else None

        return render_template('add.html', brands=brands, launcher_types=launcher_types,
                               remotes=remotes, all_tags=all_tags, prefill=prefill, back_url=back_url,
                               prefill_brand_obj=prefill_brand_obj, prefill_launcher_obj=prefill_launcher_obj)

    @app.route('/view/<int:id>')
    @login_required
    def view_model(id):
        model = TVModel.query.get_or_404(id)
        back_url = request.args.get('back_url') or request.referrer or \
                   url_for('models_list', brand_id=model.brand_id, launcher_id=model.launcher_type_id)
        return render_template('view.html', model=model, back_url=back_url)

    @app.route('/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_model(id):
        model = TVModel.query.get_or_404(id)

        if request.method == 'POST':
            model.brand_id         = request.form.get('brand_id')
            model.launcher_type_id = request.form.get('launcher_type_id')
            model.model            = request.form.get('model')
            model.lot              = request.form.get('lot')
            model.specifications   = request.form.get('specifications')
            model.remote_control   = request.form.get('remote_control')
            model.software_version = request.form.get('software_version')   # ← НОВОЕ
            model.tester_name      = request.form.get('tester_name') or current_user.name
            model.is_flashable     = request.form.get('is_flashable') == 'on'

            if not all([model.brand_id, model.launcher_type_id, model.model, model.lot]):
                flash('Заполните все обязательные поля', 'error')
                return redirect(url_for('edit_model', id=id))

            duplicate = TVModel.query.filter(
                TVModel.brand_id == model.brand_id,
                TVModel.model == model.model,
                TVModel.lot == model.lot,
                TVModel.id != id
            ).first()
            if duplicate:
                flash('Модель с таким названием и лотом уже существует', 'error')
                return redirect(url_for('edit_model', id=id))

            # Удаление отмеченных фото
            for pid in request.form.getlist('delete_photos'):
                photo = TVModelPhoto.query.get(int(pid))
                if photo and photo.tv_model_id == id:
                    delete_file(photo.filename, 'photos')
                    db.session.delete(photo)

            # Новые фото
            current_count = TVModelPhoto.query.filter_by(tv_model_id=id).count()
            for i, photo in enumerate(request.files.getlist('photos')):
                fname = save_file(photo, 'photos', ALLOWED_PHOTO)
                if fname:
                    db.session.add(TVModelPhoto(tv_model_id=id, filename=fname, order=current_count + i))

            # Удаление отмеченных прошивок
            for fid in request.form.getlist('delete_firmwares'):
                fw = TVModelFirmware.query.get(int(fid))
                if fw and fw.tv_model_id == id:
                    delete_file(fw.filename, 'firmware')
                    db.session.delete(fw)

            # Новые прошивки
            for fw_file in request.files.getlist('firmwares'):
                fname = save_file(fw_file, 'firmware', ALLOWED_FIRMWARE)
                if fname:
                    db.session.add(TVModelFirmware(
                        tv_model_id=id,
                        filename=fname,
                        original_name=secure_filename(fw_file.filename)
                    ))

            # Теги
            tag_ids = request.form.getlist('tags')
            model.tags = Tag.query.filter(Tag.id.in_([int(i) for i in tag_ids if i])).all()

            db.session.commit()
            flash('Модель обновлена', 'success')
            back_url = request.form.get('back_url', '')
            return redirect(url_for('edit_model', id=id, back_url=back_url))

        back_url = request.args.get('back_url') or request.referrer or \
                   url_for('models_list', brand_id=model.brand_id, launcher_id=model.launcher_type_id)

        brands = Brand.query.order_by(Brand.name).all()
        launcher_types = LauncherType.query.order_by(LauncherType.name).all()
        all_tags = Tag.query.order_by(Tag.name).all()
        remotes = RemoteControl.query.order_by(RemoteControl.name).all()
        return render_template('edit.html', model=model, brands=brands,
                               launcher_types=launcher_types, remotes=remotes,
                               all_tags=all_tags, back_url=back_url)

    @app.route('/duplicate/<int:id>')
    @login_required
    def duplicate_model(id):
        src = TVModel.query.get_or_404(id)
        # Не создаём запись — просто открываем форму добавления с предзаполненными данными
        return redirect(url_for('add_model',
            prefill_brand=src.brand_id,
            prefill_launcher=src.launcher_type_id,
            prefill_model=src.model + ' (копия)',
            prefill_lot=src.lot,
            prefill_remote=src.remote_control or '',
            prefill_sw=src.software_version or '',
            prefill_tester=src.tester_name or '',
            prefill_flashable='1' if src.is_flashable else '0',
            prefill_specs=src.specifications or '',
            back_url=url_for('models_list', brand_id=src.brand_id, launcher_id=src.launcher_type_id),
        ))

    @app.route('/delete/<int:id>', methods=['POST'])
    @login_required
    def delete_model(id):
        model = TVModel.query.get_or_404(id)
        brand_id, launcher_id = model.brand_id, model.launcher_type_id
        for photo in model.photos:
            delete_file(photo.filename, 'photos')
        delete_file(model.firmware_filename, 'firmware')
        db.session.delete(model)
        db.session.commit()
        flash('Модель удалена', 'success')
        return redirect(url_for('models_list', brand_id=brand_id, launcher_id=launcher_id))

    @app.route('/download/<int:id>/<file_type>')
    @login_required
    def download_file(id, file_type):
        model = TVModel.query.get_or_404(id)
        if file_type == 'firmware' and model.firmware_filename:
            return send_from_directory(
                os.path.join(current_app.config['UPLOAD_FOLDER'], 'firmware'),
                model.firmware_filename, as_attachment=True,
                download_name=model.firmware_filename)
        flash('Файл не найден', 'error')
        return redirect(url_for('view_model', id=id))

    @app.route('/download_firmware/<int:fw_id>')
    @login_required
    def download_firmware(fw_id):
        fw = TVModelFirmware.query.get_or_404(fw_id)
        return send_from_directory(
            os.path.join(current_app.config['UPLOAD_FOLDER'], 'firmware'),
            fw.filename, as_attachment=True,
            download_name=fw.original_name)

    @app.route('/delete_firmware/<int:fw_id>', methods=['POST'])
    @login_required
    def delete_firmware(fw_id):
        fw = TVModelFirmware.query.get_or_404(fw_id)
        model_id = fw.tv_model_id
        delete_file(fw.filename, 'firmware')
        db.session.delete(fw)
        db.session.commit()
        flash('Прошивка удалена', 'success')
        return redirect(url_for('view_model', id=model_id))

    @app.route('/api/suggest')
    @login_required
    def suggest():
        from flask import jsonify
        q = request.args.get('q', '').strip()
        if len(q) < 2:
            return jsonify([])
        results = TVModel.query\
            .join(Brand).join(LauncherType)\
            .filter(
                db.or_(
                    TVModel.model.ilike(f'%{q}%'),
                    TVModel.lot.ilike(f'%{q}%'),
                    TVModel.software_version.ilike(f'%{q}%'),
                    Brand.name.ilike(f'%{q}%'),
                )
            ).order_by(TVModel.date_added.desc()).limit(8).all()
        return jsonify([{
            'id':       m.id,
            'model':    m.model,
            'brand':    m.brand.name,
            'launcher': m.launcher_type.name,
            'lot':      m.lot,
            'sw':       m.software_version or '',
            'url':      url_for('view_model', id=m.id),
        } for m in results])

    @app.route('/search')
    @login_required
    def search():
        q = request.args.get('q', '').strip()
        results = []
        if q:
            results = TVModel.query\
                .join(Brand).join(LauncherType)\
                .filter(
                    db.or_(
                        TVModel.model.ilike(f'%{q}%'),
                        TVModel.lot.ilike(f'%{q}%'),
                        TVModel.tester_name.ilike(f'%{q}%'),
                        TVModel.remote_control.ilike(f'%{q}%'),
                        TVModel.software_version.ilike(f'%{q}%'),
                        Brand.name.ilike(f'%{q}%'),
                    )
                ).order_by(TVModel.date_added.desc()).limit(50).all()
        return render_template('search.html', q=q, results=results)

    @app.route('/download_photo/<int:photo_id>')
    @login_required
    def download_photo(photo_id):
        photo = TVModelPhoto.query.get_or_404(photo_id)
        return send_from_directory(
            os.path.join(current_app.config['UPLOAD_FOLDER'], 'photos'),
            photo.filename, as_attachment=True, download_name=photo.filename)
