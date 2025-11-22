
from .user_model import User
from .role_model import Role
from .student_model import Student
from .teacher_model import Teacher
from .parent_model import Parent
from .manager_model import Manager
from .class_model import Class
from .subject_model import Subject
from .attendance_model import Attendance
from .enrollment_model import Enrollment
from .evaluation_model import Evaluation
from .notification_model import Notification
from .payroll_model import Payroll
from .schedule_model import Schedule
from .test_model import Test

# Import các bảng liên kết từ association_tables.py
from .association_tables import user_roles