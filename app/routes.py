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
        all_remotes = RemoteControl.query.order_by(RemoteControl.name).all()
        pagination = query.order_by(sort_expr).paginate(page=page, per_page=20, error_out=False)
        return render_template('models.html',
            brand=brand, launcher=launcher,
            models=pagination.items, pagination=pagination,
            sort=sort, order=order, q=q,
            all_tags=all_tags, tag_filter=tag_filter,
            all_remotes=all_remotes)

    @app.route('/add', methods=['GET', 'POST'])
    @login_required
    def add_model():
        if request.method == 'POST':
            brand_id       = request.form.get('brand_id')
            launcher_id    = request.form.get('launcher_type_id')
            model          = request.form.get('model')
            lot            = request.form.get('lot')
            specs          = request.form.get('specifications')
            remote         = request.form.get('remote_control')  # это ID пульта
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
                remote_control_id=int(remote) if remote else None,
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
            model.remote_control_id = int(request.form.get('remote_control')) if request.form.get('remote_control') else None
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
            prefill_remote=src.remote.name if src.remote else '',
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
        brand_id = request.args.get('brand_id', '').strip()
        if len(q) < 2:
            return jsonify([])

        words = q.split()
        query = TVModel.query.join(Brand).join(LauncherType)

        # Фильтруем по бренду если передан (локальный поиск)
        if brand_id:
            query = query.filter(TVModel.brand_id == brand_id)

        # Каждое слово должно встречаться хоть в одном поле
        for word in words:
            query = query.filter(db.or_(
                TVModel.model.ilike(f'%{word}%'),
                TVModel.lot.ilike(f'%{word}%'),
                TVModel.software_version.ilike(f'%{word}%'),
                Brand.name.ilike(f'%{word}%'),
            ))

        results = query.order_by(TVModel.date_added.desc()).limit(8).all()
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
            words = q.split()
            query = TVModel.query.join(Brand).join(LauncherType)
            for word in words:
                query = query.filter(db.or_(
                    TVModel.model.ilike(f'%{word}%'),
                    TVModel.lot.ilike(f'%{word}%'),
                    TVModel.tester_name.ilike(f'%{word}%'),
                    TVModel.software_version.ilike(f'%{word}%'),
                    Brand.name.ilike(f'%{word}%'),
                ))
            results = query.order_by(TVModel.date_added.desc()).limit(50).all()
        return render_template('search.html', q=q, results=results)

    @app.route('/download_photo/<int:photo_id>')
    @login_required
    def download_photo(photo_id):
        photo = TVModelPhoto.query.get_or_404(photo_id)
        return send_from_directory(
            os.path.join(current_app.config['UPLOAD_FOLDER'], 'photos'),
            photo.filename, as_attachment=True, download_name=photo.filename)

    # ── ГЛОБАЛЬНЫЙ ЭКСПОРТ ВСЕГО ──
    @app.route('/export/all')
    @login_required
    def export_all():
        import io, csv
        from flask import Response
        models = TVModel.query.join(Brand).join(LauncherType)\
            .order_by(Brand.name, LauncherType.name, TVModel.model).all()

        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow([
            'Бренд', 'Лаунчер', 'Модель', 'Лот', 'Пульт', 'Версия ПО',
            'Прошивается', 'Тестировщик', 'Метки', 'Дата добавления'
        ])
        for m in models:
            writer.writerow([
                m.brand.name,
                m.launcher_type.name,
                m.model,
                m.lot,
                m.remote.name if m.remote else '',
                m.software_version or '',
                'Да' if m.is_flashable else 'Нет',
                m.tester_name or '',
                ', '.join(t.name for t in m.tags),
                m.date_added.strftime('%d.%m.%Y'),
            ])

        output.seek(0)
        return Response(
            '\ufeff' + output.getvalue(),
            mimetype='text/csv; charset=utf-8',
            headers={'Content-Disposition': 'attachment; filename="kabinet_export.csv"'}
        )

    # ── ГЛОБАЛЬНЫЙ ИМПОРТ ──
    @app.route('/import/all', methods=['GET', 'POST'])
    @login_required
    def import_all():
        if request.method == 'POST':
            import io
            file = request.files.get('file')
            if not file or not file.filename:
                flash('Выберите файл', 'error')
                return redirect(request.url)

            launcher_name = 'собственный'
            ext = file.filename.rsplit('.', 1)[-1].lower()

            try:
                added = skipped = 0
                BATCH = 100  # коммит каждые 100 записей

                # ── Кэш брендов, пультов, существующих моделей ──
                brand_cache   = {b.name: b for b in Brand.query.all()}
                remote_cache  = {r.name: r for r in RemoteControl.query.all()}
                existing_set  = {
                    (m.brand_id, m.model, m.lot)
                    for m in db.session.query(TVModel.brand_id, TVModel.model, TVModel.lot).all()
                }

                launcher = LauncherType.query.filter_by(name=launcher_name).first()
                if not launcher:
                    launcher = LauncherType(name=launcher_name)
                    db.session.add(launcher)
                    db.session.flush()

                if ext in ('xlsx', 'xls'):
                    import openpyxl
                    wb = openpyxl.load_workbook(
                        io.BytesIO(file.read()),
                        data_only=True,
                        read_only=True  # экономим память
                    )

                    skip_sheets = {'Требования по качеству'}

                    for sheet_name in wb.sheetnames:
                        if sheet_name in skip_sheets:
                            continue

                        brand_name = sheet_name.strip()
                        if brand_name not in brand_cache:
                            brand = Brand(name=brand_name)
                            db.session.add(brand)
                            db.session.flush()
                            brand_cache[brand_name] = brand
                        brand = brand_cache[brand_name]

                        ws = wb[sheet_name]
                        for row in ws.iter_rows(min_row=5, values_only=False):
                            model_name = str(row[0].value).strip() if row[0].value else ''
                            if not model_name or model_name == 'None':
                                continue
                            lot_raw = row[1].value
                            lot = str(int(lot_raw)) if isinstance(lot_raw, float) else str(lot_raw or '').strip()
                            if not lot or lot == 'None':
                                continue

                            if (brand.id, model_name, lot) in existing_set:
                                skipped += 1
                                continue

                            tester     = str(row[7].value).strip() if row[7].value else ''
                            flashable  = str(row[8].value).strip().lower() == 'да' if row[8].value else False
                            sw_version = str(row[9].value).strip() if row[9].value else ''
                            remote     = str(row[10].value).strip() if row[10].value else ''

                            sw_comment = ''
                            try:
                                if row[9].comment and row[9].comment.text:
                                    raw = row[9].comment.text.strip()
                                    marker = 'Comment:'
                                    if marker in raw:
                                        raw = raw[raw.index(marker) + len(marker):].strip()
                                    sw_comment = raw
                            except Exception:
                                pass

                            remote_id = None
                            if remote:
                                if remote not in remote_cache:
                                    rc = RemoteControl(name=remote)
                                    db.session.add(rc)
                                    db.session.flush()
                                    remote_cache[remote] = rc
                                remote_id = remote_cache[remote].id

                            tv = TVModel(
                                brand_id=brand.id,
                                launcher_type_id=launcher.id,
                                model=model_name, lot=lot,
                                remote_control_id=remote_id,
                                software_version=sw_version or None,
                                specifications=sw_comment or None,
                                is_flashable=flashable,
                                tester_name=tester or None,
                                tester_id=current_user.id if tester else None,
                            )
                            db.session.add(tv)
                            existing_set.add((brand.id, model_name, lot))
                            added += 1

                            if added % BATCH == 0:
                                db.session.commit()

                    wb.close()

                else:
                    import csv
                    content_str = file.read().decode('utf-8-sig')
                    reader = csv.DictReader(io.StringIO(content_str), delimiter=';')

                    for row in reader:
                        brand_name = row.get('Бренд', '').strip()
                        model_name = row.get('Модель', '').strip()
                        lot        = row.get('Лот', '').strip()
                        if not all([brand_name, model_name, lot]):
                            skipped += 1
                            continue

                        if brand_name not in brand_cache:
                            brand = Brand(name=brand_name)
                            db.session.add(brand)
                            db.session.flush()
                            brand_cache[brand_name] = brand
                        brand = brand_cache[brand_name]

                        if (brand.id, model_name, lot) in existing_set:
                            skipped += 1
                            continue

                        remote_name = row.get('Пульт', '').strip()
                        remote_id = None
                        if remote_name:
                            if remote_name not in remote_cache:
                                rc = RemoteControl(name=remote_name)
                                db.session.add(rc)
                                db.session.flush()
                                remote_cache[remote_name] = rc
                            remote_id = remote_cache[remote_name].id

                        tv = TVModel(
                            brand_id=brand.id, launcher_type_id=launcher.id,
                            model=model_name, lot=lot,
                            remote_control_id=remote_id,
                            software_version=row.get('Версия ПО', '').strip() or None,
                            is_flashable=row.get('Прошивается', '').strip() == 'Да',
                            tester_name=row.get('Тестировщик', '').strip() or current_user.name,
                            tester_id=current_user.id,
                        )
                        db.session.add(tv)
                        existing_set.add((brand.id, model_name, lot))
                        added += 1

                        if added % BATCH == 0:
                            db.session.commit()

                db.session.commit()
                flash(f'Импортировано: {added} моделей, пропущено дублей: {skipped}', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка импорта: {e}', 'error')

            return redirect(url_for('index'))

        return render_template('import_all.html')

    # ── ИНЛАЙН РЕДАКТИРОВАНИЕ ──
    @app.route('/api/inline_edit/<int:id>', methods=['POST'])
    @login_required
    def inline_edit(id):
        from flask import jsonify
        model = TVModel.query.get_or_404(id)
        data  = request.get_json()
        field = data.get('field')
        value = data.get('value', '').strip()

        allowed = {'software_version', 'remote_control', 'lot', 'tester_name', 'is_flashable'}
        if field not in allowed:
            return jsonify({'ok': False, 'error': 'Поле недоступно'}), 400

        if field == 'is_flashable':
            setattr(model, field, value in ('true', '1', True))
        elif field == 'remote_control':
            # Ищем пульт по имени, сохраняем FK
            if value:
                remote = RemoteControl.query.filter_by(name=value).first()
                model.remote_control_id = remote.id if remote else None
            else:
                model.remote_control_id = None
        else:
            setattr(model, field, value or None)

        db.session.commit()
        return jsonify({'ok': True, 'value': getattr(model, field)})

    # ── ЭКСПОРТ В EXCEL ──
    @app.route('/export/<int:brand_id>/<int:launcher_id>')
    @login_required
    def export_excel(brand_id, launcher_id):
        import io, csv
        from flask import Response
        brand    = Brand.query.get_or_404(brand_id)
        launcher = LauncherType.query.get_or_404(launcher_id)
        models   = TVModel.query.filter_by(
            brand_id=brand_id, launcher_type_id=launcher_id
        ).order_by(TVModel.date_added.desc()).all()

        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow([
            'Модель', 'Лот', 'Пульт', 'Версия ПО',
            'Прошивается', 'Тестировщик', 'Метки', 'Дата добавления'
        ])
        for m in models:
            writer.writerow([
                m.model,
                m.lot,
                m.remote.name if m.remote else '',
                m.software_version or '',
                'Да' if m.is_flashable else 'Нет',
                m.tester_name or '',
                ', '.join(t.name for t in m.tags),
                m.date_added.strftime('%d.%m.%Y'),
            ])

        output.seek(0)
        filename = f"{brand.name}_{launcher.name}.csv"
        return Response(
            '\ufeff' + output.getvalue(),  # BOM для Excel
            mimetype='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )

    # ── ИМПОРТ ИЗ CSV/EXCEL ──
    @app.route('/import/<int:brand_id>/<int:launcher_id>', methods=['GET', 'POST'])
    @login_required
    def import_models(brand_id, launcher_id):
        brand    = Brand.query.get_or_404(brand_id)
        launcher = LauncherType.query.get_or_404(launcher_id)

        if request.method == 'POST':
            import io, csv
            file = request.files.get('file')
            if not file or not file.filename:
                flash('Выберите файл', 'error')
                return redirect(request.url)

            try:
                content = file.read().decode('utf-8-sig')  # utf-8 с BOM
                reader  = csv.DictReader(io.StringIO(content), delimiter=';')
                added = 0
                skipped = 0
                for row in reader:
                    model_name = row.get('Модель', '').strip()
                    lot        = row.get('Лот', '').strip()
                    if not model_name or not lot:
                        skipped += 1
                        continue
                    existing = TVModel.query.filter_by(
                        brand_id=brand_id, model=model_name, lot=lot
                    ).first()
                    if existing:
                        skipped += 1
                        continue
                    remote_name = row.get('Пульт', '').strip()
                    remote_id = None
                    if remote_name:
                        rc = RemoteControl.query.filter_by(name=remote_name).first()
                        if not rc:
                            rc = RemoteControl(name=remote_name)
                            db.session.add(rc)
                            db.session.flush()
                        remote_id = rc.id
                    tv = TVModel(
                        brand_id=brand_id,
                        launcher_type_id=launcher_id,
                        model=model_name,
                        lot=lot,
                        remote_control_id=remote_id,
                        software_version=row.get('Версия ПО', '').strip() or None,
                        is_flashable=row.get('Прошивается', '').strip() == 'Да',
                        tester_name=row.get('Тестировщик', '').strip() or current_user.name,
                        tester_id=current_user.id,
                    )
                    db.session.add(tv)
                    added += 1

                db.session.commit()
                flash(f'Импортировано: {added} моделей, пропущено: {skipped}', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка импорта: {e}', 'error')

            return redirect(url_for('models_list', brand_id=brand_id, launcher_id=launcher_id))

        return render_template('import.html', brand=brand, launcher=launcher)
