from django import forms
from .models import Doctor


class DoctorForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['name', 'specialization', 'room_number', 'fee', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'f-input', 'placeholder': 'Dr. Name'}),
            'specialization': forms.TextInput(attrs={'class': 'f-input'}),
            'room_number': forms.TextInput(attrs={'class': 'f-input'}),
            'fee': forms.NumberInput(attrs={'class': 'f-input'}),
        }
        
from django import forms
from .models import Doctor, Expense


class DoctorForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['name', 'specialization', 'room_number', 'fee', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'f-input', 'placeholder': 'Dr. Name'}),
            'specialization': forms.TextInput(attrs={'class': 'f-input'}),
            'room_number': forms.TextInput(attrs={'class': 'f-input'}),
            'fee': forms.NumberInput(attrs={'class': 'f-input'}),
        }


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['title', 'category', 'amount', 'payment_method', 'date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'inp', 'placeholder': 'e.g. Purchased Hand Sanitizers & Gloves'}),
            'category': forms.Select(attrs={'class': 'inp'}),
            'amount': forms.NumberInput(attrs={'class': 'inp', 'placeholder': 'e.g. 3500', 'min': 1}),
            'payment_method': forms.Select(attrs={'class': 'inp'}),
            'date': forms.DateInput(attrs={'class': 'inp', 'type': 'date'}, format='%Y-%m-%d'),
        }

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError("Amount 0 se zyada hona chahiye.")
        return amount
    