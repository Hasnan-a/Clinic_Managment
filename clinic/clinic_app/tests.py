from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from clinic_app.models import Patient, Doctor, OpdToken, Expense

class ClinicModelTests(TestCase):

    def test_patient_model_logic(self):
        # 1. Test Patient Creation & MR Number Auto-generation
        patient = Patient.objects.create(
            name="Ali Khan",
            phone="03001234567",
            age=28,
            gender="Male"
        )
        self.assertEqual(patient.mr_number, "MR-1001")
        
        # 2. Test Initials Property
        self.assertEqual(patient.initials, "AK")

    def test_doctor_model(self):
        # Test Doctor Creation & __str__ method
        doctor = Doctor.objects.create(
            name="Dr. Ahmad",
            specialization="Cardiologist",
            room_number="Room 03",
            fee=2000
        )
        self.assertEqual(doctor.name, "Dr. Ahmad")
        self.assertEqual(str(doctor), "Dr. Ahmad (Room 03)")

    def test_opd_token_model(self):
        # Test OPD Token Link with Patient & Doctor
        patient = Patient.objects.create(
            name="Fatima Bibi",
            phone="03111234567",
            age=32,
            gender="Female"
        )
        doctor = Doctor.objects.create(name="Dr. Sana")
        
        token = OpdToken.objects.create(
            token_number=1,
            patient=patient,
            doctor=doctor,
            fee=1500,
            status="Waiting"
        )
        self.assertEqual(token.patient.name, "Fatima Bibi")
        self.assertEqual(token.status, "Waiting")

    def test_expense_voucher_number(self):
        # Test Expense Creation & Auto Voucher Number Generation (EXP-501 based on PK)
        expense = Expense.objects.create(
            title="Printer Ink",
            category="Stationery & Print",
            amount=1200
        )
        self.assertEqual(expense.voucher_number, "EXP-501")
        self.assertIn("EXP-501", str(expense))