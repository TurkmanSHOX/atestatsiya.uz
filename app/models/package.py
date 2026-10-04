import uuid
from datetime import datetime, timedelta
from app.extensions import db

class OrderStatus:
    PENDING = 'PENDING'
    PAID = 'PAID'
    CANCELLED = 'CANCELLED'
    EXPIRED = 'EXPIRED'

class PaymentStatus:
    PENDING = 'PENDING'
    PAID = 'PAID'
    CONFIRMED = 'PAID'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'
    REFUNDED = 'REFUNDED'
    EXPIRED = 'EXPIRED'

class Package(db.Model):
    __tablename__ = 'packages'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    price = db.Column(db.Numeric(12, 2), nullable=False, default=10000.00) # so'm
    duration_days = db.Column(db.Integer, nullable=False, default=30)
    test_limit = db.Column(db.Integer, nullable=True) # None = cheksiz
    
    is_all_subjects = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    features = db.Column(db.JSON, nullable=True) # ['Barcha fanlar', 'AI tavsiyalar', 'Cheksiz testlar']
    order_num = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Aloqalar
    package_subjects = db.relationship('PackageSubject', back_populates='package', cascade='all, delete-orphan')
    orders = db.relationship('Order', back_populates='package')
    entitlements = db.relationship('Entitlement', back_populates='package')

    def formatted_price(self):
        return f"{self.price:,.0f} so'm".replace(',', ' ')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'price': float(self.price),
            'formatted_price': self.formatted_price(),
            'duration_days': self.duration_days,
            'test_limit': self.test_limit,
            'is_all_subjects': self.is_all_subjects,
            'is_active': self.is_active,
            'features': self.features or []
        }

class PackageSubject(db.Model):
    __tablename__ = 'package_subjects'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    package_id = db.Column(db.Integer, db.ForeignKey('packages.id', ondelete='CASCADE'), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False, index=True)

    package = db.relationship('Package', back_populates='package_subjects')
    subject = db.relationship('Subject')

class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    package_id = db.Column(db.Integer, db.ForeignKey('packages.id', ondelete='CASCADE'), nullable=False, index=True)
    
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(20), default=OrderStatus.PENDING, index=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Aloqalar
    user = db.relationship('User', back_populates='orders')
    package = db.relationship('Package', back_populates='orders')
    payments = db.relationship('Payment', back_populates='order', cascade='all, delete-orphan')
    entitlement = db.relationship('Entitlement', back_populates='order', uselist=False)

    @staticmethod
    def generate_order_number():
        return f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(10), default='UZS')
    payment_method = db.Column(db.String(30), default='CLICK')
    
    click_trans_id = db.Column(db.String(100), unique=True, nullable=True, index=True)
    click_paydoc_id = db.Column(db.String(100), nullable=True)
    sign_time = db.Column(db.String(50), nullable=True)
    
    status = db.Column(db.String(20), default=PaymentStatus.PENDING, index=True)
    error_code = db.Column(db.Integer, default=0)
    error_note = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order = db.relationship('Order', back_populates='payments')
    user = db.relationship('User', back_populates='payments')
    events = db.relationship('PaymentEvent', back_populates='payment', cascade='all, delete-orphan')

    def formatted_amount(self):
        return f"{self.amount:,.0f} {self.currency}".replace(',', ' ')

class PaymentEvent(db.Model):
    __tablename__ = 'payment_events'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id', ondelete='SET NULL'), nullable=True, index=True)
    event_type = db.Column(db.String(50), nullable=False) # PREPARE, COMPLETE, CALLBACK
    payload = db.Column(db.JSON, nullable=True)
    status = db.Column(db.String(30), default='SUCCESS')
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    payment = db.relationship('Payment', back_populates='events')

class Entitlement(db.Model):
    __tablename__ = 'entitlements'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    package_id = db.Column(db.Integer, db.ForeignKey('packages.id', ondelete='CASCADE'), nullable=False, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='SET NULL'), nullable=True, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=True, index=True) # None = barcha fanlar
    
    starts_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    tests_remaining = db.Column(db.Integer, nullable=True) # None = cheksiz
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='entitlements')
    package = db.relationship('Package', back_populates='entitlements')
    order = db.relationship('Order', back_populates='entitlement')
    subject = db.relationship('Subject')

    @property
    def is_valid(self):
        if not self.is_active:
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        if self.tests_remaining is not None and self.tests_remaining <= 0:
            return False
        return True

    @property
    def remaining_days(self):
        diff = (self.expires_at - datetime.utcnow()).days
        return max(0, diff)
