from app import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)          # Фамилия И.О.
    password_hash = db.Column(db.String(256), nullable=True)  # None если вход через Google
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    role = db.Column(db.String(20), default='user', nullable=False)  # 'admin' | 'user'
    is_active_user = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_editor(self):
        # admin и user могут редактировать, viewer — только читать
        return self.role in ('admin', 'user')

    @property
    def is_viewer(self):
        return self.role == 'viewer'

    def __repr__(self):
        return f'<User {self.email}>'


class RemoteControl(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    # При переименовании — все модели автоматически видят новое имя через FK
    tv_models = db.relationship('TVModel', backref='remote', lazy=True,
                                foreign_keys='TVModel.remote_control_id')

# Таблица связи тегов и моделей (many-to-many)
tv_model_tags = db.Table('tv_model_tags',
    db.Column('tv_model_id', db.Integer, db.ForeignKey('tv_model.id'), primary_key=True),
    db.Column('tag_id',      db.Integer, db.ForeignKey('tag.id'),      primary_key=True)
)

class Tag(db.Model):
    id    = db.Column(db.Integer, primary_key=True)
    name  = db.Column(db.String(100), unique=True, nullable=False)
    color = db.Column(db.String(20), default='#5b8dee', nullable=False)  # hex цвет

class Brand(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    name      = db.Column(db.String(100), unique=True, nullable=False)
    tab_color = db.Column(db.String(10), nullable=True)  # ARGB цвет вкладки Excel, напр. FFFF9900
    tv_models = db.relationship('TVModel', backref='brand', lazy=True,
                                cascade='all, delete-orphan')

class LauncherType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    tv_models = db.relationship('TVModel', backref='launcher_type', lazy=True,
                                cascade='all, delete-orphan')

class TVModelPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tv_model_id = db.Column(db.Integer, db.ForeignKey('tv_model.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    order = db.Column(db.Integer, default=0)

class TVModelFirmware(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tv_model_id = db.Column(db.Integer, db.ForeignKey('tv_model.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)       # имя файла на диске
    original_name = db.Column(db.String(200), nullable=False)  # оригинальное имя файла
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class TVModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model = db.Column(db.String(100), nullable=False)
    lot = db.Column(db.String(100), nullable=False)
    specifications = db.Column(db.Text, nullable=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    firmware_filename = db.Column(db.String(200), nullable=True)  # legacy, не используется
    remote_control = db.Column(db.String(200), nullable=True)     # legacy, оставляем для совместимости
    remote_control_id = db.Column(db.Integer, db.ForeignKey('remote_control.id'), nullable=True)
    software_version = db.Column(db.String(100), nullable=True)
    tester_name = db.Column(db.String(100), nullable=True)
    tester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_flashable = db.Column(db.Boolean, default=False, nullable=False)

    brand_id = db.Column(db.Integer, db.ForeignKey('brand.id'), nullable=False)
    launcher_type_id = db.Column(db.Integer, db.ForeignKey('launcher_type.id'), nullable=False)

    photos = db.relationship('TVModelPhoto', backref='tv_model', lazy=True,
                             cascade='all, delete-orphan', order_by='TVModelPhoto.order')
    firmwares = db.relationship('TVModelFirmware', backref='tv_model', lazy=True,
                                cascade='all, delete-orphan', order_by='TVModelFirmware.uploaded_at')
    tags = db.relationship('Tag', secondary='tv_model_tags', lazy=True, backref=db.backref('tv_models', lazy=True))
    tester = db.relationship('User', foreign_keys=[tester_id])

    __table_args__ = (
        db.UniqueConstraint('brand_id', 'model', 'lot', name='_brand_model_lot_uc'),
        db.Index('ix_tvmodel_brand_launcher', 'brand_id', 'launcher_type_id'),
        db.Index('ix_tvmodel_date_added', 'date_added'),
        db.Index('ix_tvmodel_model', 'model'),
        db.Index('ix_tvmodel_tester', 'tester_name'),
        db.Index('ix_tvmodel_software_version', 'software_version'),
    )


class AuditLog(db.Model):
    """История изменений моделей телевизоров"""
    id          = db.Column(db.Integer, primary_key=True)
    tv_model_id = db.Column(db.Integer, db.ForeignKey('tv_model.id', ondelete='SET NULL'), nullable=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    action      = db.Column(db.String(20), nullable=False)   # 'create' | 'edit' | 'delete' | 'inline'
    model_name  = db.Column(db.String(100), nullable=True)   # snapshot имени модели на момент действия
    field       = db.Column(db.String(100), nullable=True)   # какое поле изменилось
    old_value   = db.Column(db.Text, nullable=True)
    new_value   = db.Column(db.Text, nullable=True)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user     = db.relationship('User', foreign_keys=[user_id])
    tv_model = db.relationship('TVModel', foreign_keys=[tv_model_id])

    db.Index('ix_auditlog_tv_model', 'tv_model_id')
    db.Index('ix_auditlog_timestamp', 'timestamp')


class ModelComment(db.Model):
    """Комментарии к моделям телевизоров"""
    id          = db.Column(db.Integer, primary_key=True)
    tv_model_id = db.Column(db.Integer, db.ForeignKey('tv_model.id', ondelete='CASCADE'), nullable=False)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    text        = db.Column(db.Text, nullable=False)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user     = db.relationship('User', foreign_keys=[user_id])
    tv_model = db.relationship('TVModel', foreign_keys=[tv_model_id],
                               backref=db.backref('comments', lazy=True,
                                                  cascade='all, delete-orphan',
                                                  order_by='ModelComment.timestamp'))
