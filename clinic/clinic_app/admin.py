from django.contrib import admin
from .models import Patient, Doctor, OpdToken,Expense


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('mr_number', 'name', 'phone', 'age', 'gender', 'blood_group', 'created_at')
    search_fields = ('mr_number', 'name', 'phone', 'cnic')
    list_filter = ('gender', 'blood_group', 'created_at')
    ordering = ('-created_at',)
    readonly_fields = ('mr_number', 'created_at', 'updated_at')


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialization', 'room_number', 'fee', 'is_active')
    search_fields = ('name', 'specialization', 'room_number')
    list_filter = ('is_active', 'specialization')
    list_editable = ('is_active', 'fee')
    ordering = ('name',)


@admin.register(OpdToken)
class OpdTokenAdmin(admin.ModelAdmin):
    list_display = ('token_number', 'patient', 'doctor', 'room_number', 'fee',
                    'payment_method', 'status', 'created_at')
    search_fields = ('patient__name', 'patient__mr_number', 'patient__phone', 'doctor__name')
    list_filter = ('status', 'payment_method', 'doctor', 'created_at')
    list_editable = ('status',)
    autocomplete_fields = ('patient',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at', 'token_number')
    readonly_fields = ('created_at', 'updated_at')
    



@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('voucher_number', 'title', 'category', 'amount', 'payment_method', 'date')
    search_fields = ('voucher_number', 'title')
    list_filter = ('category', 'payment_method', 'date')
    date_hierarchy = 'date'
    readonly_fields = ('voucher_number', 'created_at', 'updated_at')