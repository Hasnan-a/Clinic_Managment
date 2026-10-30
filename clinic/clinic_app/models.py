from django.db import models

class Patient(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]

    BLOOD_GROUP_CHOICES = [
        ('', 'Unknown'),
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('O+', 'O+'), ('O-', 'O-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
    ]

    mr_number = models.CharField(max_length=20, unique=True, blank=True)
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=25)
    cnic = models.CharField(max_length=25, blank=True, null=True)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUP_CHOICES, blank=True, default='')
    address = models.TextField(blank=True, default='')
    emergency_contact = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Auto-generate MR Number (MR-1001, MR-1002...)
        if not self.mr_number:
            last = Patient.objects.order_by('-id').first()
            next_num = (last.id + 1001) if last else 1001
            self.mr_number = f"MR-{next_num}"
        super().save(*args, **kwargs)

    @property
    def initials(self):
        parts = self.name.strip().split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[1][0]}".upper()
        elif parts:
            return parts[0][:2].upper()
        return "PT"

    def __str__(self):
        return f"{self.mr_number} - {self.name}"
    
    
    # 2 STEP





# 1. DOCTOR MODEL
class Doctor(models.Model):
    name = models.CharField(max_length=120)
    specialization = models.CharField(max_length=120, default='General Physician')
    room_number = models.CharField(max_length=30, default='Room 01')
    fee = models.PositiveIntegerField(default=1500)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.room_number})"


# 2. OPD TOKEN MODEL
class OpdToken(models.Model):
    STATUS_CHOICES = [
        ('Waiting', 'Waiting'),
        ('Serving', 'Serving'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    PAYMENT_CHOICES = [
        ('Cash', 'Cash'),
        ('Online', 'Online Transfer / EasyPaisa'),
        ('Card', 'Card'),
    ]

    token_number = models.PositiveIntegerField()  # Daily reset: 1, 2, 3...
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='tokens')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    room_number = models.CharField(max_length=50, default='Room 01')
    fee = models.PositiveIntegerField(default=1500)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_CHOICES, default='Cash')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Waiting')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['token_number']

    def __str__(self):
        return f"Token #{self.token_number:02d} - {self.patient.name} ({self.status})"
    
    
from django.utils import timezone


class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('Medical Supplies', 'Medical Supplies'),
        ('Utilities & Generator', 'Utilities & Generator'),
        ('Stationery & Print', 'Stationery & Print'),
        ('Staff Salary & Tea', 'Staff Salary & Tea'),
        ('Maintenance & Repair', 'Maintenance & Repair'),
        ('Miscellaneous', 'Miscellaneous'),
    ]

    PAYMENT_CHOICES = [
        ('Cash In Hand', 'Cash In Hand'),
        ('Bank Account', 'Bank Account'),
        ('EasyPaisa / JazzCash', 'EasyPaisa / JazzCash'),
    ]

    voucher_number = models.CharField(max_length=20, blank=True)
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Medical Supplies')
    amount = models.PositiveIntegerField()
    payment_method = models.CharField(max_length=50, choices=PAYMENT_CHOICES, default='Cash In Hand')
    date = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-id']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Voucher number: EXP-501, EXP-502 ... (id se banta hai)
        if not self.voucher_number:
            self.voucher_number = f"EXP-{500 + self.pk}"
            super().save(update_fields=['voucher_number'])

    def __str__(self):
        return f"{self.voucher_number} - {self.title} (Rs. {self.amount})"