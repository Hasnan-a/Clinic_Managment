import json
import calendar
from datetime import datetime, timedelta
from django.contrib.auth import logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, Count
from django.db.models.functions import ExtractDay, TruncDate, TruncMonth
from django.utils import timezone

from .models import Patient, Doctor, OpdToken, Expense
from .forms import DoctorForm, ExpenseForm


# 1. OVERVIEW (DASHBOARD)
def _pct_change(current, previous):
    """Pichle period se kitne percent farq hai."""
    if previous == 0:
        return 100 if current > 0 else 0
    return round((current - previous) / previous * 100)


@login_required(login_url='login')
def dashboard_view(request):
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)

    valid_tokens = OpdToken.objects.exclude(status='Cancelled')

    # ---------- CARD 1: Total Patients ----------
    total_patients = Patient.objects.count()
    last7 = Patient.objects.filter(created_at__date__gte=today - timedelta(days=6)).count()
    prev7 = Patient.objects.filter(
        created_at__date__gte=today - timedelta(days=13),
        created_at__date__lte=today - timedelta(days=7),
    ).count()
    patients_trend = _pct_change(last7, prev7)

    # ---------- CARD 2: Today's Tokens ----------
    today_tokens_qs = valid_tokens.filter(created_at__date=today)
    today_tokens_count = today_tokens_qs.count()
    yesterday_count = valid_tokens.filter(created_at__date=yesterday).count()
    tokens_trend = _pct_change(today_tokens_count, yesterday_count)

    # ---------- CARD 3: Queue Waiting ----------
    waiting_count = today_tokens_qs.filter(status='Waiting').count()
    serving_count = today_tokens_qs.filter(status='Serving').count()
    completed_count = today_tokens_qs.filter(status='Completed').count()

    # ---------- CARD 4: Expenses (is mahine ke) ----------
    month_start = today.replace(day=1)
    prev_month_end = month_start - timedelta(days=1)

    month_expense = Expense.objects.filter(
        date__year=today.year, date__month=today.month
    ).aggregate(t=Sum('amount'))['t'] or 0
    prev_month_expense = Expense.objects.filter(
        date__year=prev_month_end.year, date__month=prev_month_end.month
    ).aggregate(t=Sum('amount'))['t'] or 0
    expense_trend = _pct_change(month_expense, prev_month_expense)

    # ---------- CHART 1: Last 7 Days ----------
    start = today - timedelta(days=6)
    rows = (valid_tokens.filter(created_at__date__gte=start, created_at__date__lte=today)
            .annotate(d=TruncDate('created_at')).values('d').annotate(c=Count('id')))
    by_day = {r['d']: r['c'] for r in rows}
    days = [start + timedelta(days=i) for i in range(7)]
    week_chart = {
        'name': 'Daily Tokens',
        'categories': [d.strftime('%b %d') for d in days],
        'data': [by_day.get(d, 0) for d in days],
    }

    # ---------- CHART 2: Is mahine ke 4 hafte ----------
    last_day = calendar.monthrange(today.year, today.month)[1]
    week_counts = [0, 0, 0, 0]
    rows = (valid_tokens.filter(created_at__year=today.year, created_at__month=today.month)
            .annotate(day=ExtractDay('created_at')).values('day').annotate(c=Count('id')))
    for r in rows:
        week_counts[min((r['day'] - 1) // 7, 3)] += r['c']
    month_chart = {
        'name': 'Weekly Tokens',
        'categories': [
            f'Week 1 (1-7)', f'Week 2 (8-14)', f'Week 3 (15-21)', f'Week 4 (22-{last_day})'
        ],
        'data': week_counts,
    }

    # ---------- CHART 3: Is saal ke 12 mahine ----------
    month_counts = [0] * 12
    rows = (valid_tokens.filter(created_at__year=today.year)
            .annotate(m=TruncMonth('created_at')).values('m').annotate(c=Count('id')))
    for r in rows:
        month_counts[r['m'].month - 1] = r['c']
    year_chart = {
        'name': 'Monthly Tokens',
        'categories': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
        'data': month_counts,
    }

    # ---------- TABLES ----------
    recent_tokens = (today_tokens_qs.select_related('patient', 'doctor')
                     .order_by('-token_number')[:5])
    queue_tokens = (OpdToken.objects.filter(created_at__date=today, status__in=['Serving', 'Waiting'])
                    .select_related('patient', 'doctor').order_by('token_number')[:5])

    return render(request, 'dashboard.html', {
        'total_patients': total_patients,
        'patients_trend': patients_trend,
        'today_tokens_count': today_tokens_count,
        'tokens_trend': tokens_trend,
        'waiting_count': waiting_count,
        'serving_count': serving_count,
        'completed_count': completed_count,
        'month_expense': month_expense,
        'expense_trend': expense_trend,
        'recent_tokens': recent_tokens,
        'queue_tokens': queue_tokens,
        'chart_data': {'week': week_chart, 'month': month_chart, 'year': year_chart},
    })


# 2. PATIENTS - LIST WITH LIVE SEARCH & FILTERS
@login_required(login_url='login')
def patient_list_view(request):
    search_query = request.GET.get('q', '').strip()
    gender_filter = request.GET.get('gender', '').strip()
    blood_filter = request.GET.get('blood_group', '').strip()

    patients = Patient.objects.all().order_by('-created_at')

    if search_query:
        patients = patients.filter(
            Q(name__icontains=search_query) |
            Q(mr_number__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(cnic__icontains=search_query)
        )

    if gender_filter:
        patients = patients.filter(gender=gender_filter)

    if blood_filter:
        patients = patients.filter(blood_group=blood_filter)

    context = {
        'patients': patients,
        'search_query': search_query,
        'gender_filter': gender_filter,
        'blood_filter': blood_filter,
        'total_count': patients.count()
    }
    return render(request, 'patient/patient_list.html', context)


# 2. PATIENTS - REGISTRATION FORM (SAVE TO DB)
@login_required(login_url='login')
def register_patient_view(request):
    if request.method == 'POST':
        name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        cnic = request.POST.get('cnic', '').strip()
        age = request.POST.get('age', '').strip()
        gender = request.POST.get('gender', '').strip()
        blood_group = request.POST.get('blood_group', '').strip()
        address = request.POST.get('address', '').strip()
        emergency_contact = request.POST.get('emergency_contact', '').strip()

        # Validation
        if not name or not phone or not age or not gender:
            messages.error(request, 'Please fill in all required fields marked with *')
            return render(request, 'patient/register_patient.html')

        try:
            patient = Patient.objects.create(
                name=name,
                phone=phone,
                cnic=cnic,
                age=int(age),
                gender=gender,
                blood_group=blood_group,
                address=address,
                emergency_contact=emergency_contact
            )
            messages.success(request, f'Patient "{patient.name}" successfully registered with MR #{patient.mr_number}!')
            return redirect('patient_list')
        except Exception as e:
            messages.error(request, f'Error saving patient: {str(e)}')
            return render(request, 'patient/register_patient.html')

    return render(request, 'patient/register_patient.html')


# --- EDIT PATIENT VIEW ---
@login_required(login_url='login')
def edit_patient_view(request, pk):
    patient = get_object_or_404(Patient, pk=pk)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        age = request.POST.get('age', '').strip()
        gender = request.POST.get('gender', '').strip()
        blood_group = request.POST.get('blood_group', '').strip()
        cnic = request.POST.get('cnic', '').strip()
        emergency_contact = request.POST.get('emergency_contact', '').strip()
        address = request.POST.get('address', '').strip()

        if not name or not phone or not age or not gender:
            messages.error(request, "Name, Phone, Age, aur Gender bharna lazmi hai!")
            return render(request, 'patient/edit_patient.html', {'patient': patient})

        patient.name = name
        patient.phone = phone
        patient.age = int(age)
        patient.gender = gender
        patient.blood_group = blood_group
        patient.cnic = cnic
        patient.emergency_contact = emergency_contact
        patient.address = address
        patient.save()

        messages.success(request, f"Patient {patient.name} ({patient.mr_number}) ka record update ho gaya!")
        return redirect('patient_list')

    return render(request, 'patient/edit_patient.html', {'patient': patient})


# --- DELETE PATIENT VIEW ---
@login_required(login_url='login')
def delete_patient_view(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    patient_info = f"{patient.name} ({patient.mr_number})"
    patient.delete()

    messages.success(request, f"Patient {patient_info} kamyabi se delete ho gaya!")
    return redirect('patient_list')


# ======================= OPD =======================

# DOCTORS MANAGEMENT (add + edit ek hi page par)
@login_required(login_url='login')
def doctor_list_view(request, pk=None):
    edit_doctor = get_object_or_404(Doctor, pk=pk) if pk else None
    form = DoctorForm(request.POST or None, instance=edit_doctor)

    if request.method == 'POST' and form.is_valid():
        doc = form.save()
        messages.success(request, f"{doc.name} save ho gaya!")
        return redirect('doctor_list')

    doctors = Doctor.objects.order_by('-is_active', 'name')
    return render(request, 'OPD/doctors.html', {
        'doctors': doctors,
        'form': form,
        'edit_doctor': edit_doctor,
    })


# ACTIVE / INACTIVE TOGGLE (doctor chala gaya ya wapas aa gaya)
@login_required(login_url='login')
def doctor_toggle_view(request, pk):
    if request.method == 'POST':
        doc = get_object_or_404(Doctor, pk=pk)
        doc.is_active = not doc.is_active
        doc.save()
        state = "Active" if doc.is_active else "Inactive"
        messages.success(request, f"{doc.name} ab {state} hai.")
    return redirect('doctor_list')


# 1. BOOK & PRINT TOKEN VIEW
@login_required(login_url='login')
def book_token_view(request):
    today = timezone.localdate()
    patients = Patient.objects.order_by('-created_at')
    doctors = Doctor.objects.filter(is_active=True).order_by('name')

    # Aaj ka agla token number
    last_token = OpdToken.objects.filter(created_at__date=today).order_by('-token_number').first()
    next_token_num = (last_token.token_number + 1) if last_token else 1

    latest_token = None

    if request.method == 'POST':
        patient_id = request.POST.get('patient_id')
        doctor_id = request.POST.get('doctor_id')
        payment_method = request.POST.get('payment_method', 'Cash')

        try:
            fee = int(request.POST.get('fee') or 0)
        except ValueError:
            fee = -1

        if not patient_id or not doctor_id:
            messages.error(request, "Patient aur Doctor select karna lazmi hai!")
        elif fee < 0:
            messages.error(request, "Fee sahi likhein!")
        else:
            patient = get_object_or_404(Patient, pk=patient_id)
            doctor = get_object_or_404(Doctor, pk=doctor_id, is_active=True)

            # Dobara check taake token number conflict na ho
            today_last = OpdToken.objects.filter(created_at__date=today).order_by('-token_number').first()
            token_num = (today_last.token_number + 1) if today_last else 1

            token = OpdToken.objects.create(
                token_number=token_num,
                patient=patient,
                doctor=doctor,
                room_number=doctor.room_number,
                fee=fee,
                payment_method=payment_method,
                status='Waiting'
            )
            latest_token = token
            next_token_num = token.token_number + 1
            messages.success(request, f"Token #{token.token_number:02d} kamyabi se book ho gaya!")

    context = {
        'patients': patients,
        'doctors': doctors,
        'next_token_number': next_token_num,
        'latest_token': latest_token,
    }
    return render(request, 'OPD/book_token.html', context)


# 2. TODAY'S TOKENS MANAGEMENT VIEW
@login_required(login_url='login')
def today_tokens_view(request):
    today = timezone.localdate()
    tokens = OpdToken.objects.filter(created_at__date=today).select_related('patient', 'doctor').order_by('token_number')

    context = {
        'tokens': tokens,
        'total_tokens': tokens.count(),
        'waiting_count': tokens.filter(status='Waiting').count(),
        'serving_count': tokens.filter(status='Serving').count(),
        'completed_count': tokens.filter(status='Completed').count(),
    }
    return render(request, 'OPD/today_tokens.html', context)


# 3. UPDATE TOKEN STATUS (Call Next / Done / Cancel)
@login_required(login_url='login')
def update_token_status_view(request, pk, new_status):
    token = get_object_or_404(OpdToken, pk=pk)
    if new_status in ['Waiting', 'Serving', 'Completed', 'Cancelled']:
        token.status = new_status
        token.save()
        messages.success(request, f"Token #{token.token_number:02d} ka status '{new_status}' ho gaya!")
    return redirect('today_tokens')


# 4. LIVE TV QUEUE DISPLAY VIEW
@login_required(login_url='login')
def queue_display_view(request):
    today = timezone.localdate()

    now_serving = OpdToken.objects.filter(
        created_at__date=today, status='Serving'
    ).select_related('patient', 'doctor').order_by('-updated_at').first()

    waiting_tokens = OpdToken.objects.filter(
        created_at__date=today, status='Waiting'
    ).select_related('patient', 'doctor').order_by('token_number')[:8]

    context = {
        'now_serving': now_serving,
        'waiting_tokens': waiting_tokens,
    }
    return render(request, 'OPD/queue_display.html', context)


# ======================= FINANCE =======================

def _parse_month(value):
    """'2026-10' -> (2026, 10). Ghalat ho to current month."""
    try:
        d = datetime.strptime(value, '%Y-%m')
        return d.year, d.month
    except (ValueError, TypeError):
        today = timezone.localdate()
        return today.year, today.month


# 1. EXPENSES LIST (search + filters)
@login_required(login_url='login')
def expenses_view(request):
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    month_str = request.GET.get('month', '').strip()

    expenses = Expense.objects.all()

    if q:
        expenses = expenses.filter(Q(title__icontains=q) | Q(voucher_number__icontains=q))
    if category:
        expenses = expenses.filter(category=category)
    if month_str:
        year, month = _parse_month(month_str)
        expenses = expenses.filter(date__year=year, date__month=month)

    total_amount = expenses.aggregate(t=Sum('amount'))['t'] or 0

    return render(request, 'finance/expenses.html', {
        'expenses': expenses,
        'total_amount': total_amount,
        'total_count': expenses.count(),
        'categories': Expense.CATEGORY_CHOICES,
        'q': q,
        'selected_category': category,
        'month_str': month_str,
    })


# 2. ADD EXPENSE
@login_required(login_url='login')
def add_expense_view(request):
    form = ExpenseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        exp = form.save()
        messages.success(request, f"Expense {exp.voucher_number} (Rs. {exp.amount}) save ho gaya!")
        return redirect('expenses')
    return render(request, 'finance/add_expense.html', {'form': form, 'edit_expense': None})


# 3. EDIT EXPENSE
@login_required(login_url='login')
def edit_expense_view(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    form = ExpenseForm(request.POST or None, instance=expense)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Expense {expense.voucher_number} update ho gaya!")
        return redirect('expenses')
    return render(request, 'finance/add_expense.html', {'form': form, 'edit_expense': expense})


# 4. DELETE EXPENSE (sirf POST)
@login_required(login_url='login')
def delete_expense_view(request, pk):
    if request.method == 'POST':
        expense = get_object_or_404(Expense, pk=pk)
        info = expense.voucher_number
        expense.delete()
        messages.success(request, f"Expense {info} delete ho gaya!")
    return redirect('expenses')


# 5. FINANCE SUMMARY & CHARTS
@login_required(login_url='login')
def finance_summary_view(request):
    today = timezone.localdate()
    year, month = _parse_month(request.GET.get('month') or today.strftime('%Y-%m'))
    month_value = f"{year}-{month:02d}"

    # Revenue = OPD tokens ki fee (Cancelled tokens ke bagair)
    tokens = OpdToken.objects.filter(
        created_at__year=year, created_at__month=month
    ).exclude(status='Cancelled')
    expenses = Expense.objects.filter(date__year=year, date__month=month)

    total_revenue = tokens.aggregate(t=Sum('fee'))['t'] or 0
    total_expense = expenses.aggregate(t=Sum('amount'))['t'] or 0
    net_profit = total_revenue - total_expense
    margin = round(net_profit / total_revenue * 100, 1) if total_revenue else 0

    # Weekly buckets: 1-7, 8-14, 15-21, 22-end
    rev_weeks = [0, 0, 0, 0]
    exp_weeks = [0, 0, 0, 0]

    for row in tokens.annotate(day=ExtractDay('created_at')).values('day').annotate(total=Sum('fee')).order_by('day'):
        rev_weeks[min((row['day'] - 1) // 7, 3)] += row['total'] or 0

    for row in expenses.annotate(day=ExtractDay('date')).values('day').annotate(total=Sum('amount')).order_by('day'):
        exp_weeks[min((row['day'] - 1) // 7, 3)] += row['total'] or 0

    # Category breakdown (donut)
    cat_rows = expenses.values('category').annotate(total=Sum('amount')).order_by('-total')
    chart_data = {
        'weeks': ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
        'revenue': rev_weeks,
        'expense': exp_weeks,
        'cat_labels': [r['category'] for r in cat_rows],
        'cat_values': [r['total'] for r in cat_rows],
    }

    return render(request, 'finance/finance_summary.html', {
        'month_value': month_value,
        'total_revenue': total_revenue,
        'total_expense': total_expense,
        'net_profit': net_profit,
        'margin': margin,
        'token_count': tokens.count(),
        'expense_count': expenses.count(),
        'chart_data': chart_data,
    })


from django.http import JsonResponse
from django.urls import reverse


@login_required(login_url='login')
def global_search_view(request):
    query = request.GET.get("q", "").strip()[:100]

    if len(query) < 2:
        return JsonResponse({"results": []})

    results = []

    # Patients
    patients = Patient.objects.filter(
        Q(name__icontains=query)
        | Q(mr_number__icontains=query)
        | Q(phone__icontains=query)
    ).order_by("name")[:5]

    for patient in patients:
        results.append({
            "type": "Patient",
            "title": patient.name,
            "subtitle": f"{patient.mr_number} · {patient.phone}",
            "url": reverse("patient_list") + f"?q={patient.mr_number}",
        })

    # Doctors
    doctors = Doctor.objects.filter(
        Q(name__icontains=query)
        | Q(specialization__icontains=query)
        | Q(room_number__icontains=query)
    ).order_by("name")[:5]

    for doctor in doctors:
        results.append({
            "type": "Doctor",
            "title": doctor.name,
            "subtitle": f"{doctor.specialization} · {doctor.room_number}",
            "url": reverse("doctor_list"),
        })

    # OPD tokens
    tokens = OpdToken.objects.select_related(
        "patient", "doctor"
    ).filter(
        Q(patient__name__icontains=query)
        | Q(patient__mr_number__icontains=query)
    ).order_by("-created_at")[:5]

    if query.isdigit():
        tokens = (
            OpdToken.objects.select_related("patient", "doctor")
            .filter(token_number=int(query))
            .order_by("-created_at")[:5]
        )

    for token in tokens:
        results.append({
            "type": "OPD Token",
            "title": f"Token #{token.token_number:02d}",
            "subtitle": f"{token.patient.name} · {token.status}",
            "url": reverse("today_tokens"),
        })

    # Expenses
    expenses = Expense.objects.filter(
        Q(title__icontains=query)
        | Q(voucher_number__icontains=query)
        | Q(category__icontains=query)
    ).order_by("-date")[:5]

    for expense in expenses:
        results.append({
            "type": "Expense",
            "title": expense.title,
            "subtitle": f"{expense.voucher_number} · Rs. {expense.amount}",
            "url": reverse("expenses"),
        })

    return JsonResponse({"results": results[:15]})


from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect


def clinic_login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    error = ""

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        # Django ke existing user/admin credentials verify honge
        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None and user.is_active:
            login(request, user)

            # Login ke baad dashboard
            return redirect("dashboard")
        else:
            error = "Invalid username or password."

    return render(
        request,
        "accounts/login.html",
        {"error": error}
    )
    
def logout_view(request):
    logout(request)
    return redirect('login')