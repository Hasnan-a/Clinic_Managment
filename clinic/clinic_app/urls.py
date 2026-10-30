from django.urls import path
from . import views

urlpatterns = [
    # Dashboard & Patients
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('patients/', views.patient_list_view, name='patient_list'),
    path('patients/register/', views.register_patient_view, name='register_patient'),
    path('patients/<int:pk>/edit/', views.edit_patient_view, name='edit_patient'),
    path('patients/<int:pk>/delete/', views.delete_patient_view, name='delete_patient'),
    
   


    # OPD QUEUE MODULE
    path('tokens/book/', views.book_token_view, name='book_token'),
    path('tokens/today/', views.today_tokens_view, name='today_tokens'),
    path('tokens/<int:pk>/status/<str:new_status>/', views.update_token_status_view, name='update_token_status'),
    path('queue/display/', views.queue_display_view, name='queue_display'),
    path('doctors/', views.doctor_list_view, name='doctor_list'),
    path('doctors/<int:pk>/edit/', views.doctor_list_view, name='doctor_edit'),
    path('doctors/<int:pk>/toggle/', views.doctor_toggle_view, name='doctor_toggle'),
       

    # Finance (Placeholders)
      # Finance
    path('expenses/', views.expenses_view, name='expenses'),
    path('expenses/add/', views.add_expense_view, name='add_expense'),
    path('expenses/<int:pk>/edit/', views.edit_expense_view, name='edit_expense'),
    path('expenses/<int:pk>/delete/', views.delete_expense_view, name='delete_expense'),
    path('finance/summary/', views.finance_summary_view, name='finance_summary'),
     path("global-search/",views.global_search_view,name="global_search"),
    

]